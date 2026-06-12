"""AgentFactory — intent-driven agent creation, registry-driven and OCP-compliant.

Subscribes to AgentRegistry so that enable/disable changes are reflected
immediately without restart.
"""

from __future__ import annotations

from backend.domain.base_agent import BaseAgent
from backend.domain.llm_factory import LLMFactory
from backend.domain.synthesizer_agent import SynthesizerAgent
from backend.exceptions import ConfigurationError
from backend.models.config import AgentConfiguration
from backend.registry.agent_registry import AgentRegistry
from backend.registry.prompt_registry import PromptRegistry

# Maps agent_type strings → concrete BaseAgent subclasses.
# Add new agent types here without modifying AgentFactory logic (OCP).
_AGENT_CLASS_MAP: dict[str, type[BaseAgent]] = {
    "synthesizer": SynthesizerAgent,
}


class AgentFactory:
    """Resolves an intent string to a configured, enabled BaseAgent subclass.

    Reads agent configuration from AgentRegistry and validates that the
    requested agent_type is enabled before instantiation. Subscribes to
    AgentRegistry so that runtime enable/disable changes take effect on
    the next create() call.

    Args:
        agent_registry: Injected AgentRegistry.
        prompt_registry: Injected PromptRegistry (forwarded to created agents).
        llm_factory: Injected LLMFactory (forwarded to created agents).
    """

    def __init__(
        self,
        agent_registry: AgentRegistry,
        prompt_registry: PromptRegistry,
        llm_factory: LLMFactory,
    ) -> None:
        self._agent_registry = agent_registry
        self._prompt_registry = prompt_registry
        self._llm_factory = llm_factory
        self._agent_registry.subscribe(self._on_registry_change)

    # ── public interface ──────────────────────────────────────────────────────

    def create(self, intent: str) -> BaseAgent:
        """Resolve an intent to an agent instance.

        Looks up the AgentConfiguration for the intent (used directly as
        agent_type key), validates it is enabled, then constructs and
        returns the corresponding BaseAgent subclass.

        Args:
            intent: Agent type identifier (e.g. "synthesizer").

        Returns:
            A constructed BaseAgent subclass ready for use.

        Raises:
            KeyError: If no AgentConfiguration is registered for the intent.
            ConfigurationError: If the agent is registered but disabled,
                                or if no implementation class is mapped.
        """
        config: AgentConfiguration = self._agent_registry.get_config(intent)

        if not config.enabled:
            raise ConfigurationError(
                f"Agent '{intent}' is registered but currently disabled."
            )

        agent_cls = _AGENT_CLASS_MAP.get(intent)
        if agent_cls is None:
            raise ConfigurationError(
                f"No implementation class mapped for agent_type '{intent}'. "
                f"Register it in _AGENT_CLASS_MAP."
            )

        return agent_cls(
            prompt_registry=self._prompt_registry,
            llm_factory=self._llm_factory,
        )

    # ── private helpers ───────────────────────────────────────────────────────

    def _on_registry_change(self, key: str, value: object) -> None:
        """AgentRegistry subscriber — no local cache to invalidate.

        AgentFactory reads directly from the registry on every create() call,
        so registry changes are automatically visible without any state reset.

        Args:
            key: The agent_type key that changed.
            value: The new AgentConfiguration, or None on deletion.
        """
