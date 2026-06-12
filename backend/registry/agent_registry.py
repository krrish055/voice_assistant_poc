"""AgentRegistry — maps agent_type strings to AgentConfiguration."""

from __future__ import annotations

from typing import Literal

from backend.infrastructure.repositories.config_repository import ConfigRepository
from backend.models.config import AgentConfiguration
from backend.registry.base_registry import BaseRegistry


class AgentRegistry(BaseRegistry[str, AgentConfiguration]):
    """Registry for agent type configurations.

    Key: agent_type string (e.g. "synthesizer", "general").
    Value: AgentConfiguration.

    Changes When: agent enable/disable, prompt key, threshold, or policy changes.
    Does NOT own: LLM provider config, prompt templates.
    Does NOT instantiate agents — that is AgentFactory's responsibility.
    """

    registry_name: Literal["agent"] = "agent"

    def __init__(self, config_repo: ConfigRepository, changed_by: str = "system") -> None:
        """Initialise AgentRegistry.

        Args:
            config_repo: Injected ConfigRepository.
            changed_by: Default actor for audit trail.
        """
        super().__init__(config_repo, changed_by)

    def _serialize(self, value: AgentConfiguration) -> dict[str, object]:
        """Serialize AgentConfiguration for ConfigSnapshot storage."""
        return value.model_dump(mode="json")

    def get_config(self, agent_type: str) -> AgentConfiguration:
        """Return configuration for an agent type.

        Args:
            agent_type: The agent type identifier.

        Returns:
            AgentConfiguration for the type.

        Raises:
            KeyError: If no config is registered for the type.
        """
        return self.get_or_raise(agent_type)

    def get_enabled(self, agent_type: str) -> AgentConfiguration | None:
        """Return AgentConfiguration only if the agent is enabled.

        Args:
            agent_type: The agent type identifier.

        Returns:
            AgentConfiguration if enabled, None if disabled or not found.
        """
        config = self._store.get(agent_type)
        if config is None or not config.enabled:
            return None
        return config

    def list_enabled(self) -> list[AgentConfiguration]:
        """Return all currently enabled agent configurations."""
        return [c for c in self._store.values() if c.enabled]
