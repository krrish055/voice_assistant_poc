"""
agents/report_agent.py

Single responsibility: handle REPORT_REQUEST intents end-to-end.

Sprint 2 scope: agent_type(), build_prompt(), post_process() only.
Sprint 3 extension: add tool-calling inside post_process() when
data_complete=True. No other file changes required.
"""
from dataclasses import dataclass
from typing import Dict

from agents.base_agent import BaseAgent, AgentConfig, AgentInput, AgentOutput
from prompts.template_engine import build_prompt, PromptContext
from prompts.system_prompts import REPORT_AGENT_PROMPT
from config import get_model, LLM_TEMPERATURE, LLM_MAX_TOKENS

@dataclass
class ReportAgent(BaseAgent):
    """
    Owns the report-generation workflow.

    Future capabilities (Sprint 3+):
      - PDF generation tool call
      - PPTX generation tool call
      - Neo4j data retrieval tool call
      - Human approval workflow
    All additions are isolated to post_process() — nothing outside changes.
    """

    def agent_type(self) -> str:
        return "report"

    def build_prompt(self, agent_input: AgentInput) -> str:
        ctx = PromptContext(
            agent_name=self.name,
            company="InTimeTec",
            agent_role="report",
            session_history=agent_input.session_history,
            compliance_rules=[],
        )
        return build_prompt(self.config.system_prompt or REPORT_AGENT_PROMPT, ctx)

    def post_process(self, raw_output: Dict) -> AgentOutput:
        intent = raw_output.get("intent", "REPORT_REQUEST")
        text   = (raw_output.get("ai_response_text") or "").strip()

        # Strip any trailing JSON the LLM may have appended after the spoken text
        brace_idx = text.find("{")
        if brace_idx > 0:
            text = text[:brace_idx].strip()
        if not text or text.startswith("{"):
            text = "I'm gathering the information needed to generate your report."

        if not raw_output.get("data_complete"):
            return AgentOutput(
                text=text,
                intent="GATHERING",
                data=raw_output,
                confidence=float(raw_output.get("confidence_score", 1.0)),
            )

        # data_complete=True — report content is ready.
        # Sprint 3: invoke PDF/PPTX tool calls here before returning.
        return AgentOutput(
            text=text,
            intent=intent,
            data=raw_output,
            confidence=float(raw_output.get("confidence_score", 1.0)),
        )

def create_report_agent() -> ReportAgent:
    config = AgentConfig(
        agent_id="agent-4",
        name="Report Agent",
        model=get_model(),
        temperature=LLM_TEMPERATURE,
        max_tokens=LLM_MAX_TOKENS,
        system_prompt='REPORT_AGENT_PROMPT',
    )
    return ReportAgent(id="agent-4", name="Report Agent", config=config, is_active=True)