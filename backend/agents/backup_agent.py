from dataclasses import dataclass
from typing import Dict

from agents.base_agent import BaseAgent, AgentConfig, AgentInput, AgentOutput
from prompts.template_engine import build_prompt, PromptContext
from prompts.system_prompts import BACKUP_AGENT_PROMPT
from config import get_model, LLM_TEMPERATURE, LLM_MAX_TOKENS, COMPANY_NAME
from utils import extract_spoken_text


@dataclass
class BackupAgent(BaseAgent):
    """Failover agent. Lightweight — only last 3 history turns, no compliance rules."""

    def agent_type(self) -> str:
        return "backup"

    def build_prompt(self, agent_input: AgentInput) -> str:
        ctx = PromptContext(
            agent_name=self.name,
            company=COMPANY_NAME,
            agent_role="backup",
            session_history=agent_input.session_history[-3:],
            compliance_rules=[],
            memory_context=agent_input.memory_context,
        )
        return build_prompt(self.config.system_prompt or BACKUP_AGENT_PROMPT, ctx)

    def post_process(self, raw_output: Dict) -> AgentOutput:
        text = extract_spoken_text(raw_output, "I'm the backup assistant. How can I help?")
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
        model=get_model(),
        temperature=LLM_TEMPERATURE,
        max_tokens=LLM_MAX_TOKENS,
        system_prompt=BACKUP_AGENT_PROMPT,
    )
    return BackupAgent(id="agent-2", name="Backup Agent", config=config, is_active=False)
