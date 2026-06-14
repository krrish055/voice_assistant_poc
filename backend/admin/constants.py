"""Admin Module Constants - Magic Numbers & Configuration"""

# ═══════════════════════════════════════════════════════════════════════════
# C4 Level 4: Code - Constants Module
# SOLID Principle: Single Responsibility
# ═══════════════════════════════════════════════════════════════════════════

# Agent Limits
MAX_AGENTS = 10
MAX_AGENT_NAME_LENGTH = 64
MAX_SYSTEM_PROMPT_LENGTH = 4096
MAX_RESPONSE_TOKENS = 2048

# Temperature Bounds
MIN_TEMPERATURE = 0.0
MAX_TEMPERATURE = 2.0
DEFAULT_TEMPERATURE = 0.7

# Token Limits
MIN_MAX_TOKENS = 100
MAX_MAX_TOKENS = 4096
DEFAULT_MAX_TOKENS = 1000

# Session & Monitoring
MAX_CONVERSATION_HISTORY = 100
AGENT_ACTIVITY_TIMEOUT_SECONDS = 3600  # 1 hour
MAX_CONCURRENT_CHATS = 50

# Prompt Variable Limits
MAX_PROMPT_VARIABLES = 20
MAX_VARIABLE_NAME_LENGTH = 32
MAX_VARIABLE_VALUE_LENGTH = 512

# Agent Status
AGENT_STATUS_ACTIVE = "active"
AGENT_STATUS_IDLE = "idle"
AGENT_STATUS_PAUSED = "paused"
AGENT_STATUS_ERROR = "error"

# Models
SUPPORTED_MODELS = [
    "llama-3.3-70b-versatile",
    "llama-3.3-70b-specdec",
    "llama-3.1-70b-versatile",
    "gemma2-9b-it",
]

DEFAULT_MODEL = "llama-3.3-70b-versatile"

# API Response Codes
SUCCESS_CODE = "success"
ERROR_CODE = "error"
NOT_FOUND_CODE = "not_found"
VALIDATION_ERROR_CODE = "validation_error"
