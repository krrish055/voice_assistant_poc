from pathlib import Path
from typing import Optional

from groq import Groq
import edge_tts

from config import get_groq_api_key, get_stt_model

_REPORTS_BASE = (Path(__file__).parent.parent / 'reports').resolve()


def _safe_audio_path(session_id: str) -> Path:
    """Build and validate audio output path — guards against path traversal."""
    target = (_REPORTS_BASE / f'audio_{session_id}.mp3').resolve()
    if not str(target).startswith(str(_REPORTS_BASE)):
        raise ValueError(f'Invalid session_id: {session_id}')
    return target


class SpeechProcessorService:

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
