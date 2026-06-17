from abc import ABC, abstractmethod


class BasePipeline(ABC):
    """Abstract contract — all pipeline implementations must follow this."""

    @abstractmethod
    async def execute(self, system_prompt: str, model: str, temperature: float,
                      max_tokens: int, history: list, user_input: str) -> dict:
        """Pure LLM executor. Returns the raw parsed output dict."""
        ...

    @abstractmethod
    async def execute_stream_pipeline(self, raw_text_input: str, history: list) -> dict:
        """Backward-compatible agent-unaware entry point. Prefer execute()."""
        ...
