import re
import asyncio
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse

from services import voice_pipeline, SpeechProcessorService, ResponseBuilderService
from utils import validate_session, safe_path, cleanup_old_audio, REPORTS_DIR
from config import AUDIO_FILE_SECURITY_REGEX
from schemas import VoiceStreamPayload, VoiceEnvelopeResponse, WelcomeResponse, TTSResponse, TokenResponse
from prompts import render, WELCOME_TEXT
from graph.graph_repository import graph_repo

router = APIRouter(prefix="/api/voice", tags=["Voice"])


@router.get("/welcome", response_model=WelcomeResponse)
async def voice_welcome():
    text = render(WELCOME_TEXT, {"company": "InTimeTec"})
    audio_path = await SpeechProcessorService.text_to_speech(text, "welcome")
    if not audio_path:
        raise HTTPException(status_code=500, detail="Failed to generate welcome audio.")
    return WelcomeResponse(status="success", audio_url=f"/api/voice/stream-audio/{Path(audio_path).name}")


@router.post("/process-transcript", response_model=VoiceEnvelopeResponse)
async def process_transcript(payload: VoiceStreamPayload):
    history = graph_repo.get_session_history(payload.sessionId)
    result = await voice_pipeline.execute_stream_pipeline(raw_text_input=payload.textChunk, history=history)
    if result.get("status") != "success":
        return VoiceEnvelopeResponse(status=result.get("status", "error"),
                                     user_said=payload.textChunk,
                                     ai_response_text=result.get("ai_response_text", ""))
    envelope = await ResponseBuilderService.build_envelope(result, payload.userId, payload.sessionId, payload.textChunk)
    if envelope.status == "success":
        loop = asyncio.get_running_loop()
        loop.run_in_executor(None, graph_repo.save_turn,
                             payload.userId, payload.sessionId, envelope.user_said, envelope.ai_response_text)
    return envelope


@router.post("/process-stream", response_model=VoiceEnvelopeResponse)
@router.post("/process-audio-stream", response_model=VoiceEnvelopeResponse)
async def process_audio_stream(
    userId: str = Form(...), sessionId: str = Form(...),
    audio_blob: UploadFile = File(None), text_fallback: str = Form(None),
):
    validate_session(sessionId)
    cleanup_old_audio(REPORTS_DIR)
    transcript = await SpeechProcessorService.extract_clean_text(audio_blob, text_fallback, sessionId)
    if not transcript:
        return VoiceEnvelopeResponse(status="silence", user_said="", ai_response_text="")
    history = graph_repo.get_session_history(sessionId)
    result = await voice_pipeline.execute_stream_pipeline(raw_text_input=transcript, history=history)
    envelope = await ResponseBuilderService.build_envelope(result, userId, sessionId, transcript)
    if envelope.status == "success":
        loop = asyncio.get_running_loop()
        loop.run_in_executor(None, graph_repo.save_turn,
                             userId, sessionId, envelope.user_said, envelope.ai_response_text)
    return envelope


@router.post("/tts", response_model=TTSResponse)
async def tts_only(text: str = Form(...), sessionId: str = Form(...)):
    validate_session(sessionId)
    if not text.strip() or len(text) > 2000:
        raise HTTPException(status_code=400, detail="Invalid text input.")
    audio_path = await SpeechProcessorService.text_to_speech(text.strip(), sessionId)
    if not audio_path:
        raise HTTPException(status_code=500, detail="TTS failed.")
    return TTSResponse(status="success", audio_url=f"/api/voice/stream-audio/{Path(audio_path).name}")


@router.get("/download-report/{session_id}")
def download_report(session_id: str):
    validate_session(session_id)
    file_path = safe_path(REPORTS_DIR, f"Report_{session_id}.pdf")
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Report not found.")
    return FileResponse(str(file_path), media_type="application/pdf", filename=f"Report_{session_id}.pdf")


@router.get("/download-pptx/{session_id}")
def download_pptx(session_id: str):
    validate_session(session_id)
    file_path = safe_path(REPORTS_DIR, f"Presentation_{session_id}.pptx")
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Presentation not found.")
    return FileResponse(str(file_path),
                        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                        filename=f"Presentation_{session_id}.pptx")


@router.get("/stream-audio/{filename}")
async def stream_audio(filename: str):
    if not re.fullmatch(AUDIO_FILE_SECURITY_REGEX, filename):
        raise HTTPException(status_code=400, detail="Invalid audio resource.")
    path = safe_path(REPORTS_DIR, filename)
    for _ in range(5):
        try:
            if path.exists():
                with open(path, "rb"):
                    break
        except PermissionError:
            await asyncio.sleep(0.2)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Audio resource not found.")
    return FileResponse(str(path), media_type="audio/mpeg")


@router.get("/get-token", response_model=TokenResponse)
def get_livekit_token(roomName: str, identity: str):
    if not roomName or not identity:
        raise HTTPException(status_code=400, detail="roomName and identity are required.")
    try:
        from livekit.api import AccessToken, VideoGrants
        from config import get_livekit_credentials
        creds = get_livekit_credentials()
        token = (
            AccessToken(creds["api_key"], creds["api_secret"])
            .with_identity(identity).with_name(identity)
            .with_grants(VideoGrants(room_join=True, room=roomName, can_publish=True, can_subscribe=True))
            .to_jwt()
        )
        return TokenResponse(status="success", token=token, server_url=creds["server_url"])
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to generate LiveKit token.")
