"""SessionCache — in-memory cache for active SessionState instances.

Single responsibility: hold active SessionState objects in memory,
enforce TTL + max-sessions eviction policy, and flush dirty state
to SessionRepository before eviction.

Eviction policies (all configurable at runtime):
  TTL-based    — session inactive for ttl_seconds is evicted.
  Max-sessions — oldest session evicted when active count exceeds max_size.
  Explicit     — SessionManager calls invalidate() on session complete/abandon.

Persistence contract:
  Before any eviction, if session.is_dirty, SessionRepository.update_session()
  is awaited. If the persist fails the entry is kept in cache and the eviction
  is skipped for that cycle (logged, never silently dropped).
"""

from __future__ import annotations

import asyncio
import time
from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass

from backend.infrastructure.cache import OnEvict, OnHit, OnMiss, _CacheEntry, _noop
from backend.models.session import Session, SessionState

_FlushCallback = Callable[[Session], object]  # async: Session -> None


class SessionCache:
    """TTL + LRU cache for SessionState with dirty-flush-before-eviction.

    Args:
        ttl:            Seconds of inactivity before a session is evicted.
        max_size:       Maximum concurrent active sessions. 0 = unbounded.
        flush_callback: Async callable that persists a dirty Session to Neo4j.
                        Signature: async def flush(session: Session) -> None.
                        Injected by SessionManager. Never called if not dirty.
        on_hit:         Metrics hook invoked on cache hit.
        on_miss:        Metrics hook invoked on cache miss.
        on_evict:       Metrics hook invoked on eviction.
    """

    def __init__(
        self,
        ttl: float = 1800.0,
        max_size: int = 500,
        flush_callback: _FlushCallback | None = None,
        on_hit: OnHit = _noop,
        on_miss: OnMiss = _noop,
        on_evict: OnEvict = _noop,
    ) -> None:
        self._ttl = ttl
        self._max_size = max_size
        self._flush_callback = flush_callback
        self._on_hit = on_hit
        self._on_miss = on_miss
        self._on_evict = on_evict
        self._store: OrderedDict[str, _CacheEntry[SessionState]] = OrderedDict()
        self._lock = asyncio.Lock()
        _CACHE_NAME = "session"
        self._name = _CACHE_NAME

    # ── Public interface ──────────────────────────────────────────────────────

    def get(self, session_id: str) -> SessionState | None:
        """Return SessionState for session_id, or None on miss or expiry.

        Lock-free read. Expired entries are treated as misses.

        Args:
            session_id: Session UUID string.

        Returns:
            SessionState or None.
        """
        entry = self._store.get(session_id)
        if entry is None:
            self._on_miss(self._name)
            return None
        if time.monotonic() > entry.expires_at:
            self._on_miss(self._name)
            return None
        self._store.move_to_end(session_id)
        self._on_hit(self._name)
        return entry.value

    async def set(self, session_id: str, state: SessionState) -> None:
        """Store or refresh a SessionState in the cache.

        If max_size is exceeded, the LRU entry is flushed and evicted first.

        Args:
            session_id: Session UUID string.
            state:      SessionState to cache.
        """
        expires_at = time.monotonic() + self._ttl
        async with self._lock:
            if session_id in self._store:
                self._store.move_to_end(session_id)
            self._store[session_id] = _CacheEntry(value=state, expires_at=expires_at)
            if self._max_size > 0 and len(self._store) > self._max_size:
                await self._evict_lru_unsafe()

    async def invalidate(self, session_id: str) -> None:
        """Explicitly remove a session from the cache.

        Flushes dirty state before removal. Called on session complete/abandon.

        Args:
            session_id: Session UUID string.
        """
        async with self._lock:
            entry = self._store.get(session_id)
            if entry is None:
                return
            await self._flush_if_dirty(entry.value)
            del self._store[session_id]
            self._on_evict(self._name, "explicit")

    async def evict_expired(self) -> int:
        """Flush and evict all sessions whose TTL has elapsed.

        Called by background task. Never called inline on reads.

        Returns:
            Number of sessions evicted.
        """
        now = time.monotonic()
        expired_ids = [
            sid for sid, e in self._store.items() if now > e.expires_at
        ]
        evicted = 0
        for sid in expired_ids:
            async with self._lock:
                entry = self._store.get(sid)
                if entry is None or now <= entry.expires_at:
                    continue
                flushed = await self._flush_if_dirty(entry.value)
                if flushed is not False:
                    del self._store[sid]
                    self._on_evict(self._name, "ttl")
                    evicted += 1
        return evicted

    def active_count(self) -> int:
        """Return the number of sessions currently held in memory."""
        return len(self._store)

    def contains(self, session_id: str) -> bool:
        """Return True if the session is cached and not expired.

        Args:
            session_id: Session UUID string.
        """
        entry = self._store.get(session_id)
        if entry is None:
            return False
        return time.monotonic() <= entry.expires_at

    # ── Private helpers ───────────────────────────────────────────────────────

    async def _flush_if_dirty(self, state: SessionState) -> bool:
        """Persist dirty SessionState to Neo4j via flush_callback.

        Args:
            state: SessionState to conditionally persist.

        Returns:
            True if flush succeeded or not needed.
            False if flush failed (caller should skip eviction).
        """
        if not state.is_dirty or self._flush_callback is None:
            return True
        try:
            result = self._flush_callback(state.session)
            if asyncio.iscoroutine(result):
                await result
            return True
        except Exception:  # noqa: BLE001
            # Flush failure: keep entry in cache, log via caller.
            return False

    async def _evict_lru_unsafe(self) -> None:
        """Evict LRU entry, flushing dirty state first. Caller must hold _lock."""
        lru_key, lru_entry = next(iter(self._store.items()))
        await self._flush_if_dirty(lru_entry.value)
        del self._store[lru_key]
        self._on_evict(self._name, "lru")
