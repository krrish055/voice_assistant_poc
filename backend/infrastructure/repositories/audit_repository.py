"""AuditRepository — Neo4j persistence for AuditEvent nodes.

Single responsibility: write and query AuditEvent nodes.
Append-only — audit events are never updated or deleted.
No business logic. No formatting. No queue management (owned by AuditLogger).
"""

from __future__ import annotations

import json
from uuid import UUID

from neo4j import AsyncDriver, AsyncManagedTransaction

from backend.infrastructure.repositories.base_repository import BaseRepository
from backend.models.audit import AuditEvent, AuditEventType, AuditSeverity

# ── Cypher constants ──────────────────────────────────────────────────────────

_CREATE_AUDIT_EVENT = """
CREATE (a:AuditEvent {
    id:         $id,
    event_type: $event_type,
    severity:   $severity,
    actor:      $actor,
    session_id: $session_id,
    turn_id:    $turn_id,
    timestamp:  $timestamp,
    payload:    $payload,
    message:    $message
})
"""

_LINK_TO_SESSION = """
MATCH (a:AuditEvent {id: $event_id})
MATCH (s:Session {id: $session_id})
CREATE (a)-[:AUDIT_FOR_SESSION]->(s)
"""

_GET_EVENTS_BY_SESSION = """
MATCH (a:AuditEvent {session_id: $session_id})
RETURN a
ORDER BY a.timestamp DESC
LIMIT $limit
"""

_GET_EVENTS_BY_TYPE = """
MATCH (a:AuditEvent {event_type: $event_type})
RETURN a
ORDER BY a.timestamp DESC
LIMIT $limit
"""

_GET_EVENTS_BY_ACTOR = """
MATCH (a:AuditEvent {actor: $actor})
RETURN a
ORDER BY a.timestamp DESC
LIMIT $limit
"""

_GET_EVENTS_BY_SEVERITY = """
MATCH (a:AuditEvent {severity: $severity})
RETURN a
ORDER BY a.timestamp DESC
LIMIT $limit
"""

_GET_EVENT_BY_ID = """
MATCH (a:AuditEvent {id: $id})
RETURN a
"""

_GET_EVENTS_IN_RANGE = """
MATCH (a:AuditEvent)
WHERE a.timestamp >= $from_ts AND a.timestamp <= $to_ts
RETURN a
ORDER BY a.timestamp DESC
LIMIT $limit
"""

_COUNT_EVENTS_BY_TYPE_FOR_SESSION = """
MATCH (a:AuditEvent {session_id: $session_id, event_type: $event_type})
RETURN count(a) AS total
"""


