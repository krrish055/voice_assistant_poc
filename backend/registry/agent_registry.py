from typing import Dict, Optional
from agents.base_agent import BaseAgent
from agents.voice_agent import create_voice_agent
from agents.compliance_agent import create_compliance_agent
from agents.backup_agent import create_backup_agent


class AgentRegistry:
    """Single-responsibility registry for agent lifecycle management."""

    def __init__(self):
        self._agents: Dict[str, BaseAgent] = {}

    def seed_defaults(self) -> None:
        for agent in [create_voice_agent(), create_backup_agent(), create_compliance_agent()]:
            self._agents[agent.id] = agent

    def register(self, agent: BaseAgent) -> None:
        self._agents[agent.id] = agent

    def get(self, agent_id: str) -> Optional[BaseAgent]:
        return self._agents.get(agent_id)

    def get_active(self) -> Optional[BaseAgent]:
        return next((a for a in self._agents.values() if a.is_active), None)

    def list_all(self) -> list:
        return [a.to_dict() for a in self._agents.values()]

    def update_config(self, agent_id: str, **kwargs) -> bool:
        agent = self._agents.get(agent_id)
        if not agent:
            return False
        for key, val in kwargs.items():
            if val is not None and hasattr(agent.config, key):
                setattr(agent.config, key, val)
        agent.update_activity()
        return True

    def set_active(self, agent_id: str, active: bool) -> bool:
        agent = self._agents.get(agent_id)
        if not agent:
            return False
        agent.is_active = active
        agent.update_activity()
        return True


registry = AgentRegistry()
registry.seed_defaults()
