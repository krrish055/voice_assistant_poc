from dotenv import load_dotenv
load_dotenv()  # Must be first — loads .env before any module reads os.getenv()

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from exceptions import PipelineError
from base import BasePipeline
from services.pipeline import voice_pipeline

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
    return await pipeline.execute_stream_pipeline(
        user_id=payload.userId,
        session_id=payload.sessionId,
        raw_text_input=payload.textChunk
    )
