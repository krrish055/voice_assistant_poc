"""BaseRegistry — generic persist-first registry with asyncio.Lock and subscribers.

Design contract:
  1. update() persists to Neo4j FIRST via ConfigRepository.
  2. Only on successful persist: acquire lock → swap memory → release lock.
  3. Only after successful memory swap: notify subscribers.
  4. If Neo4j write fails: memory is unchanged. Exception propagates to caller.

This guarantees consistency: DB and memory are never out of sync.

Generic parameter K = config key type (usually str or Enum).
Generic parameter V = Pydantic model type stored per key.
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from datetime import datetime, timezone
import logging
from typing import Callable, Generic, TypeVar
from uuid import UUID

from backend.infrastructure.repositories.config_repository import ConfigRepository
from backend.models.config import ConfigSnapshot, RegistryName

K = TypeVar("K")
V = TypeVar("V")

SubscriberCallback = Callable[[str, object], object]

_log = logging.getLogger(__name__)


class BaseRegistry(ABC, Generic[K, V]):
    """Thread-safe, persist-first in-memory configuration registry.

    Subclasses must implement:
      - registry_name: the RegistryName literal for this registry.
      - _serialize(value): convert V to dict for ConfigSnapshot storage.

    Args:
        config_repo: Injected ConfigRepository for persist-first writes.
        changed_by: Actor identifier written into every ConfigSnapshot
                    (typically "system" at startup, "admin:<id>" for UI changes).
    """

    registry_name: RegistryName

    def __init__(
        self,
        config_repo: ConfigRepository,
        changed_by: str = "system",
    ) -> None:
        self._config_repo = config_repo
        self._changed_by = changed_by
        self._store: dict[str, V] = {}
        self._lock = asyncio.Lock()
        self._subscribers: list[SubscriberCallback] = []

    # ──────────────────────────── public interface ──────────────────────────────

    def get(self, key: str) -> V | None:
        """Return the value for key, or None if not present.

        Read is lock-free — dict reads are atomic in CPython and this is
        intentional. The lock only guards writes.
        """
        return self._store.get(key)

    def get_all(self) -> dict[str, V]:
        """Return a shallow copy of the entire config store."""
        return dict(self._store)

    def get_or_raise(self, key: str) -> V:
        """Return value for key, raising KeyError if absent.

        Args:
            key: Config key to look up.

        Raises:
            KeyError: If the key is not present in this registry.
        """
        value = self._store.get(key)
        if value is None:
            raise KeyError(f"[{self.registry_name}] key '{key}' not found")
        return value

    async def update(self, key: str, value: V, changed_by: str | None = None) -> None:
        """Persist-first update: write to Neo4j, then swap memory atomically.

        Steps:
          1. Fetch previous snapshot id (for SUPERSEDES chain).
          2. Build and persist ConfigSnapshot to Neo4j (awaited, not fire-and-forget).
          3. Acquire asyncio.Lock.
          4. Swap in-memory value.
          5. Release lock.
          6. Notify subscribers (outside lock to avoid deadlock).

        Args:
            key: Config key to update.
            value: New value.
            changed_by: Override actor identifier for this specific update.

        Raises:
            Exception: If Neo4j persist fails. Memory remains unchanged.
        """
        actor = changed_by or self._changed_by
        previous_value = self._store.get(key)
        previous_snapshot = await self._config_repo.get_latest_snapshot(
            self.registry_name, key
        )
        supersedes_id: UUID | None = (
            previous_snapshot.id if previous_snapshot else None
        )

        snapshot = ConfigSnapshot(
            registry_name=self.registry_name,
            config_key=key,
            previous_value=self._serialize(previous_value) if previous_value is not None else None,
            new_value=self._serialize(value),
            changed_by=actor,
            changed_at=datetime.now(timezone.utc).isoformat(),
            supersedes_id=supersedes_id,
        )

        # Step 1: persist — if this raises, we never touch memory
        await self._config_repo.save_snapshot(snapshot)

        # Step 2: atomic memory swap
        async with self._lock:
            self._store[key] = value

        # Step 3: notify subscribers (outside lock)
        await self._notify_subscribers(key, value)

    async def delete(self, key: str, changed_by: str | None = None) -> None:
        """Remove a key from the registry with audit trail.

        Persists a snapshot with new_value={"deleted": true} before removing.

        Args:
            key: Key to remove.
            changed_by: Override actor identifier.

        Raises:
            KeyError: If key does not exist.
        """
        if key not in self._store:
            raise KeyError(f"[{self.registry_name}] key '{key}' not found for delete")

        actor = changed_by or self._changed_by
        previous_value = self._store[key]
        previous_snapshot = await self._config_repo.get_latest_snapshot(
            self.registry_name, key
        )

        snapshot = ConfigSnapshot(
            registry_name=self.registry_name,
            config_key=key,
            previous_value=self._serialize(previous_value),
            new_value={"deleted": "true"},
            changed_by=actor,
            changed_at=datetime.now(timezone.utc).isoformat(),
            supersedes_id=previous_snapshot.id if previous_snapshot else None,
        )

        await self._config_repo.save_snapshot(snapshot)

        async with self._lock:
            del self._store[key]

        await self._notify_subscribers(key, None)

    def subscribe(self, callback: SubscriberCallback) -> None:
        """Register an async-compatible callback for change notifications.

        Callbacks receive (key: str, new_value: V | None).
        Exceptions in callbacks are logged and do not block other subscribers.

        Args:
            callback: Callable invoked after every successful update or delete.
        """
        self._subscribers.append(callback)

    async def load(self, key: str, value: V) -> None:
        """Load an initial value directly into memory without persisting.

        Used at application startup to seed registries from Neo4j or config
        without triggering a redundant persist-first write.

        Args:
            key: Config key.
            value: Initial value.
        """
        async with self._lock:
            self._store[key] = value

    # ──────────────────────────── abstract interface ────────────────────────────

    @abstractmethod
    def _serialize(self, value: V) -> dict[str, object]:
        """Serialize V to a plain dict for ConfigSnapshot storage.

        Args:
            value: The registry value to serialize.

        Returns:
            A plain dict representation suitable for Neo4j storage.
        """

    # ──────────────────────────── private helpers ───────────────────────────────

    async def _notify_subscribers(self, key: str, value: object) -> None:
        """Invoke all subscribers, isolating exceptions per subscriber.

        Both sync and async callbacks are supported. Async callbacks are
        awaited directly so the caller of update() is guaranteed that all
        subscriber side-effects (e.g. cache invalidation) have completed
        before update() returns.

        Args:
            key: The config key that changed.
            value: The new value (None on delete).
        """
        for callback in self._subscribers:
            try:
                result = callback(key, value)
                if asyncio.iscoroutine(result):
                    await result
            except Exception:
                _log.exception(
                    "[%s] subscriber %r raised on key '%s' — cache may be stale",
                    self.registry_name,
                    callback,
                    key,
                )
