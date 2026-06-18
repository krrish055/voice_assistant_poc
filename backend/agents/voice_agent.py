from dataclasses import dataclass
from typing import Dict

from agents.base_agent import BaseAgent, AgentConfig, AgentInput, AgentOutput
from prompts.template_engine import build_prompt, PromptContext
from prompts.system_prompts import VOICE_AGENT_PROMPT
from config import get_model, LLM_TEMPERATURE, LLM_MAX_TOKENS, COMPANY_NAME
from utils import extract_spoken_text


@dataclass
class VoiceAgent(BaseAgent):
    """Real-time voice interaction agent. Returns plain spoken text only."""

    def agent_type(self) -> str:
        return "voice"

    def build_prompt(self, agent_input: AgentInput) -> str:
        ctx = PromptContext(
            agent_name=self.name,
            company=COMPANY_NAME,
            agent_role="voice",
            session_history=agent_input.session_history,
            compliance_rules=[],
        )
        return build_prompt(self.config.system_prompt or VOICE_AGENT_PROMPT, ctx)

    def post_process(self, raw_output: Dict) -> AgentOutput:
        text = extract_spoken_text(raw_output, "I'm here to help. Please go ahead.")
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
        model=get_model(),
        temperature=LLM_TEMPERATURE,
        max_tokens=LLM_MAX_TOKENS,
        system_prompt=VOICE_AGENT_PROMPT,
    )
    return VoiceAgent(id="agent-1", name="Primary Agent", config=config, is_active=True)
