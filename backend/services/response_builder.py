"""
services/response_builder.py

Single responsibility: assemble the VoiceEnvelopeResponse from an orchestrator result.
"""
from pathlib import Path

from services.speech_processor import SpeechProcessorService
from schemas import VoiceEnvelopeResponse


class ResponseBuilderService:

    @staticmethod
    async def build_envelope(
        result: dict, user_id: str, session_id: str, transcript: str
    ) -> VoiceEnvelopeResponse:
        ai_response_text = result.get("ai_response_text") or "How can I help you?"
        data             = result.get("data", {})

        # URLs may be at top-level (set by ReportGenerationService) or inside data
        download_url = result.get("download_url") or data.get("download_url")
        pptx_url     = result.get("pptx_url")     or data.get("pptx_url")

        audio_path = await SpeechProcessorService.text_to_speech(ai_response_text, session_id)
        audio_url  = f"/api/voice/stream-audio/{Path(audio_path).name}" if audio_path else None

        return VoiceEnvelopeResponse(
            status="success",
            user_said=transcript,
            ai_response_text=ai_response_text,
            download_url=download_url,
            voice_response_url=audio_url,
            pptx_url=pptx_url,
        )
