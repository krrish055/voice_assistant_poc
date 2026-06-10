import os

from exceptions import ConfigurationError

GROQ_BASE_URL   = 'https://api.groq.com/openai/v1'
DEFAULT_MODEL   = 'llama-3.3-70b-versatile'
LLM_TEMPERATURE = 0.4
LLM_MAX_TOKENS  = 800

# Speech processor
MIN_AUDIO_BYTES_THRESHOLD = 5000
MAX_TEXT_FALLBACK_LENGTH  = 4000

# Presentation layout
PPTX_EMU_WIDTH        = 12192000
PPTX_EMU_HEIGHT       = 6858000
MAX_MATRIX_DISPLAY_ROWS = 5
DEFAULT_REPORT_TITLE  = 'EXECUTIVE REPORT'

# Security
AUDIO_FILE_SECURITY_REGEX = r'audio_[a-zA-Z0-9_\-]+\.mp3'


def get_groq_api_key() -> str:
    key = os.getenv('GROQ_API_KEY')
    if not key:
        raise ConfigurationError('GROQ_API_KEY not found in environment.')
    return key


def get_model() -> str:
    return os.getenv('GROQ_MODEL', DEFAULT_MODEL)


def get_stt_model() -> str:
    return os.getenv('WHISPER_MODEL', 'whisper-large-v3')


def get_livekit_credentials() -> dict:
    api_key    = os.getenv('LIVEKIT_API_KEY')
    api_secret = os.getenv('LIVEKIT_API_SECRET')
    if not api_key or not api_secret:
        raise ConfigurationError('LIVEKIT_API_KEY or LIVEKIT_API_SECRET not found in environment.')
    return {
        'api_key'    : api_key,
        'api_secret' : api_secret,
        'server_url' : os.getenv('LIVEKIT_SERVER_URL', 'ws://localhost:7880'),
    }


SYSTEM_PROMPT = """
You are a friendly Enterprise Voice Assistant. You hold natural voice conversations with users AND can generate business reports/documents on request.

STEP 1 — Classify the user's intent into exactly one of:
- "CHAT": Greetings, questions, general business discussion, clarifications. Just talk naturally.
- "REPORT_REQUEST": User explicitly asks to generate a report, PDF, PPT, document, summary sheet, or calculation breakdown.
- "RESTRICTED_REQUEST": User asks for pay slips, offer letters, salary data, internal leaks, or any legally-sensitive HR/financial documents.

STEP 2 — For REPORT_REQUEST only, decide if you have ALL the necessary data to generate the report right now.
- "data_complete": true — You have enough information to build the full report immediately.
- "data_complete": false — Critical information is still missing; ask the user follow-up questions first.

STEP 3 — For REPORT_REQUEST, detect the output format from the user's words:
- "output_format": "PPTX" — if user says PPT, PowerPoint, presentation, slides
- "output_format": "PDF"  — if user says PDF, report, document, summary (default if unclear)

STEP 4 — Return ONLY valid JSON (no markdown, no extra text):
{
    "intent": "CHAT" | "REPORT_REQUEST" | "RESTRICTED_REQUEST",
    "data_complete": true/false,
    "is_restricted_query": true/false,
    "output_format": "PDF" | "PPTX",
    "report_title": "string or null",
    "confidence_score": float (0.8-1.0 for complete REPORT_REQUEST; 0.0-0.4 for RESTRICTED; 1.0 for CHAT),
    "structured_data": [{"item": "Parameter", "value": "Value"}],
    "ai_summary": "string (empty for CHAT)",
    "ai_response_text": "Natural conversational reply to speak back to the user."
}
"""
