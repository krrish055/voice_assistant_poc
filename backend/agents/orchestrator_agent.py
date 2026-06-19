import logging
from typing import Optional

from agents.base_agent import AgentInput, AgentOutput, BaseAgent
from approvals.service import ApprovalService
from config import get_model, LLM_TEMPERATURE, LLM_MAX_TOKENS, COMPANY_NAME, REPORT_HISTORY_WINDOW, REPORT_MAX_TOKENS
from constants import (
    ERR_REPORT_LLM_FAILED, ERR_REPORT_BAD_FORMAT, ERR_REPORT_NO_SECTIONS,
    ERR_REPORT_FILE_SAVE_FAILED,
    MSG_PLEASE_SAY_SOMETHING, MSG_HOW_CAN_I_HELP,
    MSG_APPROVAL_PENDING,
)
from events.dispatcher import EventDispatcher
from graph.graph_repository import graph_repo
from jobs.service import JobService
from prompts.system_prompts import VOICE_AGENT_PROMPT, REPORT_GENERATION_PROMPT
from prompts.template_engine import render
from registry.agent_registry import registry
from services.fact_extractor import FactExtractorService
from services.intent_classifier import Intent, IntentClassifier
from services.session_memory import ISessionMemory
from services.tool_executor import ToolExecutorService
from utils import extract_spoken_text

_log = logging.getLogger(__name__)


class OrchestratorAgent:

    def __init__(
        self,
        pipeline,
        memory: ISessionMemory,
        approval_service: ApprovalService,
        job_service: JobService,
        dispatcher: EventDispatcher,
    ) -> None:
        self._pipeline         = pipeline
        self._memory           = memory
        self._approval_service = approval_service
        self._job_service      = job_service
        self._dispatcher       = dispatcher

    async def run(
        self,
        user_text: str,
        history: list,
        session_id: str = "",
        user_id: str = "",
    ) -> dict:
        if not user_text.strip():
            return {
                "status": "ignored",
                "ai_response_text": MSG_PLEASE_SAY_SOMETHING,
                "confidence_score": 0.0,
                "data": {},
            }
        return await self._execute_pipeline(user_text, history, session_id, user_id)

    async def _execute_pipeline(
        self,
        user_text: str,
        history: list,
        session_id: str,
        user_id: str,
    ) -> dict:
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

        intent = IntentClassifier.classify(user_text)
        if intent == Intent.RESTRICTED_REQUEST and session_id:
            return await self._handle_restricted(user_text, session_id, user_id, raw_output)

        if not agent:
            spoken = extract_spoken_text(raw_output, MSG_HOW_CAN_I_HELP)
            if session_id:
                facts = await FactExtractorService.extract_async(user_text, spoken)
                for k, v in facts.items():
                    self._memory.set_fact(session_id, k, v)
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
            self._memory.add_turn(session_id, user_text, agent_output.text)

        result = {
            "status":           "success",
            "ai_response_text": agent_output.text,
            "confidence_score": agent_output.confidence,
            "data":             agent_output.data,
        }

        if agent.agent_type() == "report" and session_id:
            # Always fill defaults and generate immediately — no slot loop
            slots = self._memory.get_slots(session_id)
            if not slots.get("topic"):
                facts = self._memory.get_facts(session_id)
                topic = (
                    facts.get("project") or facts.get("business") or
                    facts.get("topic") or facts.get("name") or "General Report"
                )
                self._memory.update_slot(session_id, "topic", topic)
            if not slots.get("page_count"):
                self._memory.update_slot(session_id, "page_count", 3)
            if not slots.get("output_format"):
                self._memory.update_slot(session_id, "output_format", "PDF")
            result = await self._generate_report(result, session_id, user_id)

        return result

    async def _handle_restricted(
        self, user_text: str, session_id: str, user_id: str, raw_output: dict
    ) -> dict:
        approval = await self._approval_service.create(
            session_id=session_id,
            user_id=user_id,
            request_type="restricted_voice_request",
            payload={"user_text": user_text, "raw_output": raw_output},
        )
        _log.info("[Orchestrator] approval_created id=%s session=%s", approval.id, session_id)
        return {
            "status":           "pending_approval",
            "ai_response_text": MSG_APPROVAL_PENDING,
            "confidence_score": 1.0,
            "data":             {"approval_id": approval.id},
        }

    async def _generate_report(self, result: dict, session_id: str, user_id: str) -> dict:
        slots          = self._memory.get_slots(session_id)
        memory_context = self._memory.get_context_block(session_id)
        full_history   = graph_repo.get_full_session_history(session_id)

        turns_text = "\n".join(
            f"User: {t.get('user_input', '')}\nAssistant: {t.get('ai_response_text', '')}"
            for t in full_history
        )
        full_context = (
            f"{memory_context}\n\n[COMPLETE CONVERSATION HISTORY]\n{turns_text}"
            if full_history else memory_context
        )

        topic         = slots.get("topic", "Report")
        page_count    = slots.get("page_count", 3)
        output_format = slots.get("output_format", "PDF")
        report_title  = result["data"].get("report_title") or topic

        gen_prompt = render(REPORT_GENERATION_PROMPT, {
            "company":        COMPANY_NAME,
            "topic":          topic,
            "page_count":     str(page_count),
            "output_format":  output_format,
            "report_title":   report_title,
            "memory_context": full_context,
        })

        from services.pipeline import VoicePipeline
        gen_output = await VoicePipeline().execute(
            system_prompt=gen_prompt,
            model=get_model(),
            temperature=LLM_TEMPERATURE,
            max_tokens=REPORT_MAX_TOKENS,
            history=[],
            user_input=f"Generate a {page_count}-page {output_format} report on: {topic}",
        )

        sections = gen_output.get("sections") or []
        if not sections:
            _log.error("[Orchestrator] report LLM returned no sections session=%s", session_id)
            result["ai_response_text"] = "Sorry, I could not generate the report. Please try again."
            return result

        report_data = {
            **gen_output,
            "report_title":    gen_output.get("report_title") or report_title,
            "structured_data": gen_output.get("structured_data") or [
                {"item": "Topic",  "value": topic},
                {"item": "Pages",  "value": str(page_count)},
                {"item": "Format", "value": output_format},
            ],
            "ai_summary": gen_output.get("ai_summary") or f"Report on {topic}.",
        }

        tool_urls = ToolExecutorService.execute(output_format, report_data, session_id)
        self._memory.clear_slots(session_id)
        _log.info("[Orchestrator] report_generated session=%s urls=%s", session_id, tool_urls)

        result["status"]           = "success"
        result["ai_response_text"] = gen_output.get("ai_response_text") or "Your report has been generated."
        result["data"]             = {**result["data"], **tool_urls}
        result["download_url"]     = tool_urls.get("download_url")
        result["pptx_url"]         = tool_urls.get("pptx_url")
        return result

    def _resolve_agent(self, user_text: str, session_id: str = "") -> Optional[BaseAgent]:
        intent   = IntentClassifier.classify(user_text)
        type_map = {
            Intent.RESTRICTED_REQUEST: "compliance",
            Intent.REPORT_REQUEST:     "report",
        }
        agent_type = type_map.get(intent, "voice")
        agent      = registry.get_by_type(agent_type) or registry.get_active()
        _log.info("[Orchestrator] intent=%s agent=%s", intent.value, agent.agent_type() if agent else "NONE")
        return agent
