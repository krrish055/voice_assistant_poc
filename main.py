import re
import time
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from exceptions import DocumentGenerationError, PipelineError, StorageError
from services import GeneratorService, voice_pipeline, SpeechProcessorService
from services.generator import _REPORTS_DIR
from storage import get_conversations_by_user, get_session_history, save_turn

load_dotenv()

# ── App bootstrap ─────────────────────────────────────────────────────────────

app = FastAPI(title="AI Voice Assistant API Gateway")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
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


# ── Security helpers ─────────────────────────────────────────────────────────

ALLOWED_AUDIO_MIME = {'audio/webm', 'audio/wav', 'audio/mpeg', 'audio/ogg', 'audio/flac', 'application/octet-stream'}
ALLOWED_AUDIO_EXT  = {'.webm', '.wav', '.mp3', '.m4a', '.ogg', '.flac'}
_SESSION_RE        = re.compile(r'^[a-zA-Z0-9_\-]{1,64}$')


def _validate_session(session_id: str) -> str:
    if not _SESSION_RE.fullmatch(session_id):
        raise HTTPException(status_code=400, detail='Invalid session ID format.')
    return session_id


def _safe_path(directory: str, filename: str) -> Path:
    """Resolve path and verify it stays within the intended directory (path traversal guard)."""
    base   = Path(directory).resolve()
    target = (base / filename).resolve()
    if not str(target).startswith(str(base)):
        raise HTTPException(status_code=400, detail='Invalid path.')
    return target


def _cleanup_old_audio(directory: str, max_age_seconds: int = 3600) -> None:
    """Remove audio files older than max_age_seconds to prevent disk bloat."""
    now = time.time()
    try:
        for f in Path(directory).glob('audio_*.mp3'):
            if now - f.stat().st_mtime > max_age_seconds:
                f.unlink(missing_ok=True)
    except Exception:
        pass


# ── Request schema ────────────────────────────────────────────────────────────

class VoiceStreamPayload(BaseModel):
    userId: str
    sessionId: str
    textChunk: str


# ── Routes ────────────────────────────────────────────────────────────────────

@app.post('/api/voice/process-transcript')
async def process_transcript(payload: VoiceStreamPayload) -> dict:
    history = get_session_history(payload.sessionId)
    result  = await voice_pipeline.execute_stream_pipeline(
        user_id=payload.userId,
        session_id=payload.sessionId,
        raw_text_input=payload.textChunk,
        history=history,
    )
    if result.get('status') == 'ignored':
        return result
    if result.get('status') == 'success':
        return await _build_response(result, payload.userId, payload.sessionId, payload.textChunk)
    return result


@app.get("/api/voice/download-report/{session_id}")
def download_report(session_id: str) -> FileResponse:
    _validate_session(session_id)
    file_path = _safe_path(_REPORTS_DIR, f"Report_{session_id}.pdf")
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Report not found.")
    return FileResponse(str(file_path), media_type="application/pdf", filename=f"Business_Report_{session_id}.pdf")


@app.get("/api/conversations/{user_id}")
def get_conversations(user_id: str) -> list:
    return get_conversations_by_user(user_id)


# ── LiveKit / Audio-stream routes 

@app.get("/api/voice/welcome")
async def voice_welcome() -> dict:
    text = "Welcome to InTimeTec Compliance Node. I am your AI voice assistant. Please speak — I am listening."
    audio_path = await SpeechProcessorService.text_to_speech(text, "welcome")
    if not audio_path:
        raise HTTPException(status_code=500, detail="Failed to generate welcome audio.")
    return {"status": "success", "audio_url": f"/api/voice/stream-audio/{Path(audio_path).name}"}


@app.get("/api/voice/get-token")
def get_livekit_token(roomName: str, identity: str) -> dict:
    if not roomName or not identity:
        raise HTTPException(status_code=400, detail="roomName and identity are required.")
    try:
        from livekit.api import AccessToken, VideoGrants
        from config import get_livekit_credentials
        credentials = get_livekit_credentials()
        token = (
            AccessToken(credentials["api_key"], credentials["api_secret"])
            .with_identity(identity)
            .with_name(identity)
            .with_grants(VideoGrants(room_join=True, room=roomName, can_publish=True, can_subscribe=True))
            .to_jwt()
        )
        return {"status": "success", "token": token, "server_url": credentials["server_url"]}
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to generate LiveKit token.")


