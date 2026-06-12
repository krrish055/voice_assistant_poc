"""RoutingRegistry — manages intent-to-agent routing table."""

from __future__ import annotations

from typing import Literal

from backend.infrastructure.repositories.config_repository import ConfigRepository
from backend.models.config import IntentRoute
from backend.registry.base_registry import BaseRegistry

_FALLBACK_AGENT_TYPE = "synthesizer"


class RoutingRegistry(BaseRegistry[str, IntentRoute]):
    """Registry for intent routing rules used by IntentRouter.

    Key: intent string (e.g. "requirement_elicitation", "general_query").
    Value: IntentRoute.

    Changes When: routing logic, keyword lists, or agent assignments change.
    Does NOT own: agent config, prompt templates, LLM config.
    """

    registry_name: Literal["routing"] = "routing"

    def __init__(self, config_repo: ConfigRepository, changed_by: str = "system") -> None:
        """Initialise RoutingRegistry.

        Args:
            config_repo: Injected ConfigRepository.
            changed_by: Default actor for audit trail.
        """
        super().__init__(config_repo, changed_by)

    def _serialize(self, value: IntentRoute) -> dict[str, object]:
        """Serialize IntentRoute for ConfigSnapshot storage."""
        return value.model_dump(mode="json")

    def get_route(self, intent: str) -> IntentRoute | None:
        """Return the routing rule for an intent string.

        Args:
            intent: Classified intent string.

        Returns:
            IntentRoute or None if no route matches.
        """
        return self._store.get(intent)

    def get_agent_type(self, intent: str) -> str:
        """Resolve an intent to an agent_type string.

        Falls back to the default synthesizer agent if no route is found
        or the matched route is disabled.

        Args:
            intent: Classified intent string.

        Returns:
            agent_type string.
        """
        route = self._store.get(intent)
        if route is None or not route.enabled:
            return _FALLBACK_AGENT_TYPE
        return route.agent_type

    def get_enabled_routes(self) -> list[IntentRoute]:
        """Return all currently enabled routing rules sorted by priority."""
        return sorted(
            [r for r in self._store.values() if r.enabled],
            key=lambda r: r.priority,
            reverse=True,
        )
