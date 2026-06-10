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

        download_url = None
        pptx_url = None

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
                t = transcript.lower()
                pptx_kw = ('ppt', 'pptx', 'powerpoint', 'presentation', 'slides')
                pdf_kw  = ('pdf', 'document', 'summary')
                want_pptx = any(k in t for k in pptx_kw)
                want_pdf  = not want_pptx and (any(k in t for k in pdf_kw) or ai_data.get('output_format', '').upper() != 'PPTX')

                if want_pptx:
                    GeneratorService.generate_dynamic_pptx(ai_data, session_id)
                    pptx_url = f'/api/voice/download-pptx/{session_id}'
                else:
                    GeneratorService.generate_dynamic_pdf(ai_data, session_id)
                    download_url = f'/api/voice/download-report/{session_id}'

        audio_path = await SpeechProcessorService.text_to_speech(ai_response_text, session_id)
        audio_url  = f'/api/voice/stream-audio/{Path(audio_path).name}' if audio_path else None

        return {
            'status'            : 'success',
            'user_said'         : transcript,
            'ai_response_text'  : ai_response_text,
            'download_url'      : download_url,
            'voice_response_url': audio_url,
            'pptx_url'         : pptx_url   
        }
