import json
import re

from openai import AsyncOpenAI
from pydantic import BaseModel, field_validator

from base import BasePipeline
from config import GROQ_BASE_URL, get_groq_api_key, get_model, LLM_TEMPERATURE, LLM_MAX_TOKENS
from exceptions import LLMProcessingError
from prompts.system_prompts import REPORT_SYSTEM_PROMPT
from prompts.template_engine import render


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_text_from_llm_output(raw: dict) -> str:
    """Pull the human-readable spoken reply out of a parsed LLM output dict.
    Never returns a raw JSON string.

    NOTE: also defined in orchestrator_agent.py to avoid a circular import.
    Both copies are intentionally identical — do not diverge them.
    """
    text = raw.get("ai_response_text", "")
    if not isinstance(text, str) or not text.strip():
        text = raw.get("ai_summary", "")
    if not isinstance(text, str) or not text.strip():
        sections = raw.get("sections") or []
        text = sections[0].get("body", "") if sections else ""
    return (text or "").strip()


def _sanitise_ai_text(value: str) -> str:
    """If a JSON blob somehow ends up in a text field, extract the spoken part."""
    stripped = value.strip()
    if stripped.startswith("{"):
        try:
            parsed = json.loads(stripped)
            clean = _extract_text_from_llm_output(parsed)
            return clean or "I'm sorry, I couldn't formulate a response. Please try again."
        except Exception:
            pass
    return value


# ---------------------------------------------------------------------------
# Response model
# ---------------------------------------------------------------------------

class PipelineResponse(BaseModel):
    status: str
    ai_response_text: str
    confidence_score: float
    data: dict = {}

    @field_validator("ai_response_text")
    @classmethod
    def must_be_plain_text(cls, v: str) -> str:
        """Last-resort guard at the model boundary."""
        return _sanitise_ai_text(v)


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

class VoicePipeline(BasePipeline):

    def __init__(self):
        self._client: AsyncOpenAI | None = None

    def _get_client(self) -> AsyncOpenAI:
        if self._client is None:
            self._client = AsyncOpenAI(api_key=get_groq_api_key(), base_url=GROQ_BASE_URL)
        return self._client

    @staticmethod
    def _parse_llm_output(raw: str) -> dict:
        # Strip markdown code fences
        raw = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.IGNORECASE)
        raw = re.sub(r"\s*```$", "", raw.strip())

        # Case 1: pure JSON response
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                return parsed
        except (json.JSONDecodeError, ValueError):
            pass

        # Case 2: LLM prepended plain text before the JSON block
        brace_idx = raw.find('{')
        if brace_idx > 0:
            prefix_text = raw[:brace_idx].strip()
            json_part   = raw[brace_idx:].strip()
            try:
                parsed = json.loads(json_part)
                if isinstance(parsed, dict):
                    if not parsed.get("ai_response_text"):
                        parsed["ai_response_text"] = prefix_text
                    return parsed
            except (json.JSONDecodeError, ValueError):
                pass

        # Case 3: plain text fallback
        return {"intent": "CHAT", "ai_response_text": raw, "confidence_score": 1.0}

    @staticmethod
    def _build_messages(system_prompt: str, history: list, user_input: str) -> list:
        messages = [{"role": "system", "content": system_prompt}]
        for turn in history:
            user_turn = (turn.get("user_input") or "").strip()
            ai_turn   = (turn.get("ai_response_text") or "").strip()
            if not user_turn or not ai_turn:
                continue
            ai_turn = _sanitise_ai_text(ai_turn)
            if ai_turn:
                messages.append({"role": "user",      "content": user_turn})
                messages.append({"role": "assistant", "content": ai_turn})
        messages.append({"role": "user", "content": user_input})
        return messages

    async def execute(self, system_prompt: str, model: str, temperature: float,
                      max_tokens: int, history: list, user_input: str) -> dict:
        """Pure LLM executor.
        Accepts a fully-resolved prompt and parameters from the orchestrator.
        Returns the raw parsed output dict. No agent awareness whatsoever.
        """
        try:
            messages = self._build_messages(system_prompt, history, user_input)
            response = await self._get_client().chat.completions.create(
                model=model, messages=messages, temperature=temperature, max_tokens=max_tokens,
            )
        except Exception as e:
            raise LLMProcessingError(f"LLM call failed: {e}") from e
        return self._parse_llm_output(response.choices[0].message.content.strip())

    async def execute_stream_pipeline(self, raw_text_input: str, history: list) -> dict:
        """Backward-compatible, agent-UNAWARE entry point.
        Retained exclusively for the admin ChatService which manages its own
        agent selection independently. Do NOT call this from the voice router —
        use OrchestratorAgent.run() instead.
        """
        if not raw_text_input.strip():
            return PipelineResponse(
                status="ignored", ai_response_text="Please say something.", confidence_score=0.0
            ).model_dump()

        system_prompt = render(REPORT_SYSTEM_PROMPT, {"agent_name": "Aria", "company": "InTimeTec"})
        raw_output = await self.execute(
            system_prompt=system_prompt,
            model=get_model(),
            temperature=LLM_TEMPERATURE,
            max_tokens=LLM_MAX_TOKENS,
            history=history,
            user_input=raw_text_input,
        )
        return PipelineResponse(
            status="success",
            ai_response_text=_extract_text_from_llm_output(raw_output),
            confidence_score=float(raw_output.get("confidence_score", 1.0)),
            data=raw_output,
        ).model_dump()


