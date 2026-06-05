# Standard library
import os
import re

# Third-party
from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

# Local
from exceptions import DocumentGenerationError, PipelineError, StorageError
from config import get_livekit_credentials
from services import GeneratorService, voice_pipeline
from services.generator import _REPORTS_DIR
from services.speech_processor import SpeechProcessorService
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
    if not re.fullmatch(r"[a-zA-Z0-9_\-]+", session_id):
        raise HTTPException(status_code=400, detail="Invalid session ID format.")
    file_path = os.path.join(_REPORTS_DIR, f"Report_{session_id}.pdf")
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Report not found.")
    return FileResponse(file_path, media_type="application/pdf", filename=f"Business_Report_{session_id}.pdf")


@app.get("/api/conversations/{user_id}")
def get_conversations(user_id: str) -> list:
    return get_conversations_by_user(user_id)


# ── LiveKit / Audio-stream routes 

@app.get("/api/voice/welcome")
async def voice_welcome():
    """Generate and return a TTS welcome greeting audio URL."""
    session_id = "welcome"
    text = "Welcome Krrish! I'm your AI compliance voice assistant. Please go ahead and speak — I'm listening."
    audio_path = await SpeechProcessorService.text_to_speech(text, session_id)
    if not audio_path:
        raise HTTPException(status_code=500, detail="Failed to generate welcome audio.")
    return {"status": "success", "audio_url": f"/api/voice/stream-audio/{os.path.basename(audio_path)}"}


@app.get("/api/voice/get-token")
def get_livekit_token(roomName: str, identity: str):
    """Return a signed LiveKit AccessToken for the frontend WebRTC client."""
    if not roomName or not identity:
        raise HTTPException(status_code=400, detail="roomName and identity are required.")

    try:
        from livekit.api import AccessToken, VideoGrants
        credentials = get_livekit_credentials()
        token = (
            AccessToken(credentials["api_key"], credentials["api_secret"])
            .with_identity(identity)                                            #permission to join.
            .with_name(identity)
            .with_grants(VideoGrants(
                room_join=True,
                room=roomName,
                can_publish=True,
                can_subscribe=True,
            ))
            .to_jwt()
        )
        return {"status": "success", "token": token, "server_url": credentials["server_url"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to generate LiveKit token.")


@app.post("/api/voice/process-stream")  # hands-free open-mic endpoint
@app.post("/api/voice/process-audio-stream")  # legacy alias
async def process_audio_stream(
    userId: str = Form(...),
    sessionId: str = Form(...),
    audio_blob: UploadFile = File(None),
    text_fallback: str = Form(None),
):
    if not re.fullmatch(r"[a-zA-Z0-9_\-]+", sessionId):
        raise HTTPException(status_code=400, detail="Invalid session ID format.")   #bad and malicious seccion.
    if not audio_blob and not text_fallback:
        raise HTTPException(status_code=400, detail="Either audio_blob or text_fallback is required.")

    temp_path = os.path.join(_REPORTS_DIR, f"input_{sessionId}.wav")

    try:
        os.makedirs(_REPORTS_DIR, exist_ok=True)

        if text_fallback and text_fallback.strip():
            transcript = text_fallback.strip()
        else:
            audio_bytes = await audio_blob.read()
            # Skip Whisper entirely if blob is too small to contain speech
            if len(audio_bytes) < 5000:
                return {"status": "silence", "user_said": "", "ai_response_text": "", "voice_response_url": None, "download_url": None}
            with open(temp_path, "wb") as f:
                f.write(audio_bytes)
            transcript = SpeechProcessorService.speech_to_text(temp_path)

        if not transcript:
            return {"status": "silence", "user_said": "", "ai_response_text": "", "voice_response_url": None, "download_url": None}

        history = get_session_history(sessionId)
        result = await voice_pipeline.execute_stream_pipeline(
            user_id=userId,
            session_id=sessionId,
            raw_text_input=transcript,
            history=history,
        )

        if result.get("status") != "success":
            raise HTTPException(status_code=500, detail="Pipeline error.")

        ai_data = result.get("data", {})
        intent = ai_data.get("intent", "CHAT")
        ai_response_text = ai_data.get("ai_response_text", "How can I help you?")
        is_restricted = intent == "RESTRICTED_REQUEST" or ai_data.get("is_restricted_query", False)

        if is_restricted:
            save_turn({"user_id": userId, "session_id": sessionId, "user_input": transcript,
                       "ai_response_text": ai_response_text, "intent": intent, "ai_data": ai_data,
                       "status": "PENDING_KRRISH_APPROVAL"})
            response_text = ai_response_text
        else:
            response_text = ai_response_text
            status = "CHAT" if intent == "CHAT" else ("APPROVED" if ai_data.get("data_complete") else "GATHERING")
            save_turn({"user_id": userId, "session_id": sessionId, "user_input": transcript,
                       "ai_response_text": response_text, "intent": intent,
                       "ai_data": ai_data if status == "APPROVED" else {}, "status": status})
            if status == "APPROVED":
                GeneratorService.generate_dynamic_pdf(ai_data, sessionId)

        audio_path = await SpeechProcessorService.text_to_speech(response_text, sessionId)
        audio_url = f"/api/voice/stream-audio/{os.path.basename(audio_path)}" if audio_path else None

        return {
            "status": "success",
            "user_said": transcript,
            "ai_response_text": response_text,
            "download_url": f"/api/voice/download-report/{sessionId}" if not is_restricted and ai_data.get("data_complete") else None,
            "voice_response_url": audio_url,
        }
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


@app.get("/api/voice/stream-audio/{filename}")
def stream_audio(filename: str):
    if not re.fullmatch(r"audio_[a-zA-Z0-9_\-]+\.mp3", filename):
        raise HTTPException(status_code=400, detail="Invalid filename.")
    path = os.path.join(_REPORTS_DIR, filename)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Audio file not found.")
    return FileResponse(path, media_type="audio/mpeg", filename=filename)
