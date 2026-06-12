"""CoverageCache and InferenceCache — typed TTLCache wrappers.

Both are thin wrappers over TTLCache[str, V] with domain-specific
key conventions and invalidation helpers.

CoverageCache:
  Caches CoverageSnapshot per session_id (str).
  Invalidated when:
    - A new turn is processed (coverage may have changed).
    - CoverageConfigRegistry weights are updated (all entries stale).
    - Session completes.

InferenceCache:
  Caches SessionInferences per session_id (str).
  Invalidated when:
    - A new turn is processed (new input may confirm/contradict inferences).
    - InferenceRuleRegistry rules are updated (all entries stale).
    - Session completes.

Neither cache performs computation. They are pure read-through storage.
CoverageEngine and InferenceEngine own the computation logic.
"""

from __future__ import annotations

from backend.infrastructure.cache import OnEvict, OnHit, OnMiss, TTLCache, _noop
from backend.models.coverage import CoverageSnapshot
from backend.models.inference import SessionInferences


class CoverageCache:
    """TTL cache for CoverageSnapshot objects keyed by session_id string.

    Args:
        ttl:      Seconds before a cached snapshot is considered stale.
                  Default 300 seconds (5 minutes).
        max_size: Maximum entries before LRU eviction. 0 = unbounded.
        on_hit:   Metrics hook for cache hits.
        on_miss:  Metrics hook for cache misses.
        on_evict: Metrics hook for evictions.
    """

    def __init__(
        self,
        ttl: float = 300.0,
        max_size: int = 0,
        on_hit: OnHit = _noop,
        on_miss: OnMiss = _noop,
        on_evict: OnEvict = _noop,
    ) -> None:
        self._cache: TTLCache[str, CoverageSnapshot] = TTLCache(
            name="coverage",
            ttl=ttl,
            max_size=max_size,
            on_hit=on_hit,
            on_miss=on_miss,
            on_evict=on_evict,
        )

    def get(self, session_id: str) -> CoverageSnapshot | None:
        """Return cached CoverageSnapshot for a session, or None on miss.

        Args:
            session_id: Session UUID string.

        Returns:
            CoverageSnapshot or None.
        """
        return self._cache.get(session_id)

    async def set(self, session_id: str, snapshot: CoverageSnapshot) -> None:
        """Cache a CoverageSnapshot for a session.

        Args:
            session_id: Session UUID string.
            snapshot:   CoverageSnapshot to cache.
        """
        await self._cache.set(session_id, snapshot)

    async def invalidate(self, session_id: str) -> None:
        """Remove a single session's coverage snapshot from the cache.

        Called after each turn or on session completion.

        Args:
            session_id: Session UUID string.
        """
        await self._cache.invalidate(session_id)

    async def invalidate_all(self) -> None:
        """Remove all coverage snapshots.

        Called when CoverageConfigRegistry dimension weights are updated —
        all cached scores are stale and must be recomputed.
        """
        await self._cache.invalidate_all()

    async def evict_expired(self) -> int:
        """Evict TTL-expired entries. Called by background task.

        Returns:
            Number of entries evicted.
        """
        return await self._cache.evict_expired()

    def size(self) -> int:
        """Return current number of cached entries."""
        return self._cache.size()

    def contains(self, session_id: str) -> bool:
        """Return True if a fresh snapshot exists for the session.

        Args:
            session_id: Session UUID string.
        """
        return self._cache.contains(session_id)


class InferenceCache:
    """TTL cache for SessionInferences objects keyed by session_id string.

    Args:
        ttl:      Seconds before cached inferences are considered stale.
                  Default 600 seconds (10 minutes).
        max_size: Maximum entries before LRU eviction. 0 = unbounded.
        on_hit:   Metrics hook for cache hits.
        on_miss:  Metrics hook for cache misses.
        on_evict: Metrics hook for evictions.
    """

    def __init__(
        self,
        ttl: float = 600.0,
        max_size: int = 0,
        on_hit: OnHit = _noop,
        on_miss: OnMiss = _noop,
        on_evict: OnEvict = _noop,
    ) -> None:
        self._cache: TTLCache[str, SessionInferences] = TTLCache(
            name="inference",
            ttl=ttl,
            max_size=max_size,
            on_hit=on_hit,
            on_miss=on_miss,
            on_evict=on_evict,
        )

    def get(self, session_id: str) -> SessionInferences | None:
        """Return cached SessionInferences for a session, or None on miss.

        Args:
            session_id: Session UUID string.

        Returns:
            SessionInferences or None.
        """
        return self._cache.get(session_id)

    async def set(self, session_id: str, inferences: SessionInferences) -> None:
        """Cache SessionInferences for a session.

        Args:
            session_id:  Session UUID string.
            inferences:  SessionInferences to cache.
        """
        await self._cache.set(session_id, inferences)

    async def invalidate(self, session_id: str) -> None:
        """Remove a single session's inferences from the cache.

        Called after each turn — new user input may alter inference state.

        Args:
            session_id: Session UUID string.
        """
        await self._cache.invalidate(session_id)

    async def invalidate_all(self) -> None:
        """Remove all inference entries.

        Called when InferenceRuleRegistry rules are updated —
        all cached inferences may be based on stale rules.
        """
        await self._cache.invalidate_all()

    async def evict_expired(self) -> int:
        """Evict TTL-expired entries. Called by background task.

        Returns:
            Number of entries evicted.
        """
        return await self._cache.evict_expired()

    def size(self) -> int:
        """Return current number of cached entries."""
        return self._cache.size()

    def contains(self, session_id: str) -> bool:
        """Return True if fresh inferences exist for the session.

        Args:
            session_id: Session UUID string.
        """
        return self._cache.contains(session_id)
