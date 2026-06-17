"""
OrchestratorAgent — Sprint 2
Single responsibility: coordinate a voice-pipeline request.

Sprint 2: _resolve_agent() uses IntentClassifier for type-based dispatch.
Sprint 3 extension: only _resolve_agent() changes again — nothing else.

What this class does NOT do:
  - No LLM client ownership
  - No Neo4j access
  - No document generation
  - No TTS
  - No HTTP concerns
  - No business logic
  - No intent classification logic (delegated to IntentClassifier)
"""
import json
import logging
from typing import Any, Optional

from agents.base_agent import AgentInput, BaseAgent
from registry.agent_registry import registry
from config import get_model, LLM_TEMPERATURE, LLM_MAX_TOKENS
from prompts.system_prompts import REPORT_SYSTEM_PROMPT
from prompts.template_engine import render
from services.intent_classifier import Intent, IntentClassifier


# ---------------------------------------------------------------------------
# Module-level helpers
# Moved verbatim from pipeline.py — behaviour is byte-for-byte identical.
# Kept here so orchestrator_agent.py has zero imports from services.pipeline,
# eliminating the circular-import risk entirely.
# ---------------------------------------------------------------------------

def _extract_text_from_llm_output(raw: dict) -> str:
    """Pull the human-readable spoken reply from a parsed LLM output dict.
    Never returns a raw JSON string."""
    text = raw.get("ai_response_text", "")
    if not isinstance(text, str) or not text.strip():
        text = raw.get("ai_summary", "")
    if not isinstance(text, str) or not text.strip():
        sections = raw.get("sections") or []
        text = sections[0].get("body", "") if sections else ""
    return (text or "").strip()


def _extract_known_slots(history: list) -> dict[str, Any]:
    """Recover already-confirmed report slots from session history so the LLM
    is not asked for information it already received in a prior turn."""
    slots: dict[str, Any] = {}
    for turn in history:
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
        user_raw = turn.get("user_input", "")
        if user_raw and not slots.get("Topic"):
            slots["_user_context"] = user_raw[:200]
    return slots


def _build_fallback_prompt(history: list) -> str:
    """System prompt used when no agent is active in the registry.
    Identical in content to the former pipeline.py else-branch."""
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
    return render(REPORT_SYSTEM_PROMPT, {"agent_name": "Aria", "company": "InTimeTec"}) + slot_hint


# ---------------------------------------------------------------------------
# OrchestratorAgent
# ---------------------------------------------------------------------------

class OrchestratorAgent:
    """
    Coordinates all voice-pipeline requests.

    Public contract (stable across sprints):
        run(user_text: str, history: list) -> dict
        Return shape:
            {
                "status":           "success" | "ignored",
                "ai_response_text": str,
                "confidence_score": float,
                "data":             dict,
            }

    Sprint 2 multi-agent routing requires ONLY _resolve_agent() to change.
    run(), the pipeline contract, voice_router, and all tests remain untouched.
    """

    _log = logging.getLogger(__qualname__)

    def __init__(self, pipeline) -> None:
        self._pipeline = pipeline  # BasePipeline — injected, never constructed here

    async def run(self, user_text: str, history: list) -> dict:
        """
        Main entry point called by voice_router.

        Flow:
          1. _resolve_agent()      → BaseAgent | None
          2. agent.build_prompt()  → system_prompt str
             (or fallback prompt when no agent is active)
          3. pipeline.execute()    → raw LLM output dict
          4. agent.post_process()  → AgentOutput
             (or plain text extraction for the fallback path)
          5. Return normalised dict
        """
        if not user_text.strip():
            return {
                "status": "ignored",
                "ai_response_text": "Please say something.",
                "confidence_score": 0.0,
                "data": {},
            }

        agent: Optional[BaseAgent] = self._resolve_agent(user_text, history)

        if agent:
            agent_input = AgentInput(user_text=user_text, session_history=history)
            system_prompt = agent.build_prompt(agent_input)
            model         = agent.config.model
            temperature   = agent.config.temperature
            max_tokens    = agent.config.max_tokens
        else:
            system_prompt = _build_fallback_prompt(history)
            model, temperature, max_tokens = get_model(), LLM_TEMPERATURE, LLM_MAX_TOKENS

        raw_output: dict = await self._pipeline.execute(
            system_prompt=system_prompt,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            history=history,
            user_input=user_text,
        )

        if agent:
            agent_output = agent.post_process(raw_output)
            return {
                "status":           "success",
                "ai_response_text": agent_output.text,
                "confidence_score": agent_output.confidence,
                "data":             agent_output.data,
            }

        return {
            "status":           "success",
            "ai_response_text": _extract_text_from_llm_output(raw_output),
            "confidence_score": float(raw_output.get("confidence_score", 1.0)),
            "data":             raw_output,
        }
    def _resolve_agent(
        self,
        user_text: str,
        history: list
    ) -> Optional[BaseAgent]:  # noqa: ARG002

        self._log.info("=" * 80)
        self._log.info("[Orchestrator] _resolve_agent called")
        self._log.info("[Orchestrator] user_text=%r", user_text)
        self._log.info(
            "[Orchestrator] history_length=%s",
            len(history) if history else 0
        )

        intent = IntentClassifier.classify(user_text)

        self._log.info(
            "[Orchestrator] classified_intent=%s",
            intent.value
        )

        if intent == Intent.RESTRICTED_REQUEST:
            self._log.info(
                "[Orchestrator] looking for compliance agent"
            )

            agent = registry.get_by_type("compliance")

            if not agent:
                self._log.warning(
                    "[Orchestrator] compliance agent not found, "
                    "falling back to get_active()"
                )
                agent = registry.get_active()

        elif intent == Intent.REPORT_REQUEST:
            self._log.info(
                "[Orchestrator] looking for report agent"
            )

            agent = registry.get_by_type("report")

            if not agent:
                self._log.warning(
                    "[Orchestrator] report agent not found, "
                    "falling back to get_active()"
                )
                agent = registry.get_active()

        else:
            self._log.info(
                "[Orchestrator] looking for voice agent"
            )

            agent = registry.get_by_type("voice")

            if not agent:
                self._log.warning(
                    "[Orchestrator] voice agent not found, "
                    "falling back to get_active()"
                )
                agent = registry.get_active()

        if agent:
            self._log.info(
                "[Orchestrator] selected agent=%s | class=%s | id=%s | active=%s",
                agent.agent_type(),
                agent.__class__.__name__,
                getattr(agent, "agent_id", "N/A"),
                getattr(agent, "is_active", "N/A"),
            )
        else:
            self._log.error(
                "[Orchestrator] No agent found after fallback chain"
            )

        self._log.info("=" * 80)

        return agent