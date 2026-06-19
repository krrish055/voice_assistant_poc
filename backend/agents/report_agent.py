"""
agents/report_agent.py

Single responsibility: drive slot-collection conversation for report requests.

What this agent does:
  - Injects confirmed slots + memory context into prompt
  - Parses LLM response to extract newly confirmed slots
  - Delegates slot storage to SessionMemoryService
  - Returns conversational spoken reply and completion state

What this agent does NOT do:
  - Generate PDF or PPTX
  - Make LLM calls for report content
  - Store memory internally
  - Execute tools
"""
from dataclasses import dataclass, field
from typing import Dict, Optional

from agents.base_agent import BaseAgent, AgentConfig, AgentInput, AgentOutput
from prompts.template_engine import build_prompt, PromptContext
from prompts.system_prompts import REPORT_AGENT_PROMPT
from services.session_memory import ISessionMemory
from config import get_model, LLM_TEMPERATURE, LLM_MAX_TOKENS, COMPANY_NAME
from utils import extract_spoken_text


@dataclass
class ReportAgent(BaseAgent):
    """Slot-collection agent for report requests."""

    memory: Optional[ISessionMemory] = field(default=None)

    def agent_type(self) -> str:
        return "report"

    def build_prompt(self, agent_input: AgentInput) -> str:
        ctx = PromptContext(
            agent_name=self.name,
            company=COMPANY_NAME,
            agent_role="report",
            session_history=agent_input.session_history,
            compliance_rules=[],
            memory_context=agent_input.memory_context,
        )
        return build_prompt(self.config.system_prompt or REPORT_AGENT_PROMPT, ctx)

    def post_process(self, raw_output: Dict, session_id: str = "") -> AgentOutput:
        if session_id and self.memory:
            self._sync_slots(raw_output, session_id)
            slots_complete = self.memory.is_slots_complete(session_id)
        else:
            slots_complete = bool(raw_output.get("data_complete"))

        text = extract_spoken_text(
            raw_output,
            "I'm gathering the information needed to generate your report."
        )

        return AgentOutput(
            text=text,
            intent="REPORT_REQUEST",
            data={
                **raw_output,
                "slots_complete": slots_complete,
                "data_complete":  slots_complete,
            },
            confidence=float(raw_output.get("confidence_score", 1.0)),
        )

    @staticmethod
    def _is_valid(value) -> bool:
        """Reject None, empty string, and LLM null-placeholder strings."""
        if value is None:
            return False
        return str(value).strip().lower() not in ("", "null", "none")

    def _sync_slots(self, raw: Dict, session_id: str) -> None:
        topic = raw.get("topic")
        if self._is_valid(topic):
            self.memory.update_slot(session_id, "topic", str(topic).strip())

        page = raw.get("page_count")
        if self._is_valid(page):
            try:
                self.memory.update_slot(session_id, "page_count", int(page))
            except (ValueError, TypeError):
                pass

        fmt = (raw.get("output_format") or "").strip().upper()
        if fmt in ("PDF", "PPTX"):
            self.memory.update_slot(session_id, "output_format", fmt)


def create_report_agent(memory: ISessionMemory) -> ReportAgent:
    config = AgentConfig(
        agent_id="agent-4",
        name="Report Agent",
        model=get_model(),
        temperature=LLM_TEMPERATURE,
        max_tokens=LLM_MAX_TOKENS,
        system_prompt=REPORT_AGENT_PROMPT,
    )
    return ReportAgent(
        id="agent-4",
        name="Report Agent",
        config=config,
        is_active=True,
        memory=memory,
    )
