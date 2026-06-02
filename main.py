from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from exceptions import PipelineError
from base import BasePipeline
from services.pipeline import voice_pipeline
from storage import save_to_db, get_all_data

app = FastAPI(title="AI Voice Assistant API Gateway", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(PipelineError)
async def pipeline_exception_handler(request: Request, exc: PipelineError):
    return JSONResponse(
        status_code=500,
        content={"status": "error", "message": "Pipeline Orchestration Failed", "details": str(exc)},
    )

class VoiceStreamPayload(BaseModel):
    userId: str
    sessionId: str
    textChunk: str

@app.post("/api/voice/process-transcript")
async def process_transcript(payload: VoiceStreamPayload):
    pipeline: BasePipeline = voice_pipeline
    result = await pipeline.execute_stream_pipeline(
        user_id=payload.userId,
        session_id=payload.sessionId,
        raw_text_input=payload.textChunk
    ) #this is for the json storage
    if result["status"] == "success":
        save_to_db({
            "user_id":    payload.userId,
            "session_id": payload.sessionId,
            "user_input": payload.textChunk,
            "ai_response": result["ai_response_text"],
            "next_step":   result["next_step"],
            "confidence":  result["confidence_score"],
        })
    return result

@app.get("/api/conversations/{user_id}")
def get_conversations(user_id: str):
    return [r for r in get_all_data() if r.get("user_id") == user_id]
