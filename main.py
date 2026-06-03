# Standard library
import os

# Third-party
from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

# Local
from exceptions import DocumentGenerationError, PipelineError, StorageError
from services import GeneratorService, voice_pipeline
from storage import get_conversations_by_user, get_session_history, save_turn

load_dotenv()

# ── App bootstrap ─────────────────────────────────────────────────────────────

app = FastAPI(title="AI Voice Assistant API Gateway")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Exception handlers ────────────────────────────────────────────────────────

@app.exception_handler(PipelineError)
async def pipeline_error_handler(request: Request, exc: PipelineError) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={"status": "error", "message": "Pipeline failure", "details": str(exc)},
    )


@app.exception_handler(StorageError)
async def storage_error_handler(request: Request, exc: StorageError) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={"status": "error", "message": "Storage failure", "details": str(exc)},
    )


@app.exception_handler(DocumentGenerationError)
async def document_error_handler(request: Request, exc: DocumentGenerationError) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={"status": "error", "message": "Document generation failed", "details": str(exc)},
    )


# ── Request schema ────────────────────────────────────────────────────────────

class VoiceStreamPayload(BaseModel):
    userId: str
    sessionId: str
    textChunk: str


# ── Routes ────────────────────────────────────────────────────────────────────

@app.post("/api/voice/process-transcript")
async def process_transcript(payload: VoiceStreamPayload) -> dict:
    history = get_session_history(payload.sessionId)

    result = await voice_pipeline.execute_stream_pipeline(
        user_id=payload.userId,
        session_id=payload.sessionId,
        raw_text_input=payload.textChunk,
        history=history,
    )

    # Empty input — return prompt, nothing to store
    if result.get("status") == "ignored":
        return result

    if result.get("status") == "success":
        ai_data = result.get("data", {})
        intent = ai_data.get("intent", "CHAT")
        ai_response_text = ai_data.get("ai_response_text", "How can I help you?")
        result["download_url"] = None

        if intent == "RESTRICTED_REQUEST" or ai_data.get("is_restricted_query", False):
            # Save once with PENDING status — do NOT generate PDF
            save_turn({
                "user_id": payload.userId,
                "session_id": payload.sessionId,
                "user_input": payload.textChunk,
                "ai_response_text": ai_response_text,
                "intent": intent,
                "ai_data": ai_data,
                "status": "PENDING_KRRISH_APPROVAL",
            })
            result["ai_response_text"] = (
                "This request involves internal compliance guidelines or sensitive parameters "
                "(like pay slips, offer letters, or restricted data). This document cannot be "
                "processed right now. It will only be generated and sent over mail once Krrish "
                "reviews and approves it."
            )
            return result

        # Save the turn for all non-restricted intents
        save_turn({
            "user_id": payload.userId,
            "session_id": payload.sessionId,
            "user_input": payload.textChunk,
            "ai_response_text": ai_response_text,
            "intent": intent,
            "status": "CHAT" if intent == "CHAT" else "GATHERING",
        })

        if intent == "CHAT" or not ai_data.get("data_complete", False):
            result["ai_response_text"] = ai_response_text
            return result

        # REPORT_REQUEST with complete data — generate PDF and update status
        save_turn({
            "user_id": payload.userId,
            "session_id": payload.sessionId,
            "user_input": payload.textChunk,
            "ai_response_text": ai_response_text,
            "intent": intent,
            "ai_data": ai_data,
            "status": "APPROVED",
        })
        filepath = GeneratorService.generate_dynamic_pdf(ai_data, payload.sessionId)
        result["ai_response_text"] = ai_response_text
        result["download_url"] = f"/api/voice/download-report/{payload.sessionId}"

    return result


@app.get("/api/voice/download-report/{session_id}")
def download_report(session_id: str) -> FileResponse:
    """Serve a generated PDF report. Validates session_id to prevent path traversal."""
    import re
    if not re.fullmatch(r"[a-zA-Z0-9_\-]+", session_id):
        raise HTTPException(status_code=400, detail="Invalid session ID format.")

    from services.generator import _REPORTS_DIR
    file_path = os.path.join(_REPORTS_DIR, f"Report_{session_id}.pdf")

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Report not found.")

    return FileResponse(
        file_path,
        media_type="application/pdf",
        filename=f"Business_Report_{session_id}.pdf",
    )


@app.get("/api/conversations/{user_id}")
def get_conversations(user_id: str) -> list:
    return get_conversations_by_user(user_id)
