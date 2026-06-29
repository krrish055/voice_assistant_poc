import os

from exceptions import ConfigurationError

GROQ_BASE_URL   = 'https://api.groq.com/openai/v1'
DEFAULT_MODEL   = 'llama-3.3-70b-versatile'
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.4"))
LLM_MAX_TOKENS  = int(os.getenv("LLM_MAX_TOKENS", "4000"))

# Company
COMPANY_NAME = os.getenv("COMPANY_NAME", "InTimeTec")

# Speech processor
MIN_AUDIO_BYTES_THRESHOLD = 5000
MAX_TEXT_FALLBACK_LENGTH  = 4000
TTS_VOICE                 = os.getenv("TTS_VOICE", "en-US-AriaNeural")

# Presentation layout
PPTX_EMU_WIDTH        = 12192000
PPTX_EMU_HEIGHT       = 6858000
DEFAULT_REPORT_TITLE  = 'EXECUTIVE REPORT'

# File retention
PDF_MAX_AGE_SECONDS = int(os.getenv("PDF_MAX_AGE_SECONDS", "86400"))

# Session memory
MEMORY_MAX_FACTS            = int(os.getenv("MEMORY_MAX_FACTS", "50"))
MEMORY_SUMMARY_TURNS        = int(os.getenv("MEMORY_SUMMARY_TURNS", "6"))
MEMORY_HISTORY_WINDOW       = int(os.getenv("MEMORY_HISTORY_WINDOW", "20"))
REPORT_HISTORY_WINDOW       = int(os.getenv("REPORT_HISTORY_WINDOW", "8"))      # turns injected into report agent prompt
REPORT_MAX_TOKENS           = int(os.getenv("REPORT_MAX_TOKENS", "16000"))      # large output for full-page section content
MAX_REPORT_HISTORY_LIMIT    = int(os.getenv("MAX_REPORT_HISTORY_LIMIT", "10000")) # upper bound for full session fetch

# Security
AUDIO_FILE_SECURITY_REGEX = r'audio_[a-zA-Z0-9_\-]+\.mp3'

# ── Background Job Engine ─────────────────────────────────────────────────────
JOB_MAX_RETRIES          = int(os.getenv("JOB_MAX_RETRIES", "3"))
JOB_POLL_INTERVAL_SECS   = float(os.getenv("JOB_POLL_INTERVAL_SECS", "5.0"))
JOB_MAX_CONCURRENT       = int(os.getenv("JOB_MAX_CONCURRENT", "4"))
JOB_EXECUTION_TIMEOUT    = int(os.getenv("JOB_EXECUTION_TIMEOUT", "300"))

# ── Notification Center ───────────────────────────────────────────────────────
NOTIFICATION_RETENTION_DAYS = int(os.getenv("NOTIFICATION_RETENTION_DAYS", "30"))
NOTIFICATION_MAX_UNREAD     = int(os.getenv("NOTIFICATION_MAX_UNREAD", "100"))


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
