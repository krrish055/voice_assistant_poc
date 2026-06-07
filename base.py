from abc import ABC, abstractmethod


class BasePipeline(ABC):
    """Abstract contract — all pipeline implementations must follow this."""

    @abstractmethod
    async def execute_stream_pipeline(self, raw_text_input: str, history: list) -> dict:
        """Execute the LLM pipeline and return a structured response envelope."""
        ...
