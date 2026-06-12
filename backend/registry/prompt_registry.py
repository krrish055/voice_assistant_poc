"""PromptRegistry — manages versioned prompt templates."""

from __future__ import annotations

from typing import Literal

from backend.infrastructure.repositories.config_repository import ConfigRepository
from backend.models.config import PromptTemplate
from backend.registry.base_registry import BaseRegistry


class PromptRegistry(BaseRegistry[str, PromptTemplate]):
    """Registry for prompt templates and their variable schemas.

    Key: prompt key string (e.g. "synthesizer_elicitation", "report_synthesis").
    Value: PromptTemplate (immutable Pydantic model).

    Changes When: prompt wording or variable schema changes.
    Does NOT own: agent config, LLM config, inference rules.
    """

    registry_name: Literal["prompt"] = "prompt"

    def __init__(self, config_repo: ConfigRepository, changed_by: str = "system") -> None:
        """Initialise PromptRegistry.

        Args:
            config_repo: Injected ConfigRepository for persist-first writes.
            changed_by: Default actor for audit trail.
        """
        super().__init__(config_repo, changed_by)

    def _serialize(self, value: PromptTemplate) -> dict[str, object]:
        """Serialize PromptTemplate to dict for ConfigSnapshot storage."""
        return value.model_dump()

    def get_template(self, key: str) -> PromptTemplate:
        """Return a PromptTemplate by key.

        Args:
            key: Prompt key string.

        Returns:
            The PromptTemplate for the given key.

        Raises:
            KeyError: If no template is registered for the given key.
        """
        return self.get_or_raise(key)
