from dataclasses import dataclass
from typing import Dict, List

from agents.base_agent import BaseAgent, AgentConfig, AgentInput, AgentOutput
from prompts.template_engine import build_prompt, PromptContext
from prompts.system_prompts import COMPLIANCE_AGENT_PROMPT

_DEFAULT_RULES: List[str] = [
    "Never disclose salary, payroll, or HR data without admin approval.",
    "Flag any PII in user input before processing.",
    "All report requests require explicit data_complete=true before generation.",
]


@dataclass
class ComplianceAgent(BaseAgent):
    """Compliance auditor. Injects guardrails, gates restricted requests."""

    def agent_type(self) -> str:
        return "compliance"

    def build_prompt(self, agent_input: AgentInput) -> str:
        ctx = PromptContext(
            agent_name=self.name,
            company="InTimeTec",
            agent_role="compliance",
            session_history=agent_input.session_history,
            compliance_rules=agent_input.compliance_rules or _DEFAULT_RULES,
        )
        return build_prompt(self.config.system_prompt or COMPLIANCE_AGENT_PROMPT, ctx)

    def post_process(self, raw_output: Dict) -> AgentOutput:
        intent = raw_output.get("intent", "CHAT")
        if intent == "RESTRICTED_REQUEST" or raw_output.get("is_restricted_query"):
            return AgentOutput(
                text="That request requires administrator approval. I've flagged it for review.",
                intent="RESTRICTED_REQUEST",
                data=raw_output,
                confidence=1.0,
            )
        if intent == "REPORT_REQUEST" and not raw_output.get("data_complete"):
            return AgentOutput(
                text=raw_output.get("ai_response_text", "I need more details before generating the report."),
                intent="GATHERING",
                data=raw_output,
                confidence=float(raw_output.get("confidence_score", 1.0)),
            )
        return AgentOutput(
            text=raw_output.get("ai_response_text", ""),
            intent=intent,
            data=raw_output,
            confidence=float(raw_output.get("confidence_score", 1.0)),
        )


def create_compliance_agent() -> ComplianceAgent:
    config = AgentConfig(
        agent_id="agent-3",
        name="Compliance Agent",
        model="llama-3.3-70b-versatile",
        temperature=0.5,
        max_tokens=1500,
        system_prompt=COMPLIANCE_AGENT_PROMPT,
    )
    return ComplianceAgent(id="agent-3", name="Compliance Agent", config=config, is_active=True)
