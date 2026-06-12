"""LLMProviderRegistry — manages LLM provider configurations.

Renamed from AgentProviderRegistry for clarity.
This registry owns LLM provider config, not agent config.
"""

from __future__ import annotations

from typing import Literal

from backend.infrastructure.repositories.config_repository import ConfigRepository
from backend.models.config import LLMProviderConfig
from backend.registry.base_registry import BaseRegistry


class LLMProviderRegistry(BaseRegistry[str, LLMProviderConfig]):
    """Registry for LLM provider slot configurations.

    Key: provider slot key (e.g. "primary", "fallback", "synthesis").
    Value: LLMProviderConfig.

    Changes When: provider, model, API key, base URL, or temperature changes.
    Does NOT own: agent config, prompt templates, inference rules.

    LLMFactory subscribes to this registry to evict stale cached clients
    when a provider config is updated.
    """

    registry_name: Literal["llm_provider"] = "llm_provider"

    def __init__(self, config_repo: ConfigRepository, changed_by: str = "system") -> None:
        """Initialise LLMProviderRegistry.

        Args:
            config_repo: Injected ConfigRepository.
            changed_by: Default actor for audit trail.
        """
        super().__init__(config_repo, changed_by)

    def _serialize(self, value: LLMProviderConfig) -> dict[str, object]:
        """Serialize LLMProviderConfig for ConfigSnapshot storage.

        The API key is excluded from serialization to prevent secrets
        being stored in plain text in the ConfigSnapshot chain.
        """
        data = value.model_dump(mode="json", exclude={"api_key"})
        data["api_key"] = "***REDACTED***"
        return data

    def get_provider(self, slot_key: str) -> LLMProviderConfig:
        """Return LLMProviderConfig for a named slot.

        Args:
            slot_key: Provider slot key (e.g. "primary").

        Returns:
            LLMProviderConfig for the slot.

        Raises:
            KeyError: If the slot is not configured.
        """
        return self.get_or_raise(slot_key)

    def get_primary(self) -> LLMProviderConfig:
        """Return the primary provider configuration.

        Returns:
            LLMProviderConfig for the "primary" slot.

        Raises:
            KeyError: If no primary provider is configured.
        """
        return self.get_or_raise("primary")

    def get_fallback(self) -> LLMProviderConfig | None:
        """Return the fallback provider configuration, if configured.

        Returns:
            LLMProviderConfig for the "fallback" slot, or None.
        """
        return self._store.get("fallback")