@app.post("/api/voice/process-stream")
@app.post("/api/voice/process-audio-stream")
async def process_audio_stream(
    userId: str = Form(...),
    sessionId: str = Form(...),
    audio_blob: UploadFile = File(None),
    text_fallback: str = Form(None),
) -> dict:
    _validate_session(sessionId)
    if not audio_blob and not text_fallback:
        raise HTTPException(status_code=400, detail='Either audio_blob or text_fallback is required.')

    Path(_REPORTS_DIR).mkdir(parents=True, exist_ok=True)
    _cleanup_old_audio(_REPORTS_DIR)
    temp_path: Path | None = None

    try:
        transcript, temp_path = await _extract_transcript(audio_blob, text_fallback, sessionId)
        if not transcript:
            return {'status': 'silence', 'user_said': '', 'ai_response_text': '', 'voice_response_url': None, 'download_url': None}

        history = get_session_history(sessionId)
        result  = await voice_pipeline.execute_stream_pipeline(
            user_id=userId, session_id=sessionId, raw_text_input=transcript, history=history,
        )
        if result.get('status') != 'success':
            raise HTTPException(status_code=500, detail='Pipeline error.')

        return await _build_response(result, userId, sessionId, transcript)
    finally:
        if temp_path and temp_path.exists():
            temp_path.unlink(missing_ok=True)


async def _extract_transcript(
    audio_blob: UploadFile | None, text_fallback: str | None, session_id: str
) -> tuple[str, Path | None]:
    """Returns (transcript, temp_path). Caller must delete temp_path if not None."""
    if text_fallback and text_fallback.strip():
        return text_fallback.strip()[:4000], None

    if not audio_blob:
        return '', None

    if audio_blob.content_type and audio_blob.content_type not in ALLOWED_AUDIO_MIME:
        raise HTTPException(status_code=400, detail='Invalid audio format.')

    audio_bytes = await audio_blob.read()
    if len(audio_bytes) < 5000:
        return '', None

    ext = Path(audio_blob.filename or '').suffix.lower()
    if ext not in ALLOWED_AUDIO_EXT:
        ext = '.webm'

    temp_path = _safe_path(_REPORTS_DIR, f'input_{session_id}{ext}')
    temp_path.write_bytes(audio_bytes)
    return SpeechProcessorService.speech_to_text(str(temp_path)), temp_path


async def _build_response(result: dict, user_id: str, session_id: str, transcript: str) -> dict:
    """Process pipeline result, save turn, generate PDF if needed, return final response."""
    ai_data         = result.get('data', {})
    intent          = ai_data.get('intent', 'CHAT')
    ai_response_text = ai_data.get('ai_response_text', 'How can I help you?')
    is_restricted   = intent == 'RESTRICTED_REQUEST' or ai_data.get('is_restricted_query', False)

    if is_restricted:
        save_turn({'user_id': user_id, 'session_id': session_id, 'user_input': transcript,
                   'ai_response_text': ai_response_text, 'intent': intent,
                   'ai_data': ai_data, 'status': 'PENDING_KRRISH_APPROVAL'})
        response_text = ai_response_text
        download_url  = None
    else:
        response_text = ai_response_text
        status = 'CHAT' if intent == 'CHAT' else ('APPROVED' if ai_data.get('data_complete') else 'GATHERING')
        save_turn({'user_id': user_id, 'session_id': session_id, 'user_input': transcript,
                   'ai_response_text': response_text, 'intent': intent,
                   'ai_data': ai_data if status == 'APPROVED' else {}, 'status': status})
        if status == 'APPROVED':
            GeneratorService.generate_dynamic_pdf(ai_data, session_id)
        download_url = f'/api/voice/download-report/{session_id}' if status == 'APPROVED' else None

    audio_path = await SpeechProcessorService.text_to_speech(response_text, session_id)
    audio_url  = f'/api/voice/stream-audio/{Path(audio_path).name}' if audio_path else None

    return {'status': 'success', 'user_said': transcript, 'ai_response_text': response_text,
            'download_url': download_url, 'voice_response_url': audio_url}


@app.post("/api/voice/tts")
async def tts_only(text: str = Form(...), sessionId: str = Form(...)):
    """TTS-only endpoint — no AI pipeline. Used for FAQ cached answers."""
    _validate_session(sessionId)
    if not text or not text.strip() or len(text) > 2000:
        raise HTTPException(status_code=400, detail='Invalid text input.')
    audio_path = await SpeechProcessorService.text_to_speech(text.strip(), sessionId)
    if not audio_path:
        raise HTTPException(status_code=500, detail='TTS failed.')
    return {'status': 'success', 'audio_url': f'/api/voice/stream-audio/{Path(audio_path).name}'}


@app.get("/api/voice/stream-audio/{filename}")
def stream_audio(filename: str):
    if not re.fullmatch(r'audio_[a-zA-Z0-9_\-]+\.mp3', filename):
        raise HTTPException(status_code=400, detail='Invalid filename.')
    path = _safe_path(_REPORTS_DIR, filename)
    if not path.exists():
        raise HTTPException(status_code=404, detail='Audio file not found.')
    return FileResponse(str(path), media_type='audio/mpeg', filename=filename)
