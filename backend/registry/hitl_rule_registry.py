"""HITLRuleRegistry — manages Human-in-the-Loop trigger rules."""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from backend.infrastructure.repositories.config_repository import ConfigRepository
from backend.models.config import HITLRule
from backend.registry.base_registry import BaseRegistry


class HITLRuleRegistry(BaseRegistry[str, HITLRule]):
    """Registry for HITL trigger rules evaluated after every conversation turn.

    Key: rule id string (UUID as str).
    Value: HITLRule.

    Changes When: HITL conditions, thresholds, or flagged topics change.
    Does NOT own: agent config, LLM config, prompt templates.
    """

    registry_name: Literal["hitl_rule"] = "hitl_rule"

    def __init__(self, config_repo: ConfigRepository, changed_by: str = "system") -> None:
        """Initialise HITLRuleRegistry.

        Args:
            config_repo: Injected ConfigRepository.
            changed_by: Default actor for audit trail.
        """
        super().__init__(config_repo, changed_by)

    def _serialize(self, value: HITLRule) -> dict[str, object]:
        """Serialize HITLRule for ConfigSnapshot storage."""
        return value.model_dump(mode="json")

    def get_enabled_rules(self) -> list[HITLRule]:
        """Return all currently enabled HITL rules, sorted by priority descending."""
        return sorted(
            [r for r in self._store.values() if r.enabled],
            key=lambda r: r.priority,
            reverse=True,
        )

    def get_by_id(self, rule_id: UUID) -> HITLRule | None:
        """Return a HITL rule by its UUID.

        Args:
            rule_id: The rule's UUID.

        Returns:
            HITLRule or None if not found.
        """
        return self._store.get(str(rule_id))
