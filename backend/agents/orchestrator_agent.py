"""
agents/orchestrator_agent.py

Single responsibility: coordinate a voice-pipeline request.

Sprint 3.1 flow:
  1. Classify intent
  2. Extract facts from user utterance → SessionMemoryService
  3. Build memory context block
  4. Resolve agent
  5. Execute agent (LLM call via pipeline)
  6. If report agent AND slots complete:
       a. Second LLM call with REPORT_GENERATION_PROMPT → full content
       b. ToolExecutorService → PDF or PPTX
  7. Add turn to session memory
  8. Return normalised result dict

What this class does NOT do:
  - No LLM client ownership
  - No document generation (ToolExecutorService)
  - No TTS, no HTTP concerns
  - No slot collection (ReportAgent + SessionMemoryService)
  - No prompt building (each agent)
"""
import logging
from typing import Optional

from agents.base_agent import AgentInput, AgentOutput, BaseAgent
from registry.agent_registry import registry
from config import get_model, LLM_TEMPERATURE, LLM_MAX_TOKENS, COMPANY_NAME, REPORT_HISTORY_WINDOW, REPORT_MAX_TOKENS
from constants import (
    ERR_REPORT_LLM_FAILED, ERR_REPORT_BAD_FORMAT, ERR_REPORT_NO_SECTIONS,
    ERR_REPORT_FILE_SAVE_FAILED, MSG_REPORT_READY,
    MSG_PLEASE_SAY_SOMETHING, MSG_HOW_CAN_I_HELP,
)
from graph.graph_repository import graph_repo
from prompts.system_prompts import VOICE_AGENT_PROMPT, REPORT_GENERATION_PROMPT
from prompts.template_engine import render
from services.intent_classifier import Intent, IntentClassifier
from services.session_memory import ISessionMemory
from services.fact_extractor import FactExtractorService
from services.tool_executor import ToolExecutorService
from utils import extract_spoken_text

_log = logging.getLogger(__name__)


