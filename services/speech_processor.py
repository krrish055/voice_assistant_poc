from pathlib import Path
from typing import Optional

from fastapi import HTTPException, UploadFile
from groq import Groq
import edge_tts

from config import get_groq_api_key, get_stt_model, MIN_AUDIO_BYTES_THRESHOLD, MAX_TEXT_FALLBACK_LENGTH
from utils import REPORTS_DIR, ALLOWED_AUDIO_MIME, ALLOWED_AUDIO_EXT, safe_path

_REPORTS_BASE = Path(REPORTS_DIR).resolve()


def _safe_audio_path(session_id: str) -> Path:
    target = (_REPORTS_BASE / f'audio_{session_id}.mp3').resolve()
    if not str(target).startswith(str(_REPORTS_BASE)):
        raise ValueError(f'Invalid session_id: {session_id}')
    return target


class SpeechProcessorService:

    @staticmethod
    async def extract_clean_text(
        audio_blob: Optional[UploadFile], text_fallback: Optional[str], session_id: str
    ) -> str:
        """Extract transcript from text fallback or audio blob. Returns empty string on silence."""
        if text_fallback and text_fallback.strip():
            return text_fallback.strip()[:MAX_TEXT_FALLBACK_LENGTH]

        if not audio_blob:
            return ''

        if audio_blob.content_type and audio_blob.content_type not in ALLOWED_AUDIO_MIME:
            raise HTTPException(status_code=400, detail='Invalid audio format.')

        audio_bytes = await audio_blob.read()
        if len(audio_bytes) < MIN_AUDIO_BYTES_THRESHOLD:
            return ''

        ext = Path(audio_blob.filename or '').suffix.lower()
        if ext not in ALLOWED_AUDIO_EXT:
            ext = '.webm'

        temp_path = safe_path(REPORTS_DIR, f'input_{session_id}{ext}')
        try:
            temp_path.write_bytes(audio_bytes)
            return SpeechProcessorService.speech_to_text(str(temp_path))
        finally:
            temp_path.unlink(missing_ok=True)

    @staticmethod
    def speech_to_text(audio_file_path: str) -> str:
        if not Path(audio_file_path).exists():
            return ''
        try:
            client = Groq(api_key=get_groq_api_key())
            with open(audio_file_path, 'rb') as f:
                result = client.audio.transcriptions.create(
                    model=get_stt_model(),
                    file=f,
                    response_format='text',
                )
            return str(result).strip()
        except Exception as e:
            print(f'[STT] Error: {e}')
            return ''

    @staticmethod
    async def text_to_speech(text: str, session_id: str) -> Optional[str]:
        try:
            _REPORTS_BASE.mkdir(parents=True, exist_ok=True)
            output_path = _safe_audio_path(session_id)
            communicate = edge_tts.Communicate(text, voice='en-US-AriaNeural')
            await communicate.save(str(output_path))
            return str(output_path)
        except Exception as e:
            print(f'[TTS] Error: {e}')
            return None
