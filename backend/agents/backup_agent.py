from dataclasses import dataclass
from typing import Dict

from agents.base_agent import BaseAgent, AgentConfig, AgentInput, AgentOutput
from prompts.template_engine import build_prompt, PromptContext
from prompts.system_prompts import BACKUP_AGENT_PROMPT


@dataclass
class BackupAgent(BaseAgent):
    """Failover agent. Lightweight — only last 3 history turns, no compliance rules."""

    def agent_type(self) -> str:
        return "backup"

    def build_prompt(self, agent_input: AgentInput) -> str:
        ctx = PromptContext(
            agent_name=self.name,
            company="InTimeTec",
            agent_role="backup",
            session_history=agent_input.session_history[-3:],
            compliance_rules=[],
        )
        return build_prompt(self.config.system_prompt or BACKUP_AGENT_PROMPT, ctx)

    def post_process(self, raw_output: Dict) -> AgentOutput:
        text = raw_output.get("ai_response_text", "I'm the backup assistant. How can I help?")
        return AgentOutput(
            text=text,
            intent=raw_output.get("intent", "CHAT"),
            data={**raw_output, "_served_by": "backup"},
            confidence=float(raw_output.get("confidence_score", 0.8)),
        )


def create_backup_agent() -> BackupAgent:
    config = AgentConfig(
        agent_id="agent-2",
        name="Backup Agent",
        model="llama-3.3-70b-versatile",
        temperature=0.6,
        max_tokens=1000,
        system_prompt=BACKUP_AGENT_PROMPT,
    )
    return BackupAgent(id="agent-2", name="Backup Agent", config=config, is_active=False)