class AuditRepository(BaseRepository):
    """Append-only write and query of AuditEvent nodes in Neo4j.

    Write path is always append — no updates, no deletes.
    AuditLogger owns the async queue and backpressure policy.
    This repository only executes the Neo4j write when called.

    All methods are async. All queries run through execute_write or
    execute_read — no sync driver, no run_in_executor.
    """

    def __init__(self, driver: AsyncDriver, database: str = "neo4j") -> None:
        """Initialise AuditRepository.

        Args:
            driver: Injected async Neo4j driver.
            database: Target database name.
        """
        super().__init__(driver, database)

    # ── Write ─────────────────────────────────────────────────────────────────

    async def save_event(self, event: AuditEvent) -> None:
        """Persist an AuditEvent node.

        If the event has a session_id, an AUDIT_FOR_SESSION relationship
        is also created to enable session-scoped audit queries.

        Args:
            event: AuditEvent to persist. Never mutated.
        """
        await self._execute_write(self._save_event_tx, event=event)

    async def save_many(self, events: list[AuditEvent]) -> None:
        """Persist multiple AuditEvent nodes in a single transaction.

        Args:
            events: List of AuditEvent instances to persist.
        """
        await self._execute_write(self._save_many_tx, events=events)

    # ── Reads ─────────────────────────────────────────────────────────────────

    async def get_event(self, event_id: UUID) -> AuditEvent | None:
        """Return an AuditEvent by id.

        Args:
            event_id: AuditEvent UUID.

        Returns:
            AuditEvent or None.
        """
        rows = await self._execute_read(
            self._get_event_tx, event_id=str(event_id)
        )
        return self._row_to_event(rows[0]) if rows else None

    async def get_by_session(
        self, session_id: UUID, limit: int = 200
    ) -> list[AuditEvent]:
        """Return audit events for a session ordered newest first.

        Args:
            session_id: Session UUID.
            limit: Maximum number of events to return.

        Returns:
            List of AuditEvent models.
        """
        rows = await self._execute_read(
            self._get_by_session_tx,
            session_id=str(session_id),
            limit=limit,
        )
        return [self._row_to_event(r) for r in rows]

    async def get_by_event_type(
        self, event_type: AuditEventType, limit: int = 100
    ) -> list[AuditEvent]:
        """Return audit events of a specific type ordered newest first.

        Args:
            event_type: AuditEventType filter.
            limit: Maximum number of events.

        Returns:
            List of AuditEvent models.
        """
        rows = await self._execute_read(
            self._get_by_type_tx,
            event_type=event_type.value,
            limit=limit,
        )
        return [self._row_to_event(r) for r in rows]

    async def get_by_actor(
        self, actor: str, limit: int = 100
    ) -> list[AuditEvent]:
        """Return audit events for a specific actor ordered newest first.

        Args:
            actor: Actor identifier string.
            limit: Maximum number of events.

        Returns:
            List of AuditEvent models.
        """
        rows = await self._execute_read(
            self._get_by_actor_tx, actor=actor, limit=limit
        )
        return [self._row_to_event(r) for r in rows]

    async def get_by_severity(
        self, severity: AuditSeverity, limit: int = 100
    ) -> list[AuditEvent]:
        """Return audit events of a given severity ordered newest first.

        Args:
            severity: AuditSeverity filter.
            limit: Maximum number of events.

        Returns:
            List of AuditEvent models.
        """
        rows = await self._execute_read(
            self._get_by_severity_tx,
            severity=severity.value,
            limit=limit,
        )
        return [self._row_to_event(r) for r in rows]

    async def get_in_range(
        self, from_ts: str, to_ts: str, limit: int = 500
    ) -> list[AuditEvent]:
        """Return audit events within a timestamp range.

        Args:
            from_ts: ISO 8601 start timestamp (inclusive).
            to_ts: ISO 8601 end timestamp (inclusive).
            limit: Maximum number of events.

        Returns:
            List of AuditEvent models ordered newest first.
        """
        rows = await self._execute_read(
            self._get_in_range_tx,
            from_ts=from_ts,
            to_ts=to_ts,
            limit=limit,
        )
        return [self._row_to_event(r) for r in rows]

    async def count_by_type_for_session(
        self, session_id: UUID, event_type: AuditEventType
    ) -> int:
        """Return count of a specific event type for a session.

        Args:
            session_id: Session UUID.
            event_type: AuditEventType to count.

        Returns:
            Integer count.
        """
        rows = await self._execute_read(
            self._count_by_type_tx,
            session_id=str(session_id),
            event_type=event_type.value,
        )
        return int(rows[0]["total"]) if rows else 0

    # ── Transaction functions ─────────────────────────────────────────────────

    @staticmethod
    async def _save_event_tx(
        tx: AsyncManagedTransaction, event: AuditEvent
    ) -> list[dict[str, object]]:
        await BaseRepository._run(
            tx,
            _CREATE_AUDIT_EVENT,
            {
                "id": str(event.id),
                "event_type": event.event_type.value,
                "severity": event.severity.value,
                "actor": event.actor,
                "session_id": str(event.session_id) if event.session_id else None,
                "turn_id": str(event.turn_id) if event.turn_id else None,
                "timestamp": event.timestamp,
                "payload": json.dumps(event.payload),
                "message": event.message,
            },
        )
        if event.session_id is not None:
            await BaseRepository._run(
                tx,
                _LINK_TO_SESSION,
                {"event_id": str(event.id), "session_id": str(event.session_id)},
            )
        return []

    @staticmethod
    async def _save_many_tx(
        tx: AsyncManagedTransaction, events: list[AuditEvent]
    ) -> list[dict[str, object]]:
        for event in events:
            await BaseRepository._run(
                tx,
                _CREATE_AUDIT_EVENT,
                {
                    "id": str(event.id),
                    "event_type": event.event_type.value,
                    "severity": event.severity.value,
                    "actor": event.actor,
                    "session_id": str(event.session_id) if event.session_id else None,
                    "turn_id": str(event.turn_id) if event.turn_id else None,
                    "timestamp": event.timestamp,
                    "payload": json.dumps(event.payload),
                    "message": event.message,
                },
            )
            if event.session_id is not None:
                await BaseRepository._run(
                    tx,
                    _LINK_TO_SESSION,
                    {"event_id": str(event.id), "session_id": str(event.session_id)},
                )
        return []

    @staticmethod
    async def _get_event_tx(
        tx: AsyncManagedTransaction, event_id: str
    ) -> list[dict[str, object]]:
        return await BaseRepository._run(tx, _GET_EVENT_BY_ID, {"id": event_id})

    @staticmethod
    async def _get_by_session_tx(
        tx: AsyncManagedTransaction, session_id: str, limit: int
    ) -> list[dict[str, object]]:
        return await BaseRepository._run(
            tx, _GET_EVENTS_BY_SESSION, {"session_id": session_id, "limit": limit}
        )

    @staticmethod
    async def _get_by_type_tx(
        tx: AsyncManagedTransaction, event_type: str, limit: int
    ) -> list[dict[str, object]]:
        return await BaseRepository._run(
            tx, _GET_EVENTS_BY_TYPE, {"event_type": event_type, "limit": limit}
        )

    @staticmethod
    async def _get_by_actor_tx(
        tx: AsyncManagedTransaction, actor: str, limit: int
    ) -> list[dict[str, object]]:
        return await BaseRepository._run(
            tx, _GET_EVENTS_BY_ACTOR, {"actor": actor, "limit": limit}
        )

    @staticmethod
    async def _get_by_severity_tx(
        tx: AsyncManagedTransaction, severity: str, limit: int
    ) -> list[dict[str, object]]:
        return await BaseRepository._run(
            tx, _GET_EVENTS_BY_SEVERITY, {"severity": severity, "limit": limit}
        )

    @staticmethod
    async def _get_in_range_tx(
        tx: AsyncManagedTransaction, from_ts: str, to_ts: str, limit: int
    ) -> list[dict[str, object]]:
        return await BaseRepository._run(
            tx,
            _GET_EVENTS_IN_RANGE,
            {"from_ts": from_ts, "to_ts": to_ts, "limit": limit},
        )

    @staticmethod
    async def _count_by_type_tx(
        tx: AsyncManagedTransaction, session_id: str, event_type: str
    ) -> list[dict[str, object]]:
        return await BaseRepository._run(
            tx,
            _COUNT_EVENTS_BY_TYPE_FOR_SESSION,
            {"session_id": session_id, "event_type": event_type},
        )

    # ── Mapping helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _row_to_event(record: dict[str, object]) -> AuditEvent:
        """Map a Neo4j record to an AuditEvent model."""
        node: dict[str, object] = record.get("a", record)  # type: ignore[assignment]
        raw_payload = node.get("payload", "{}")
        payload: dict[str, str | int | float | bool | None] = (
            json.loads(raw_payload)
            if isinstance(raw_payload, str)
            else dict(raw_payload)  # type: ignore[arg-type]
        )
        return AuditEvent(
            id=UUID(str(node["id"])),
            event_type=AuditEventType(str(node["event_type"])),
            severity=AuditSeverity(str(node["severity"])),
            actor=str(node["actor"]),
            session_id=(
                UUID(str(node["session_id"])) if node.get("session_id") else None
            ),
            turn_id=(
                UUID(str(node["turn_id"])) if node.get("turn_id") else None
            ),
            timestamp=str(node["timestamp"]),
            payload=payload,
            message=str(node.get("message", "")),
        )
