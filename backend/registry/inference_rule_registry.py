"""InferenceRuleRegistry — manages domain inference rules."""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from backend.infrastructure.repositories.config_repository import ConfigRepository
from backend.models.config import InferenceRule
from backend.registry.base_registry import BaseRegistry


class InferenceRuleRegistry(BaseRegistry[str, InferenceRule]):
    """Registry for RequirementInferenceEngine rules.

    Key: rule id string (UUID as str).
    Value: InferenceRule.

    Changes When: inference logic or domain knowledge rules change.
    Does NOT own: prompt templates, coverage config, agent config.

    Admin changes here invalidate InferenceCache via subscriber.
    """

    registry_name: Literal["inference_rule"] = "inference_rule"

    def __init__(self, config_repo: ConfigRepository, changed_by: str = "system") -> None:
        """Initialise InferenceRuleRegistry.

        Args:
            config_repo: Injected ConfigRepository.
            changed_by: Default actor for audit trail.
        """
        super().__init__(config_repo, changed_by)

    def _serialize(self, value: InferenceRule) -> dict[str, object]:
        """Serialize InferenceRule for ConfigSnapshot storage."""
        return value.model_dump(mode="json")

    def get_by_id(self, rule_id: UUID) -> InferenceRule | None:
        """Return a rule by its UUID.

        Args:
            rule_id: The rule's UUID.

        Returns:
            InferenceRule or None if not found.
        """
        return self._store.get(str(rule_id))

    def get_enabled_rules(self) -> list[InferenceRule]:
        """Return all currently enabled inference rules."""
        return [r for r in self._store.values() if r.enabled]

    def get_rules_for_domain(self, domain_keyword: str) -> list[InferenceRule]:
        """Return enabled rules matching a domain keyword.

        Args:
            domain_keyword: Domain string to match against rule.condition_domain.

        Returns:
            List of matching enabled InferenceRules.
        """
        return [
            r
            for r in self._store.values()
            if r.enabled and domain_keyword.lower() in r.condition_domain.lower()
        ]
