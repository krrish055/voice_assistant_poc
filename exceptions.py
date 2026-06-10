class PipelineError(Exception):
    """Base class for all pipeline-related errors."""
    pass


class LLMProcessingError(PipelineError):
    """Raised when the LLM fails to generate or parse a response."""
    pass


class ConfigurationError(PipelineError):
    """Raised when required API keys or environment variables are missing."""
    pass


class StorageError(Exception):
    """Raised when a DB read or write operation fails."""
    pass


class DocumentGenerationError(Exception):
    """Raised when PDF generation fails."""
    pass
