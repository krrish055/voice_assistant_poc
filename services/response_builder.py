from pathlib import Path

from services.generator import GeneratorService
from services.speech_processor import SpeechProcessorService
from storage import save_turn


class ResponseBuilderService:

    @staticmethod
    async def build_envelope(result: dict, user_id: str, session_id: str, transcript: str) -> dict:
        """Classify intent, persist turn, optionally generate PDF, return response envelope."""
        ai_data          = result.get('data', {})
        intent           = ai_data.get('intent', 'CHAT')
        ai_response_text = ai_data.get('ai_response_text', 'How can I help you?')
        is_restricted    = intent == 'RESTRICTED_REQUEST' or ai_data.get('is_restricted_query', False)

        if is_restricted:
            save_turn({'user_id': user_id, 'session_id': session_id, 'user_input': transcript,
                       'ai_response_text': ai_response_text, 'intent': intent,
                       'ai_data': ai_data, 'status': 'PENDING_KRRISH_APPROVAL'})
            download_url = None
        else:
            status = 'CHAT' if intent == 'CHAT' else ('APPROVED' if ai_data.get('data_complete') else 'GATHERING')
            save_turn({'user_id': user_id, 'session_id': session_id, 'user_input': transcript,
                       'ai_response_text': ai_response_text, 'intent': intent,
                       'ai_data': ai_data if status == 'APPROVED' else {}, 'status': status})
            if status == 'APPROVED':
                GeneratorService.generate_dynamic_pdf(ai_data, session_id)
            download_url = f'/api/voice/download-report/{session_id}' if status == 'APPROVED' else None

        audio_path = await SpeechProcessorService.text_to_speech(ai_response_text, session_id)
        audio_url  = f'/api/voice/stream-audio/{Path(audio_path).name}' if audio_path else None

        return {
            'status'            : 'success',
            'user_said'         : transcript,
            'ai_response_text'  : ai_response_text,
            'download_url'      : download_url,
            'voice_response_url': audio_url,
        }
