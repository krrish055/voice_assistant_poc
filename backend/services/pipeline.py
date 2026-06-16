import json
import re
from typing import Any

from openai import AsyncOpenAI
from pydantic import BaseModel, field_validator

from base import BasePipeline
from config import GROQ_BASE_URL, get_groq_api_key, get_model, LLM_TEMPERATURE, LLM_MAX_TOKENS
from exceptions import LLMProcessingError
from registry.agent_registry import registry
from agents.base_agent import AgentInput
from prompts.system_prompts import REPORT_SYSTEM_PROMPT
from prompts.template_engine import render


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_text_from_llm_output(raw: dict) -> str:
    """Pull the human-readable spoken reply out of a parsed LLM output dict.
    Never returns a raw JSON string."""
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


def _extract_known_slots(history: list) -> dict[str, Any]:
    """Scan session history to recover already-confirmed report slots so the
    system prompt can tell the LLM not to ask for them again."""
    slots: dict[str, Any] = {}
    for turn in history:
        # Slots may be stored in the structured JSON that was saved to Neo4j
        # before the sanitisation fix was in place.
        ai_raw = turn.get("ai_response_text", "")
        if isinstance(ai_raw, str) and ai_raw.strip().startswith("{"):
            try:
                parsed = json.loads(ai_raw)
                for entry in parsed.get("structured_data", []):
                    item, value = entry.get("item"), entry.get("value")
                    if item and value and str(value).lower() not in ("unknown", "", "null", "none"):
                        slots[item] = value
                if parsed.get("report_title"):
                    slots["report_title"] = parsed["report_title"]
            except Exception:
                pass
        # Also check raw user turns for explicit topic mentions (belt-and-braces)
        user_raw = turn.get("user_input", "")
        if user_raw and not slots.get("Topic"):
            slots["_user_context"] = user_raw[:200]
    return slots


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
        # e.g. "Hello Krish, I can help. { "intent": ... }"
        brace_idx = raw.find('{')
        if brace_idx > 0:
            prefix_text = raw[:brace_idx].strip()
            json_part   = raw[brace_idx:].strip()
            try:
                parsed = json.loads(json_part)
                if isinstance(parsed, dict):
                    # Prefer the ai_response_text inside JSON; if missing, use the prefix
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
            # Skip incomplete turns — they corrupt context
            if not user_turn or not ai_turn:
                continue
            # Never inject a raw JSON blob as an assistant message
            ai_turn = _sanitise_ai_text(ai_turn)
            if ai_turn:
                messages.append({"role": "user",      "content": user_turn})
                messages.append({"role": "assistant", "content": ai_turn})
        messages.append({"role": "user", "content": user_input})
        return messages

    async def execute_stream_pipeline(self, raw_text_input: str, history: list) -> dict:
        if not raw_text_input.strip():
            return PipelineResponse(
                status="ignored", ai_response_text="Please say something.", confidence_score=0.0
            ).model_dump()

        agent = registry.get_active()

        if agent:
            agent_input = AgentInput(
                user_text=raw_text_input,
                session_history=history,
            )
            system_prompt = agent.build_prompt(agent_input)
            model = agent.config.model
            temperature = agent.config.temperature
            max_tokens = agent.config.max_tokens
        else:
            # Inject already-confirmed slots so the LLM won't re-ask for them
            known_slots = _extract_known_slots(history)
            slot_hint = ""
            if known_slots:
                slot_lines = "\n".join(
                    f"  - {k}: {v}" for k, v in known_slots.items()
                    if not k.startswith("_")
                )
                user_ctx = known_slots.get("_user_context", "")
                slot_hint = (
                    "\n\n[ALREADY COLLECTED FROM THIS SESSION — treat as confirmed, do NOT ask again]\n"
                    + (slot_lines or "")
                    + (f"\n\nRecent user context: {user_ctx}" if user_ctx else "")
                )
            system_prompt = (
                render(REPORT_SYSTEM_PROMPT, {"agent_name": "Aria", "company": "InTimeTec"})
                + slot_hint
            )
            model, temperature, max_tokens = get_model(), LLM_TEMPERATURE, LLM_MAX_TOKENS

        try:
            messages = self._build_messages(system_prompt, history, raw_text_input)
            response = await self._get_client().chat.completions.create(
                model=model, messages=messages, temperature=temperature, max_tokens=max_tokens,
            )
        except Exception as e:
            raise LLMProcessingError(f"LLM call failed: {e}") from e

        raw_output = self._parse_llm_output(response.choices[0].message.content.strip())

        if agent:
            agent_output = agent.post_process(raw_output)
            return PipelineResponse(
                status="success",
                ai_response_text=agent_output.text,
                confidence_score=agent_output.confidence,
                data=agent_output.data,
            ).model_dump()

        return PipelineResponse(
            status="success",
            ai_response_text=_extract_text_from_llm_output(raw_output),
            confidence_score=float(raw_output.get("confidence_score", 1.0)),
            data=raw_output,
        ).model_dump()


voice_pipeline = VoicePipeline()
