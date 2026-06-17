import os

from exceptions import ConfigurationError

GROQ_BASE_URL   = 'https://api.groq.com/openai/v1'
DEFAULT_MODEL   = 'llama-3.3-70b-versatile'
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.4"))
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "4000"))

# Speech processor
MIN_AUDIO_BYTES_THRESHOLD = 5000
MAX_TEXT_FALLBACK_LENGTH  = 4000

# Presentation layout
PPTX_EMU_WIDTH        = 12192000
PPTX_EMU_HEIGHT       = 6858000
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


def get_allowed_origins() -> list[str]:
    raw = os.getenv('ALLOWED_ORIGINS', 'http://localhost:3000')
    return [o.strip() for o in raw.split(',') if o.strip()]


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
