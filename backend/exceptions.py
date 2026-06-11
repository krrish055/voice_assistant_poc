# ── Exception Hierarchy ───────────────────────────────────────────────────────
# Single Responsibility: pure domain error definitions — no HTTP logic here.
# Open/Closed: extend by subclassing AppBaseException; never modify this file.


class AppBaseException(Exception):
    """Root base for all application domain exceptions."""
    def __init__(self, message: str, status_code: int = 500) -> None:
        super().__init__(message)
        self.message     = message
        self.status_code = status_code


# ── Domain Exceptions ─────────────────────────────────────────────────────────

class VoiceProcessingError(AppBaseException):
    """Groq/Whisper, VAD chunking, or transcription failures."""
    def __init__(self, message: str) -> None:
        super().__init__(message, status_code=422)


class DocumentGenerationError(AppBaseException):
    """Physical PPT or PDF generation failures."""
    def __init__(self, message: str) -> None:
        super().__init__(message, status_code=503)


class SessionExpiredError(AppBaseException):
    """Invalid or expired session / WebSocket identity."""
    def __init__(self, message: str) -> None:
        super().__init__(message, status_code=401)


class ExternalServiceTimeout(AppBaseException):
    """Upstream AI API dependency did not respond in time."""
    def __init__(self, message: str) -> None:
        super().__init__(message, status_code=504)


# ── Legacy Aliases (backward compatibility) ───────────────────────────────────
# Services that raise these names continue to work without any changes.

class PipelineError(AppBaseException):
    """Base for pipeline-related errors."""
    def __init__(self, message: str = '', status_code: int = 500) -> None:
        super().__init__(message, status_code)


class LLMProcessingError(PipelineError):
    """LLM failed to generate or parse a response."""


class ConfigurationError(PipelineError):
    """Required API keys or environment variables are missing."""


class StorageError(AppBaseException):
    """DB read or write operation failed."""
    def __init__(self, message: str = '') -> None:
        super().__init__(message, status_code=500)
