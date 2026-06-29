import json
import logging
import re

from openai import AsyncOpenAI
from pydantic import BaseModel, field_validator

from base import BasePipeline
from config import GROQ_BASE_URL, get_groq_api_key, get_model, LLM_TEMPERATURE, LLM_MAX_TOKENS, COMPANY_NAME
from exceptions import LLMProcessingError
from prompts.system_prompts import VOICE_AGENT_PROMPT
from prompts.template_engine import render
from utils import extract_spoken_text


def _sanitise_ai_text(value: str) -> str:
    """Guard: if a JSON blob ends up in a text field, extract the spoken part."""
    stripped = value.strip()
    if stripped.startswith("{"):
        try:
            parsed = json.loads(stripped)

            # If this JSON looks like a structured report/tool payload, do not extract a spoken text.
            # Returning plain spoken text here can cause the later JSON detection/guard to be bypassed.
            if isinstance(parsed, dict) and any(
                k in parsed for k in ("sections", "structured_data", "download_url", "pptx_url")
            ):
                return "[Previous structured response omitted]"

            clean = extract_spoken_text(parsed)
            return clean or "I'm sorry, I couldn't formulate a response. Please try again."
        except Exception:
            pass
    return value



class PipelineResponse(BaseModel):
    status: str
    ai_response_text: str
    confidence_score: float
    data: dict = {}

    @field_validator("ai_response_text")
    @classmethod
    def must_be_plain_text(cls, v: str) -> str:
        return _sanitise_ai_text(v)


