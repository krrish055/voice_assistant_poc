"""
agents/orchestrator_agent.py

Single responsibility: coordinate a voice-pipeline request.

Sprint 3 flow:
  1. Classify intent
  2. Resolve agent
  3. Execute agent (LLM call via pipeline)
  4. If report agent AND slots complete → invoke ToolExecutorService
  5. Return normalised result dict

What this class does NOT do:
  - No LLM client ownership
  - No Neo4j access
  - No document generation (delegated to ToolExecutorService)
  - No TTS
  - No HTTP concerns
  - No slot collection (delegated to ReportAgent + MemoryService)
  - No prompt building (delegated to each agent)
"""
import logging
from typing import Optional

from agents.base_agent import AgentInput, AgentOutput, BaseAgent
from registry.agent_registry import registry
from config import get_model, LLM_TEMPERATURE, LLM_MAX_TOKENS, COMPANY_NAME
from prompts.system_prompts import VOICE_AGENT_PROMPT
from prompts.template_engine import render
from services.intent_classifier import Intent, IntentClassifier
from services.memory_service import IMemoryService
from services.tool_executor import ToolExecutorService
from utils import extract_spoken_text


class OrchestratorAgent:
    """
    Coordinates all voice-pipeline requests.

    Public contract (stable across sprints):
        run(user_text, history, session_id) -> dict
        {
            "status":           "success" | "ignored",
            "ai_response_text": str,
            "confidence_score": float,
            "data":             dict,
        }
    """

    _log = logging.getLogger(__qualname__)

    def __init__(self, pipeline, memory: IMemoryService) -> None:
        self._pipeline = pipeline
        self._memory   = memory

    async def run(self, user_text: str, history: list, session_id: str = "") -> dict:
        if not user_text.strip():
            return {
                "status": "ignored",
                "ai_response_text": "Please say something.",
                "confidence_score": 0.0,
                "data": {},
            }

        agent: Optional[BaseAgent] = self._resolve_agent(user_text, history)

        if agent:
            agent_input   = AgentInput(user_text=user_text, session_history=history)
            system_prompt = agent.build_prompt(agent_input)
            model         = agent.config.model
            temperature   = agent.config.temperature
            max_tokens    = agent.config.max_tokens
        else:
            system_prompt = render(VOICE_AGENT_PROMPT, {"agent_name": "Aria", "company": COMPANY_NAME})
            model, temperature, max_tokens = get_model(), LLM_TEMPERATURE, LLM_MAX_TOKENS

        raw_output: dict = await self._pipeline.execute(
            system_prompt=system_prompt,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            history=history,
            user_input=user_text,
        )

        if not agent:
            return {
                "status":           "success",
                "ai_response_text": extract_spoken_text(raw_output, "How can I help you?"),
                "confidence_score": float(raw_output.get("confidence_score", 1.0)),
                "data":             raw_output,
            }

        # Report agent: pass session_id so it can update memory
        if agent.agent_type() == "report" and session_id:
            agent_output: AgentOutput = agent.post_process(raw_output, session_id=session_id)
        else:
            agent_output: AgentOutput = agent.post_process(raw_output)

        result = {
            "status":           "success",
            "ai_response_text": agent_output.text,
            "confidence_score": agent_output.confidence,
            "data":             agent_output.data,
        }

        # Sprint 3: trigger tool execution only when all slots are confirmed
        if agent.agent_type() == "report" and session_id and self._memory.is_complete(session_id):
            slots     = self._memory.get_slots(session_id)
            tool_urls = self._generate_report(slots, agent_output.data, session_id)
            result["data"] = {**agent_output.data, **tool_urls}
            self._memory.clear(session_id)

        return result

    def _generate_report(self, slots: dict, agent_data: dict, session_id: str) -> dict:
        """
        Build the report payload and invoke ToolExecutorService.
        Orchestrator delegates generation — it does not generate anything itself.
        """
        report_data = {
            **agent_data,
            "report_title":  agent_data.get("report_title") or slots.get("topic", "Report"),
            "sections":      agent_data.get("sections") or [],
            "structured_data": agent_data.get("structured_data") or [
                {"item": "Topic",         "value": slots.get("topic", "")},
                {"item": "Pages/Slides",  "value": str(slots.get("page_count", ""))},
                {"item": "Format",        "value": slots.get("output_format", "PDF")},
            ],
            "ai_summary": agent_data.get("ai_summary") or f"Report on {slots.get('topic', '')}.",
        }
        output_format = slots.get("output_format", "PDF")
        urls = ToolExecutorService.execute(output_format, report_data, session_id)
        self._log.info("[Orchestrator] Tool executed format=%s urls=%s", output_format, urls)
        return urls

    def _resolve_agent(self, user_text: str, history: list) -> Optional[BaseAgent]:
        self._log.info("=" * 60)
        self._log.info("[Orchestrator] user_text=%r", user_text)

        intent = IntentClassifier.classify(user_text)
        self._log.info("[Orchestrator] intent=%s", intent.value)

        type_map = {
            Intent.RESTRICTED_REQUEST: "compliance",
            Intent.REPORT_REQUEST:     "report",
        }
        agent_type = type_map.get(intent, "voice")
        agent      = registry.get_by_type(agent_type) or registry.get_active()

        if agent:
            self._log.info(
                "[Orchestrator] agent=%s class=%s id=%s",
                agent.agent_type(), agent.__class__.__name__, agent.id,
            )
        else:
            self._log.error("[Orchestrator] No agent resolved")

        self._log.info("=" * 60)
        return agent
