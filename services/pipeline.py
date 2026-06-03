# Standard library
import json

# Third-party
from openai import AsyncOpenAI
from pydantic import BaseModel

# Local
from base import BasePipeline
from config import GROQ_BASE_URL, SYSTEM_PROMPT, get_groq_api_key, get_model, LLM_TEMPERATURE, LLM_MAX_TOKENS
from exceptions import LLMProcessingError


class PipelineResponse(BaseModel):
    """Envelope returned by the pipeline to the API layer."""
    status: str
    ai_response_text: str
    confidence_score: float
    data: dict = {}


class VoicePipelineOrchestrator(BasePipeline):

    def __init__(self) -> None:
        self._client: AsyncOpenAI | None = None

    def _get_client(self) -> AsyncOpenAI:
        """Lazy-init Groq client — validates API key on first call."""
        if self._client is None:
            self._client = AsyncOpenAI(
                api_key=get_groq_api_key(),
                base_url=GROQ_BASE_URL,
            )
        return self._client

    @staticmethod
    def _strip_markdown(raw: str) -> str:
        """Strip ```json ... ``` fences that Groq sometimes wraps responses in."""
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return raw.strip()

    @staticmethod
    def _build_messages(history: list, raw_text_input: str) -> list:
        """Build the multi-turn message list from session history + current input."""
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        for turn in history:
            messages.append({"role": "user", "content": turn["user_input"]})
            messages.append({"role": "assistant", "content": turn["ai_response_text"]})
        messages.append({"role": "user", "content": raw_text_input})
        return messages

    async def execute_stream_pipeline(
        self,
        user_id: str,
        session_id: str,
        raw_text_input: str,
        history: list,
    ) -> dict:
        """Run LLM pipeline and return a structured response envelope."""
        if not raw_text_input.strip():
            return PipelineResponse(
                status="ignored",
                ai_response_text="Please say something so I can help you.",
                confidence_score=0.0,
            ).model_dump()

        try:
            messages = self._build_messages(history, raw_text_input)

            response = await self._get_client().chat.completions.create(
                model=get_model(),
                messages=messages,
                temperature=LLM_TEMPERATURE,
                max_tokens=LLM_MAX_TOKENS,
            )

        except Exception as e:
            raise LLMProcessingError(f"Groq API call failed: {e}") from e

        try:
            raw = self._strip_markdown(response.choices[0].message.content.strip())
            ai_data = json.loads(raw)
        except (json.JSONDecodeError, ValueError) as e:
            raise LLMProcessingError(f"Failed to parse LLM response as JSON: {e}") from e

        return PipelineResponse(
            status="success",
            ai_response_text=ai_data.get("ai_response_text", "I have processed your request."),
            confidence_score=float(ai_data.get("confidence_score", 1.0)),
            data=ai_data,
        ).model_dump()


# Module-level singleton
voice_pipeline = VoicePipelineOrchestrator()
