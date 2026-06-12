"""Generic TTL + LRU in-memory cache.

Design contract:
- get()  is lock-free (read-only dict access, atomic in CPython).
- set()  acquires asyncio.Lock to guard concurrent writes.
- evict_expired() and evict_lru() are called by a background task,
  never inline on reads, to avoid latency spikes on cache misses.
- Metrics hooks are plain callables injected at construction time.
  ObservabilityService (Phase 7) supplies them. Default = no-op.
- No global state. All state lives on the instance.

Generic parameters:
  K — key type (str, UUID, etc.)
  V — cached value type (Pydantic model)
"""

from __future__ import annotations

import asyncio
import time
from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Generic, TypeVar

K = TypeVar("K")
V = TypeVar("V")

# Metrics hook signatures
OnHit = Callable[[str], None]      # cache_name
OnMiss = Callable[[str], None]     # cache_name
OnEvict = Callable[[str, str], None]  # cache_name, reason ("ttl" | "lru" | "explicit")


def _noop(*_: object) -> None:
    pass


@dataclass
class _CacheEntry(Generic[V]):
    """Internal wrapper holding a cached value with its expiry timestamp."""

    value: V
    expires_at: float  # monotonic clock seconds


class TTLCache(Generic[K, V]):
    """Thread-safe async TTL + LRU in-memory cache.

    Args:
        name:       Identifier used in metric hooks. E.g. "session", "coverage".
        ttl:        Default time-to-live in seconds for each entry.
        max_size:   Maximum number of entries before LRU eviction triggers.
                    0 = unbounded (TTL-only eviction).
        on_hit:     Callable invoked on every cache hit. Receives cache name.
        on_miss:    Callable invoked on every cache miss. Receives cache name.
        on_evict:   Callable invoked on every eviction. Receives (name, reason).
    """

    def __init__(
        self,
        name: str,
        ttl: float = 300.0,
        max_size: int = 0,
        on_hit: OnHit = _noop,
        on_miss: OnMiss = _noop,
        on_evict: OnEvict = _noop,
    ) -> None:
        self._name = name
        self._ttl = ttl
        self._max_size = max_size
        self._on_hit = on_hit
        self._on_miss = on_miss
        self._on_evict = on_evict
        # OrderedDict preserves insertion order for LRU tracking.
        self._store: OrderedDict[K, _CacheEntry[V]] = OrderedDict()
        self._lock = asyncio.Lock()

    # ── Public interface ──────────────────────────────────────────────────────

    def get(self, key: K) -> V | None:
        """Return cached value for key, or None on miss or expiry.

        Lock-free — safe to call from any coroutine without awaiting.
        Expired entries are treated as misses and left for background eviction.

        Args:
            key: Cache key.

        Returns:
            Cached value or None.
        """
        entry = self._store.get(key)
        if entry is None:
            self._on_miss(self._name)
            return None
        if time.monotonic() > entry.expires_at:
            # Treat as miss; background task will clean up.
            self._on_miss(self._name)
            return None
        # Move to end to mark as recently used (LRU tracking).
        self._store.move_to_end(key)
        self._on_hit(self._name)
        return entry.value

    async def set(self, key: K, value: V, ttl: float | None = None) -> None:
        """Store a value under key with optional per-entry TTL override.

        Acquires asyncio.Lock for the write. If max_size is set and the
        cache is full, the least-recently-used entry is evicted first.

        Args:
            key:   Cache key.
            value: Value to cache.
            ttl:   Per-entry TTL override in seconds. Defaults to self._ttl.
        """
        expires_at = time.monotonic() + (ttl if ttl is not None else self._ttl)
        async with self._lock:
            if key in self._store:
                self._store.move_to_end(key)
            self._store[key] = _CacheEntry(value=value, expires_at=expires_at)
            if self._max_size > 0 and len(self._store) > self._max_size:
                self._evict_lru_unsafe()

    async def invalidate(self, key: K) -> None:
        """Explicitly remove a single key from the cache.

        Args:
            key: Cache key to remove.
        """
        async with self._lock:
            if key in self._store:
                del self._store[key]
                self._on_evict(self._name, "explicit")

    async def invalidate_all(self) -> None:
        """Remove all entries from the cache.

        Used when a registry config change invalidates all computed state.
        E.g., CoverageConfigRegistry weight change invalidates all CoverageCache entries.
        """
        async with self._lock:
            count = len(self._store)
            self._store.clear()
        for _ in range(count):
            self._on_evict(self._name, "explicit")

    async def evict_expired(self) -> int:
        """Remove all entries whose TTL has elapsed.

        Called by a background task — never called inline on reads.

        Returns:
            Number of entries evicted.
        """
        now = time.monotonic()
        expired: list[K] = [
            k for k, e in self._store.items() if now > e.expires_at
        ]
        if not expired:
            return 0
        async with self._lock:
            # Re-check under lock — entry may have been refreshed between scan and lock.
            still_expired = [k for k in expired if k in self._store and now > self._store[k].expires_at]
            for k in still_expired:
                del self._store[k]
                self._on_evict(self._name, "ttl")
        return len(still_expired)

    def size(self) -> int:
        """Return the current number of entries (including expired, not yet evicted)."""
        return len(self._store)

    def contains(self, key: K) -> bool:
        """Return True if key exists and has not expired.

        Args:
            key: Cache key.
        """
        entry = self._store.get(key)
        if entry is None:
            return False
        return time.monotonic() <= entry.expires_at

    # ── Private helpers ───────────────────────────────────────────────────────

    def _evict_lru_unsafe(self) -> None:
        """Evict the least-recently-used entry. Caller must hold _lock."""
        lru_key, _ = next(iter(self._store.items()))
        del self._store[lru_key]
        self._on_evict(self._name, "lru")
