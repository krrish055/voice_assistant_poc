# Standard library
from abc import ABC, abstractmethod


class BasePipeline(ABC):
    """Abstract contract — all pipeline implementations must follow this."""

    @abstractmethod   #open/close
    async def execute_stream_pipeline(
        self,
        user_id: str,
        session_id: str,
        raw_text_input: str,
        history: list,
    ) -> dict:
        """Execute the full STT → LLM → TTS pipeline and return a response envelope."""
        ...
