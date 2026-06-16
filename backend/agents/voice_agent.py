from dataclasses import dataclass
from typing import Dict

from agents.base_agent import BaseAgent, AgentConfig, AgentInput, AgentOutput
from prompts.template_engine import build_prompt, PromptContext
from prompts.system_prompts import REPORT_SYSTEM_PROMPT


@dataclass
class VoiceAgent(BaseAgent):
    """Real-time voice interaction agent. Returns plain text only."""

    def agent_type(self) -> str:
        return "voice"

    def build_prompt(self, agent_input: AgentInput) -> str:
        ctx = PromptContext(
            agent_name=self.name,
            company="InTimeTec",
            agent_role="voice",
            session_history=agent_input.session_history,
            compliance_rules=[],
        )
        return build_prompt(self.config.system_prompt or REPORT_SYSTEM_PROMPT, ctx)

    def post_process(self, raw_output: Dict) -> AgentOutput:
        text = raw_output.get("ai_response_text", "").strip()
        # LLM sometimes appends the JSON block after the spoken text in the same field
        brace_idx = text.find('{')
        if brace_idx > 0:
            text = text[:brace_idx].strip()
        if not text or text.startswith("{"):
            text = "I'm here to help. Please go ahead."
        return AgentOutput(
            text=text,
            intent=raw_output.get("intent", "CHAT"),
            data=raw_output,
            confidence=float(raw_output.get("confidence_score", 1.0)),
        )


def create_voice_agent() -> VoiceAgent:
    config = AgentConfig(
        agent_id="agent-1",
        name="Primary Agent",
        model="llama-3.3-70b-versatile",
        temperature=0.7,
        max_tokens=1000,
        system_prompt=REPORT_SYSTEM_PROMPT,
    )
    return VoiceAgent(id="agent-1", name="Primary Agent", config=config, is_active=True)
