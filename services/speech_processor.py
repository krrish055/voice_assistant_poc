# Standard library
import os
from typing import Optional

# Third-party
from groq import Groq
import edge_tts

# Local
from config import get_groq_api_key, get_stt_model

_REPORTS_DIR = os.path.join(os.path.dirname(__file__), "..", "reports")


class SpeechProcessorService:

    @staticmethod
    def speech_to_text(audio_file_path: str) -> str:
        if not os.path.exists(audio_file_path):
            return ""
        try:
            client = Groq(api_key=get_groq_api_key())
            with open(audio_file_path, "rb") as f:
                result = client.audio.transcriptions.create(
                    model=get_stt_model(),
                    file=f,
                    response_format="text",
                )
            return str(result).strip()
        except Exception as e:
            print(f"[STT] Error: {e}")
            return ""

    @staticmethod
    async def text_to_speech(text: str, session_id: str) -> Optional[str]:
        try:
            os.makedirs(_REPORTS_DIR, exist_ok=True)
            output_path = os.path.join(_REPORTS_DIR, f"audio_{session_id}.mp3")
            communicate = edge_tts.Communicate(text, voice="en-US-AriaNeural")
            await communicate.save(output_path)
            return output_path
        except Exception as e:
            print(f"[TTS] Error: {e}")
            return None
