import logging
import os
from typing import Optional

from agents.base_agent import AgentInput, AgentOutput, BaseAgent
from approvals.service import ApprovalService
from config import get_model, LLM_TEMPERATURE, LLM_MAX_TOKENS, COMPANY_NAME
from constants import (
    MSG_PLEASE_SAY_SOMETHING,
    MSG_HOW_CAN_I_HELP,
    MSG_APPROVAL_PENDING,
)
from events.dispatcher import EventDispatcher
from jobs.service import JobService
from prompts.system_prompts import VOICE_AGENT_PROMPT
from prompts.template_engine import render
from registry.agent_registry import registry
from services.fact_extractor import FactExtractorService
from services.intent_classifier import Intent, IntentClassifier
from services.session_memory import ISessionMemory
from services.report_generation_service import ReportGenerationService
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
        self._pipeline = pipeline
        self._memory = memory
        self._approval_service = approval_service
        self._job_service = job_service
        self._dispatcher = dispatcher
        self._report_generation_service = ReportGenerationService()

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
        # Prefer in-process turn history (always up-to-date) over the graph-fetched
        # history passed in — the graph write is fire-and-forget and may lag by one turn.
        if session_id:
            in_process = self._memory.get_recent_turns(session_id)
            if in_process:
                history = in_process
        memory_context = self._memory.get_context_block(session_id) if session_id else ""
        agent, intent = await self._resolve_agent(user_text, session_id)

        agent_input = AgentInput(
            user_text=user_text,
            session_history=history,
            session_id=session_id,
            memory_context=memory_context,
        )

        if agent:
            system_prompt = agent.build_prompt(agent_input)
            model = agent.config.model
            temperature = agent.config.temperature
            max_tokens = agent.config.max_tokens
        else:
            system_prompt = render(VOICE_AGENT_PROMPT, {
                "agent_name": os.getenv("AGENT_NAME", "Aria"),
                "company": COMPANY_NAME,
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

        if intent == Intent.RESTRICTED_REQUEST and session_id:
            return await self._handle_restricted(user_text, session_id, user_id, raw_output)

        if not agent:
            spoken = extract_spoken_text(raw_output, MSG_HOW_CAN_I_HELP)
            if session_id:
                facts = await FactExtractorService.extract_async(user_text, spoken)
                for k, v in facts.items():
                    self._memory.set_fact(session_id, k, v)
                self._memory.add_turn(session_id, user_text, spoken)
            # If a report was recently generated, always surface its URLs
            last_urls = self._memory.get_last_report_urls(session_id) if session_id else {}
            return {
                "status": "success",
                "ai_response_text": spoken,
                "confidence_score": float(raw_output.get("confidence_score", 1.0)),
                "data": raw_output,
                "download_url": last_urls.get("download_url"),
                "pptx_url": last_urls.get("pptx_url"),
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
            "status": "success",
            "ai_response_text": agent_output.text,
            "confidence_score": agent_output.confidence,
            "data": agent_output.data,
        }

        if agent.agent_type() == "report" and session_id:
            missing_slots = self._memory.missing_slots(session_id)
            if missing_slots:
                _log.info(
                    "[Orchestrator] report_slots_incomplete session=%s missing_slots=%s",
                    session_id,
                    missing_slots,
                )
                result.setdefault("data", {})
                result["data"]["missing_slots"] = missing_slots
                return result

            _log.info(
                "[Orchestrator] report_slots_complete session=%s",
                session_id,
            )
            _log.info(
                "[Orchestrator] report_generation_started session=%s",
                session_id,
            )

            result = await self._generate_report(result, session_id, user_id)

            _log.info(
                "[Orchestrator] report_generation_completed session=%s",
                session_id,
            )

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
            "status": "pending_approval",
            "ai_response_text": MSG_APPROVAL_PENDING,
            "confidence_score": 1.0,
            "data": {"approval_id": approval.id},
        }

    async def _generate_report(self, result: dict, session_id: str, user_id: str) -> dict:
        return await self._report_generation_service.generate(
            result=result,
            session_id=session_id,
            user_id=user_id,
            memory=self._memory,
        )

    async def _resolve_agent(self, user_text: str, session_id: str = "") -> tuple[Optional[BaseAgent], Intent]:
        if session_id and self._memory.is_report_in_progress(session_id):
            agent = registry.get_by_type("report") or registry.get_active()
            _log.info("[Orchestrator] REPORT_IN_PROGRESS bypass agent=%s",
                      agent.agent_type() if agent else "NONE")
            return agent, Intent.REPORT_REQUEST

        intent = await IntentClassifier.classify_async(user_text)
        type_map = {
            Intent.RESTRICTED_REQUEST: "compliance",
            Intent.REPORT_REQUEST: "report",
        }
        agent_type = type_map.get(intent, "voice")
        agent = registry.get_by_type(agent_type) or registry.get_active()
        _log.info("[Orchestrator] intent=%s agent=%s",
                  intent.value, agent.agent_type() if agent else "NONE")
        return agent, intent

