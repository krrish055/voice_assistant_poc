from pathlib import Path
import json

from services.generator import GeneratorService
from services.speech_processor import SpeechProcessorService
from schemas import VoiceEnvelopeResponse


def _clean_text(value: str) -> str:
    """Strip any trailing JSON blob that the LLM appended after the spoken text."""
    if not value:
        return value
    brace_idx = value.find('{')
    if brace_idx > 0:
        prefix = value[:brace_idx].strip()
        suffix = value[brace_idx:].strip()
        try:
            parsed = json.loads(suffix)
            # If the JSON itself has a cleaner ai_response_text, prefer it
            inner = parsed.get("ai_response_text", "").strip()
            return inner if inner and not inner.startswith("{") else prefix
        except (json.JSONDecodeError, ValueError):
            pass
        return prefix
    # If the whole thing is JSON, extract the text field
    if value.strip().startswith("{"):
        try:
            parsed = json.loads(value.strip())
            return (
                parsed.get("ai_response_text")
                or parsed.get("ai_summary")
                or ""
            ).strip()
        except (json.JSONDecodeError, ValueError):
            pass
    return value


class ResponseBuilderService:

    @staticmethod
    async def build_envelope(result: dict, user_id: str, session_id: str, transcript: str) -> VoiceEnvelopeResponse:
        ai_data = result.get("data", {})
        intent = ai_data.get("intent", "CHAT")
        raw_text = result.get("ai_response_text") or ai_data.get("ai_response_text", "How can I help you?")
        ai_response_text = _clean_text(raw_text) or "How can I help you?"
        is_restricted = intent == "RESTRICTED_REQUEST" or ai_data.get("is_restricted_query", False)

        download_url = pptx_url = None

        if not is_restricted and intent == "REPORT_REQUEST" and ai_data.get("data_complete"):
            want_pptx = any(k in transcript.lower() for k in ("ppt", "pptx", "powerpoint", "presentation", "slides"))
            if want_pptx:
                GeneratorService.generate_dynamic_pptx(ai_data, session_id)
                pptx_url = f"/api/voice/download-pptx/{session_id}"
            else:
                GeneratorService.generate_dynamic_pdf(ai_data, session_id)
                download_url = f"/api/voice/download-report/{session_id}"

        audio_path = await SpeechProcessorService.text_to_speech(ai_response_text, session_id)
        audio_url = f"/api/voice/stream-audio/{Path(audio_path).name}" if audio_path else None

        return VoiceEnvelopeResponse(
            status="success",
            user_said=transcript,
            ai_response_text=ai_response_text,
            download_url=download_url,
            voice_response_url=audio_url,
            pptx_url=pptx_url,
        )
