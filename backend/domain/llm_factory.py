"""LLMFactory — runtime LLM provider resolution with hot-reload support.

Subscribes to LLMProviderRegistry so that any admin-driven provider update
is reflected immediately without application restart.
"""

from __future__ import annotations

import asyncio

from backend.exceptions import ConfigurationError
from backend.models.config import LLMProviderConfig
from backend.registry.llm_provider_registry import LLMProviderRegistry


class LLMFactory:
    """Resolves and caches the active primary and fallback LLM provider configs.

    Subscribes to LLMProviderRegistry on construction. When the registry
    updates any provider slot, reload_provider_configs() is invoked
    automatically so that the next call to get_primary_client() or
    get_fallback_client() returns the updated config.

    Args:
        provider_registry: Injected LLMProviderRegistry.
    """

    def __init__(self, provider_registry: LLMProviderRegistry) -> None:
        self._registry = provider_registry
        self._lock = asyncio.Lock()
        self._primary: LLMProviderConfig | None = None
        self._fallback: LLMProviderConfig | None = None
        self._registry.subscribe(self.on_provider_change)

    # ── public interface ──────────────────────────────────────────────────────

    def get_primary_client(self) -> LLMProviderConfig:
        """Return the active primary provider config.

        Raises:
            ConfigurationError: If no primary provider has been loaded.
        """
        if self._primary is None:
            raise ConfigurationError("No primary LLM provider configured.")
        return self._primary

    def get_fallback_client(self) -> LLMProviderConfig | None:
        """Return the active fallback provider config, or None if absent."""
        return self._fallback

    async def reload_provider_configs(self) -> None:
        """Re-read primary and fallback slots from the registry.

        Called automatically by on_provider_change, or manually to
        force a synchronous refresh.
        """
        async with self._lock:
            self._primary = self._registry.get_primary()
            self._fallback = self._registry.get_fallback()

    def on_provider_change(self, key: str, value: object) -> None:
        """Registry subscriber callback — schedules a config reload.

        Intentionally non-async: BaseRegistry._notify_subscribers detects
        coroutines and awaits them; a plain callable is also supported.
        This method runs synchronously so it can be registered without
        creating a coroutine object at subscribe time.

        Args:
            key: The provider slot key that changed (e.g. "primary").
            value: The new LLMProviderConfig, or None on deletion.
        """
        # Direct in-place swap — no I/O, lock not required for atomic
        # CPython dict writes. For full async safety call reload_provider_configs.
        if key == "primary":
            self._primary = value if isinstance(value, LLMProviderConfig) else None
        elif key == "fallback":
            self._fallback = value if isinstance(value, LLMProviderConfig) else None