class VoicePipeline(BasePipeline):

    def __init__(self):
        self._client: AsyncOpenAI | None = None

    def _get_client(self) -> AsyncOpenAI:
        if self._client is None:
            self._client = AsyncOpenAI(api_key=get_groq_api_key(), base_url=GROQ_BASE_URL)
        return self._client

    @staticmethod
    def _parse_llm_output(raw: str) -> dict:
        # Strip markdown code fences (``` or ```json)
        raw = raw.strip()
        raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.IGNORECASE)
        raw = re.sub(r"```\s*$", "", raw)  # strip closing fence regardless of newlines
        raw = raw.strip()

        # Find the first { to skip any preamble text before JSON
        brace_idx = raw.find('{')
        if brace_idx > 0:
            raw = raw[brace_idx:]
        # Trim anything after the last }
        last_brace = raw.rfind('}')
        if last_brace != -1 and last_brace < len(raw) - 1:
            raw = raw[:last_brace + 1]

        # Sanitize literal control characters inside JSON strings that make json.loads fail.
        # LLMs often embed real \n, \t, \r inside string values instead of escaped \\n etc.
        def _fix_control_chars(s: str) -> str:
            result = []
            in_string = False
            i = 0
            while i < len(s):
                c = s[i]
                if c == '\\' and in_string:
                    result.append(c)
                    if i + 1 < len(s):
                        result.append(s[i + 1])
                        i += 2
                    else:
                        i += 1
                    continue
                if c == '"':
                    in_string = not in_string
                elif in_string and c == '\n':
                    result.append('\\n')
                    i += 1
                    continue
                elif in_string and c == '\r':
                    result.append('\\r')
                    i += 1
                    continue
                elif in_string and c == '\t':
                    result.append('\\t')
                    i += 1
                    continue
                result.append(c)
                i += 1
            return ''.join(result)

        try:
            parsed = json.loads(raw)
        except (json.JSONDecodeError, ValueError):
            try:
                parsed = json.loads(_fix_control_chars(raw))
            except (json.JSONDecodeError, ValueError):
                parsed = None

        if isinstance(parsed, dict):
            # Unwrap: LLM sometimes nests the real JSON payload as a string inside ai_response_text
            inner_text = (parsed.get("ai_response_text") or "").strip()
            if inner_text.startswith("{"):
                try:
                    inner = json.loads(inner_text)
                    if not isinstance(inner, dict):
                        inner = None
                except (json.JSONDecodeError, ValueError):
                    try:
                        inner = json.loads(_fix_control_chars(inner_text))
                    except (json.JSONDecodeError, ValueError):
                        inner = None
                if isinstance(inner, dict) and inner.get("sections"):
                    return inner
            return parsed

        # Truncated JSON recovery: try to close incomplete JSON
        for closing in (']}', ']}}'):
            for candidate in (raw, _fix_control_chars(raw)):
                try:
                    parsed = json.loads(candidate + closing)
                    if isinstance(parsed, dict) and parsed.get("sections"):
                        logging.getLogger(__name__).warning(
                            "[Pipeline] recovered truncated JSON with %d sections", len(parsed["sections"])
                        )
                        return parsed
                except (json.JSONDecodeError, ValueError):
                    pass

        return {"intent": "CHAT", "ai_response_text": raw, "confidence_score": 1.0}

    @staticmethod
    def _build_messages(system_prompt: str, history: list, user_input: str) -> list:
        messages = [{"role": "system", "content": system_prompt}]
        for turn in history:
            user_turn = (turn.get("user_input") or "").strip()
            ai_turn   = (turn.get("ai_response_text") or "").strip()
            if not user_turn or not ai_turn:
                continue
            # Replay sanitization: prevent structured report/tool payloads from being replayed
            # as assistant content (which can cause provider tool-role protocol errors).
            ai_turn = _sanitise_ai_text(ai_turn)

            stripped = ai_turn.lstrip()
            if stripped.startswith("{"):
                try:
                    parsed = json.loads(stripped)
                    if isinstance(parsed, dict) and any(
                        k in parsed for k in (
                            "sections",
                            "structured_data",
                            "download_url",
                            "pptx_url",
                        )
                    ):
                        ai_turn = "[Previous structured response omitted]"
                except Exception:
                    # If parsing fails, preserve normal behavior (already sanitised by _sanitise_ai_text).
                    pass

            if ai_turn:
                messages.append({"role": "user",      "content": user_turn})
                messages.append({"role": "assistant", "content": ai_turn})
        messages.append({"role": "user", "content": user_input})
        return messages


    async def execute(self, system_prompt: str, model: str, temperature: float,
                      max_tokens: int, history: list, user_input: str) -> dict:
        """Pure LLM executor. Returns the raw parsed output dict."""
        _log_pipe = logging.getLogger(__name__)
        try:
            messages = self._build_messages(system_prompt, history, user_input)
            response = await self._get_client().chat.completions.create(
                model=model, messages=messages, temperature=temperature, max_tokens=max_tokens,
            )
        except Exception as e:
            raise LLMProcessingError(f"LLM call failed: {e}") from e
        choice = response.choices[0]
        if choice.finish_reason == "length":
            _log_pipe.warning(
                "[Pipeline] LLM output truncated (finish_reason=length) model=%s max_tokens=%s",
                model, max_tokens,
            )
        raw_content = choice.message.content.strip()
        if choice.finish_reason == "length" or "sections" in raw_content[:50] or not raw_content.startswith("{"):
            _log_pipe.info("[Pipeline] finish_reason=%s raw_head=%s", choice.finish_reason, raw_content[:400])
        return self._parse_llm_output(raw_content)

    async def execute_stream_pipeline(self, raw_text_input: str, history: list) -> dict:
        """Backward-compatible agent-unaware entry point for admin ChatService."""
        if not raw_text_input.strip():
            return PipelineResponse(
                status="ignored", ai_response_text="Please say something.", confidence_score=0.0
            ).model_dump()

        system_prompt = render(VOICE_AGENT_PROMPT, {"agent_name": "Aria", "company": COMPANY_NAME})
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
            ai_response_text=extract_spoken_text(raw_output),
            confidence_score=float(raw_output.get("confidence_score", 1.0)),
            data=raw_output,
        ).model_dump()
