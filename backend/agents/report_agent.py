"""
agents/report_agent.py

Single responsibility: drive the slot-collection conversation for report requests.

What this agent does:
  - Builds the slot-collection prompt with confirmed slots injected
  - Parses LLM response to extract newly confirmed slots
  - Updates MemoryService with any new slots
  - Returns a conversational spoken reply and slot-complete state

What this agent does NOT do:
  - Generate PDF or PPTX
  - Call GeneratorService
  - Store memory internally
  - Perform tool execution
  - Generate report content, sections, or summaries
"""
from dataclasses import dataclass, field
from typing import Dict, Optional

from agents.base_agent import BaseAgent, AgentConfig, AgentInput, AgentOutput
from prompts.template_engine import build_prompt, PromptContext
from prompts.system_prompts import REPORT_AGENT_PROMPT
from services.memory_service import IMemoryService
from config import get_model, LLM_TEMPERATURE, LLM_MAX_TOKENS, COMPANY_NAME
from utils import extract_spoken_text


@dataclass
class ReportAgent(BaseAgent):
    """Slot-collection agent for report requests."""

    memory: Optional[IMemoryService] = field(default=None)

    def agent_type(self) -> str:
        return "report"

    def build_prompt(self, agent_input: AgentInput) -> str:
        ctx = PromptContext(
            agent_name=self.name,
            company=COMPANY_NAME,
            agent_role="report",
            session_history=agent_input.session_history,
            compliance_rules=[],
        )
        return build_prompt(self.config.system_prompt or REPORT_AGENT_PROMPT, ctx)

    def post_process(self, raw_output: Dict, session_id: str = "") -> AgentOutput:
        """
        Parse LLM output, update memory with any newly confirmed slots,
        return spoken reply and completion state.
        """
        if session_id and self.memory:
            self._sync_slots(raw_output, session_id)
            slots_complete = self.memory.is_complete(session_id)
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
                "data_complete": slots_complete,
            },
            confidence=float(raw_output.get("confidence_score", 1.0)),
        )

    def _sync_slots(self, raw: Dict, session_id: str) -> None:
        """Persist any newly confirmed slots from the LLM response into memory."""
        if raw.get("topic"):
            self.memory.update_slot(session_id, "topic", raw["topic"])
        if raw.get("page_count"):
            try:
                self.memory.update_slot(session_id, "page_count", int(raw["page_count"]))
            except (ValueError, TypeError):
                pass
        fmt = (raw.get("output_format") or "").upper()
        if fmt in ("PDF", "PPTX"):
            self.memory.update_slot(session_id, "output_format", fmt)


def create_report_agent(memory: IMemoryService) -> ReportAgent:
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
