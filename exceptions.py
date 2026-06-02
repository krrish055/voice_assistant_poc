class PipelineError(Exception):
    """Base class for all pipeline errors."""
    pass

class LLMProcessingError(PipelineError):
    """Raised when the LLM fails to generate a response."""
    pass

class ConfigurationError(PipelineError):
    """Raised when API keys or env variables are missing."""
    pass

class GatewayTimeoutError(PipelineError):
    """Raised when the process takes too long."""
    pass
