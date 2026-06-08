import re
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from exceptions import DocumentGenerationError, PipelineError, StorageError
from services import voice_pipeline, SpeechProcessorService, ResponseBuilderService
from storage import get_conversations_by_user, get_session_history
from utils import validate_session, safe_path, cleanup_old_audio, REPORTS_DIR
from config import AUDIO_FILE_SECURITY_REGEX

load_dotenv()

app = FastAPI(title='InTimeTec AI Voice Node Gateway')

app.add_middleware(
    CORSMiddleware,
    allow_origins=['http://localhost:3000'],
    allow_credentials=False,
    allow_methods=['GET', 'POST'],
    allow_headers=['*'],
)


# ── Exception Handlers ────────────────────────────────────────────────────────

@app.exception_handler(PipelineError)
async def pipeline_error_handler(req: Request, exc: PipelineError) -> JSONResponse:
    return JSONResponse(status_code=500, content={'status': 'error', 'message': str(exc)})

@app.exception_handler(StorageError)
async def storage_error_handler(req: Request, exc: StorageError) -> JSONResponse:
    return JSONResponse(status_code=500, content={'status': 'error', 'message': str(exc)})

@app.exception_handler(DocumentGenerationError)
async def document_error_handler(req: Request, exc: DocumentGenerationError) -> JSONResponse:
    return JSONResponse(status_code=500, content={'status': 'error', 'message': str(exc)})

@app.exception_handler(ValueError)
async def value_error_handler(req: Request, exc: ValueError) -> JSONResponse:
    return JSONResponse(status_code=400, content={'status': 'error', 'message': str(exc)})


# ── Request Schema ────────────────────────────────────────────────────────────

class VoiceStreamPayload(BaseModel):
    userId: str
    sessionId: str
    textChunk: str


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get('/api/voice/welcome')
async def voice_welcome() -> dict:
    text = 'Welcome to InTimeTec Compliance Node. I am your AI voice assistant. Please speak — I am listening.'
    audio_path = await SpeechProcessorService.text_to_speech(text, 'welcome')
    if not audio_path:
        raise HTTPException(status_code=500, detail='Failed to generate welcome audio.')
    return {'status': 'success', 'audio_url': f'/api/voice/stream-audio/{Path(audio_path).name}'}


@app.post('/api/voice/process-transcript')
async def process_transcript(payload: VoiceStreamPayload) -> dict:
    history = get_session_history(payload.sessionId)
    result = await voice_pipeline.execute_stream_pipeline(
        raw_text_input=payload.textChunk, history=history,
    )
    if result.get('status') != 'success':
        return result
    return await ResponseBuilderService.build_envelope(result, payload.userId, payload.sessionId, payload.textChunk)


@app.post('/api/voice/process-stream')
@app.post('/api/voice/process-audio-stream')
async def process_audio_stream(
    userId: str = Form(...), sessionId: str = Form(...),
    audio_blob: UploadFile = File(None), text_fallback: str = Form(None),
) -> dict:
    validate_session(sessionId)
    cleanup_old_audio(REPORTS_DIR)
    transcript = await SpeechProcessorService.extract_clean_text(audio_blob, text_fallback, sessionId)
    if not transcript:
        return {'status': 'silence', 'user_said': '', 'ai_response_text': '', 'voice_response_url': None, 'download_url': None}
    history = get_session_history(sessionId)
    result  = await voice_pipeline.execute_stream_pipeline(
        raw_text_input=transcript, history=history,
    )
    return await ResponseBuilderService.build_envelope(result, userId, sessionId, transcript)


@app.post('/api/voice/tts')
async def tts_only(text: str = Form(...), sessionId: str = Form(...)) -> dict:
    validate_session(sessionId)
    if not text.strip() or len(text) > 2000:
        raise HTTPException(status_code=400, detail='Invalid text input.')
    audio_path = await SpeechProcessorService.text_to_speech(text.strip(), sessionId)
    if not audio_path:
        raise HTTPException(status_code=500, detail='TTS failed.')
    return {'status': 'success', 'audio_url': f'/api/voice/stream-audio/{Path(audio_path).name}'}


@app.get('/api/voice/download-report/{session_id}')
def download_report(session_id: str) -> FileResponse:
    validate_session(session_id)
    file_path = safe_path(REPORTS_DIR, f'Report_{session_id}.pdf')
    if not file_path.exists():
        raise HTTPException(status_code=404, detail='Report asset not found.')
    return FileResponse(str(file_path), media_type='application/pdf', filename=f'Report_{session_id}.pdf')


@app.get('/api/voice/download-pptx/{session_id}')
def download_pptx(session_id: str) -> FileResponse:
    validate_session(session_id)
    file_path = safe_path(REPORTS_DIR, f'Presentation_{session_id}.pptx')
    if not file_path.exists():
        raise HTTPException(status_code=404, detail='Presentation asset not found.')
    return FileResponse(str(file_path),
                        media_type='application/vnd.openxmlformats-officedocument.presentationml.presentation',
                        filename=f'Presentation_{session_id}.pptx')


@app.get('/api/voice/stream-audio/{filename}')
def stream_audio(filename: str) -> FileResponse:
    if not re.fullmatch(AUDIO_FILE_SECURITY_REGEX, filename):
        raise HTTPException(status_code=400, detail='Invalid audio resource.')
    path = safe_path(REPORTS_DIR, filename)
    if not path.exists():
        raise HTTPException(status_code=404, detail='Audio resource not found.')
    return FileResponse(str(path), media_type='audio/mpeg')


@app.get('/api/voice/get-token')
def get_livekit_token(roomName: str, identity: str) -> dict:
    if not roomName or not identity:
        raise HTTPException(status_code=400, detail='roomName and identity are required.')
    try:
        from livekit.api import AccessToken, VideoGrants
        from config import get_livekit_credentials
        creds = get_livekit_credentials()
        token = (
            AccessToken(creds['api_key'], creds['api_secret'])
            .with_identity(identity).with_name(identity)
            .with_grants(VideoGrants(room_join=True, room=roomName, can_publish=True, can_subscribe=True))
            .to_jwt()
        )
        return {'status': 'success', 'token': token, 'server_url': creds['server_url']}
    except Exception:
        raise HTTPException(status_code=500, detail='Failed to generate LiveKit token.')


@app.get('/api/conversations/{user_id}')
def get_conversations(user_id: str) -> list:
    return get_conversations_by_user(user_id)