class OrchestratorAgent:
    """
    Coordinates all voice-pipeline requests.

    Public contract:
        run(user_text, history, session_id) -> dict
        {
            "status":           "success" | "ignored",
            "ai_response_text": str,
            "confidence_score": float,
            "data":             dict,
        }
    """

    def __init__(self, pipeline, memory: ISessionMemory) -> None:
        self._pipeline = pipeline
        self._memory   = memory

    async def run(self, user_text: str, history: list, session_id: str = "") -> dict:
        if not user_text.strip():
            return {
                "status": "ignored",
                "ai_response_text": MSG_PLEASE_SAY_SOMETHING,
                "confidence_score": 0.0,
                "data": {},
            }

        memory_context = self._memory.get_context_block(session_id) if session_id else ""
        agent: Optional[BaseAgent] = self._resolve_agent(user_text, session_id)

        agent_input = AgentInput(
            user_text=user_text,
            session_history=history,
            session_id=session_id,
            memory_context=memory_context,
        )

        if agent:
            system_prompt = agent.build_prompt(agent_input)
            model         = agent.config.model
            temperature   = agent.config.temperature
            max_tokens    = agent.config.max_tokens
        else:
            system_prompt = render(VOICE_AGENT_PROMPT, {
                "agent_name":     "Aria",
                "company":        COMPANY_NAME,
                "memory_context": memory_context,
            })
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
            spoken = extract_spoken_text(raw_output, MSG_HOW_CAN_I_HELP)
            if session_id:
                facts = await FactExtractorService.extract_async(user_text, spoken)
                for k, v in facts.items():
                    self._memory.set_fact(session_id, k, v)
                if facts:
                    _log.info("[Orchestrator] facts_extracted=%s session=%s", facts, session_id)
                self._memory.add_turn(session_id, user_text, spoken)
            return {
                "status":           "success",
                "ai_response_text": spoken,
                "confidence_score": float(raw_output.get("confidence_score", 1.0)),
                "data":             raw_output,
            }

        if agent.agent_type() == "report" and session_id:
            agent_output: AgentOutput = agent.post_process(raw_output, session_id=session_id)
        else:
            agent_output: AgentOutput = agent.post_process(raw_output)

        if session_id:
            facts = await FactExtractorService.extract_async(user_text, agent_output.text)
            for k, v in facts.items():
                self._memory.set_fact(session_id, k, v)
            if facts:
                _log.info("[Orchestrator] facts_extracted=%s session=%s", facts, session_id)
            self._memory.add_turn(session_id, user_text, agent_output.text)

        result = {
            "status":           "success",
            "ai_response_text": agent_output.text,
            "confidence_score": agent_output.confidence,
            "data":             agent_output.data,
        }

        if agent.agent_type() == "report" and session_id and self._memory.is_slots_complete(session_id):
            result = await self._complete_report(result, session_id)

        return result

    async def _complete_report(self, result: dict, session_id: str) -> dict:
        """
        Generate full report content via a second LLM call, then execute the tool.

        Context sent to LLM:
          - memory_context  : extracted facts + filled slots (from SessionMemoryService)
          - recent_turns    : last REPORT_HISTORY_WINDOW raw turns (conversation narrative)

        Failures are logged with full diagnostic detail — never silently swallowed.
        """
        slots          = self._memory.get_slots(session_id)
        memory_context = self._memory.get_context_block(session_id)
        output_format  = slots.get("output_format", "PDF")
        topic          = slots.get("topic", "Report")
        page_count     = slots.get("page_count", 3)
        report_title   = result["data"].get("report_title") or topic

        # Full context for report: fetch ALL turns from Neo4j (persistent store)
        # so the LLM sees the complete conversation from turn 1, not just the
        # last N turns held in RAM. This is the core "20-minute chat → full report" fix.
        full_history = graph_repo.get_full_session_history(session_id)
        if full_history:
            turns_text = "\n".join(
                f"User: {t.get('user_input', '')}\nAssistant: {t.get('ai_response_text', '')}"
                for t in full_history
            )
            full_context = f"{memory_context}\n\n[COMPLETE CONVERSATION HISTORY - USE THIS FOR ALL REPORT CONTENT]\n{turns_text}"
        else:
            # Fallback to in-process RAM turns if Neo4j is unavailable
            recent_turns = self._memory.get_recent_turns(session_id)
            turns_text = "\n".join(
                f"User: {t.get('user_input', '')}\nAssistant: {t.get('ai_response_text', '')}"
                for t in recent_turns
            )
            full_context = f"{memory_context}\n\n[RECENT CONVERSATION TURNS]\n{turns_text}" if turns_text else memory_context

        _log.info(
            "[Orchestrator] report_generation_start session=%s topic=%r format=%s pages=%s "
            "context_len=%d history_turns=%d",
            session_id, topic, output_format, page_count,
            len(full_context), len(full_history) if full_history else 0,
        )

        gen_prompt = render(REPORT_GENERATION_PROMPT, {
            "company":        COMPANY_NAME,
            "topic":          topic,
            "page_count":     str(page_count),
            "output_format":  output_format,
            "report_title":   report_title,
            "memory_context": full_context,
        })

        try:
            gen_output = await self._pipeline.execute(
                system_prompt=gen_prompt,
                model=get_model(),
                temperature=LLM_TEMPERATURE,
                max_tokens=REPORT_MAX_TOKENS,   # higher budget for full report JSON
                history=[],
                user_input=(
                    f"Generate a {page_count}-page {output_format} report on: {topic}"
                ),
            )
        except Exception as e:
            _log.error(
                "[Orchestrator] report_content_llm_failed session=%s "
                "error_type=%s error_detail=%s",
                session_id, type(e).__name__, str(e),
            )
            result["ai_response_text"] = ERR_REPORT_LLM_FAILED
            return result

        # RC-5 fix: detailed diagnostic logging on parse outcome so failures
        # are immediately visible in logs instead of surfacing as silent errors.
        present_keys = list(gen_output.keys())
        sections     = gen_output.get("sections") or []
        _log.info(
            "[Orchestrator] report_llm_response session=%s keys=%s sections_count=%d "
            "intent=%s data_complete=%s",
            session_id, present_keys, len(sections),
            gen_output.get("intent"), gen_output.get("data_complete"),
        )

        if not sections:
            # Distinguish between a parse failure (only CHAT fallback keys present)
            # and a genuine empty-sections response from the LLM.
            is_parse_failure = (
                present_keys == ["intent", "ai_response_text", "confidence_score"]
                and gen_output.get("intent") == "CHAT"
            )
            if is_parse_failure:
                raw_text = gen_output.get("ai_response_text", "")
                _log.error(
                    "[Orchestrator] report_json_parse_failed session=%s "
                    "raw_response_length=%d raw_preview=%.200r",
                    session_id, len(raw_text), raw_text,
                )
                result["ai_response_text"] = ERR_REPORT_BAD_FORMAT
            else:
                _log.error(
                    "[Orchestrator] report_no_sections session=%s keys=%s",
                    session_id, present_keys,
                )
                result["ai_response_text"] = ERR_REPORT_NO_SECTIONS
            return result

        report_data = {
            **gen_output,
            "report_title": gen_output.get("report_title") or report_title,
            "structured_data": gen_output.get("structured_data") or [
                {"item": "Topic",        "value": topic},
                {"item": "Pages/Slides", "value": str(page_count)},
                {"item": "Format",       "value": output_format},
            ],
            "ai_summary": gen_output.get("ai_summary") or f"Report on {topic}.",
        }

        tool_urls = ToolExecutorService.execute(output_format, report_data, session_id)
        _log.info("[Orchestrator] tool_result session=%s urls=%s", session_id, tool_urls)

        if not tool_urls.get("download_url") and not tool_urls.get("pptx_url"):
            _log.error(
                "[Orchestrator] tool_no_output session=%s format=%s", session_id, output_format
            )
            result["ai_response_text"] = ERR_REPORT_FILE_SAVE_FAILED
            return result

        self._memory.clear_slots(session_id)

        result["data"]             = {**result["data"], **tool_urls, **report_data}
        result["ai_response_text"] = extract_spoken_text(gen_output, MSG_REPORT_READY)
        return result

    def _resolve_agent(self, user_text: str, session_id: str = "") -> Optional[BaseAgent]:
        # Sticky routing: if slot collection is already in progress for this session,
        # keep routing to ReportAgent regardless of intent on this turn.
        # This handles follow-up answers like "3 pages" or "PDF" that contain
        # no action verb or document noun and would otherwise fall through to VoiceAgent.
        if session_id and self._memory.is_report_in_progress(session_id):
            agent = registry.get_by_type("report")
            if agent:
                _log.info(
                    "[Orchestrator] sticky_route=report session=%s reason=slot_collection_in_progress",
                    session_id,
                )
                return agent

        intent   = IntentClassifier.classify(user_text)
        type_map = {
            Intent.RESTRICTED_REQUEST: "compliance",
            Intent.REPORT_REQUEST:     "report",
        }
        agent_type = type_map.get(intent, "voice")
        agent      = registry.get_by_type(agent_type) or registry.get_active()
        _log.info(
            "[Orchestrator] intent=%s agent=%s",
            intent.value,
            agent.agent_type() if agent else "NONE",
        )
        return agent
