"""SessionRepository — Neo4j persistence for Session and Turn nodes.

Single responsibility: read and write Session and Turn graph nodes.
No business logic. No coverage computation. No inference logic.
"""

from __future__ import annotations

import json
from uuid import UUID

from neo4j import AsyncDriver, AsyncManagedTransaction

from backend.infrastructure.repositories.base_repository import BaseRepository
from backend.models.session import (
    InputModality,
    LLMConfigSnapshot,
    Session,
    SessionStatus,
    Turn,
    TurnStatus,
)

# ── Cypher constants ──────────────────────────────────────────────────────────

_CREATE_SESSION = """
CREATE (s:Session {
    id:                    $id,
    user_id:               $user_id,
    agent_type:            $agent_type,
    status:                $status,
    llm_config_snapshot:   $llm_config_snapshot,
    session_update_policy: $session_update_policy,
    coverage_score:        $coverage_score,
    turn_count:            $turn_count,
    created_at:            $created_at,
    updated_at:            $updated_at,
    completed_at:          $completed_at,
    metadata:              $metadata
})
"""

_UPDATE_SESSION = """
MATCH (s:Session {id: $id})
SET s.status         = $status,
    s.coverage_score = $coverage_score,
    s.turn_count     = $turn_count,
    s.updated_at     = $updated_at,
    s.completed_at   = $completed_at
"""

_GET_SESSION_BY_ID = """
MATCH (s:Session {id: $id})
RETURN s
"""

_GET_SESSIONS_BY_USER = """
MATCH (s:Session {user_id: $user_id})
RETURN s
ORDER BY s.created_at DESC
LIMIT $limit
"""

_GET_SESSIONS_BY_STATUS = """
MATCH (s:Session {status: $status})
RETURN s
ORDER BY s.created_at DESC
LIMIT $limit
"""

_CREATE_TURN = """
MATCH (s:Session {id: $session_id})
CREATE (t:Turn {
    id:                $id,
    session_id:        $session_id,
    sequence:          $sequence,
    user_input:        $user_input,
    agent_response:    $agent_response,
    intent_classified: $intent_classified,
    provider_used:     $provider_used,
    modality:          $modality,
    status:            $status,
    coverage_delta:    $coverage_delta,
    latency_ms:        $latency_ms,
    hitl_triggered:    $hitl_triggered,
    created_at:        $created_at
})
CREATE (s)-[:HAS_TURN {sequence: $sequence}]->(t)
"""

_GET_TURNS_BY_SESSION = """
MATCH (s:Session {id: $session_id})-[:HAS_TURN]->(t:Turn)
RETURN t
ORDER BY t.sequence ASC
LIMIT $limit
"""

_GET_TURN_BY_ID = """
MATCH (t:Turn {id: $id})
RETURN t
"""

_GET_RECENT_TURNS = """
MATCH (s:Session {id: $session_id})-[:HAS_TURN]->(t:Turn)
RETURN t
ORDER BY t.sequence DESC
LIMIT $limit
"""

_COUNT_TURNS = """
MATCH (s:Session {id: $session_id})-[:HAS_TURN]->(t:Turn)
RETURN count(t) AS turn_count
"""


class SessionRepository(BaseRepository):
    """Read and write Session and Turn nodes in Neo4j.

    All methods are async. All queries run through execute_write or
    execute_read — no sync driver, no run_in_executor.
    """

    def __init__(self, driver: AsyncDriver, database: str = "neo4j") -> None:
        """Initialise SessionRepository.

        Args:
            driver: Injected async Neo4j driver.
            database: Target database name.
        """
        super().__init__(driver, database)

    # ── Session writes ────────────────────────────────────────────────────────

    async def save_session(self, session: Session) -> None:
        """Persist a new Session node.

        Args:
            session: Session to create in Neo4j.
        """
        await self._execute_write(self._save_session_tx, session=session)

    async def update_session(self, session: Session) -> None:
        """Update mutable fields on an existing Session node.

        Only status, coverage_score, turn_count, updated_at, and
        completed_at are updated. Immutable fields (id, user_id,
        agent_type) are never overwritten.

        Args:
            session: Session with updated field values.
        """
        await self._execute_write(self._update_session_tx, session=session)

    # ── Session reads ─────────────────────────────────────────────────────────

    async def get_session(self, session_id: UUID) -> Session | None:
        """Return a Session by id, or None if not found.

        Args:
            session_id: Session UUID.

        Returns:
            Session model or None.
        """
        rows = await self._execute_read(
            self._get_session_tx, session_id=str(session_id)
        )
        return self._row_to_session(rows[0]) if rows else None

    async def get_sessions_by_user(
        self, user_id: str, limit: int = 20
    ) -> list[Session]:
        """Return sessions for a user ordered newest first.

        Args:
            user_id: User identifier.
            limit: Maximum number of sessions to return.

        Returns:
            List of Session models.
        """
        rows = await self._execute_read(
            self._get_sessions_by_user_tx, user_id=user_id, limit=limit
        )
        return [self._row_to_session(r) for r in rows]

    async def get_sessions_by_status(
        self, status: SessionStatus, limit: int = 100
    ) -> list[Session]:
        """Return sessions with a given status.

        Args:
            status: SessionStatus filter.
            limit: Maximum number of sessions to return.

        Returns:
            List of Session models.
        """
        rows = await self._execute_read(
            self._get_sessions_by_status_tx,
            status=status.value,
            limit=limit,
        )
        return [self._row_to_session(r) for r in rows]

    # ── Turn writes ───────────────────────────────────────────────────────────

    async def save_turn(self, turn: Turn) -> None:
        """Persist a new Turn node linked to its parent Session.

        Args:
            turn: Turn to create in Neo4j.

        Raises:
            neo4j.exceptions.ConstraintError: If session_id does not exist.
        """
        await self._execute_write(self._save_turn_tx, turn=turn)

    # ── Turn reads ────────────────────────────────────────────────────────────

    async def get_turn(self, turn_id: UUID) -> Turn | None:
        """Return a Turn by id, or None if not found.

        Args:
            turn_id: Turn UUID.

        Returns:
            Turn model or None.
        """
        rows = await self._execute_read(
            self._get_turn_tx, turn_id=str(turn_id)
        )
        return self._row_to_turn(rows[0]) if rows else None

    async def get_turns_by_session(
        self, session_id: UUID, limit: int = 200
    ) -> list[Turn]:
        """Return all turns for a session ordered by sequence ascending.

        Args:
            session_id: Session UUID.
            limit: Maximum number of turns.

        Returns:
            List of Turn models in chronological order.
        """
        rows = await self._execute_read(
            self._get_turns_by_session_tx,
            session_id=str(session_id),
            limit=limit,
        )
        return [self._row_to_turn(r) for r in rows]

    async def get_recent_turns(
        self, session_id: UUID, limit: int = 10
    ) -> list[Turn]:
        """Return the N most recent turns for a session, newest first.

        Used by ContextBuilder to assemble conversation history.

        Args:
            session_id: Session UUID.
            limit: Number of recent turns to return.

        Returns:
            List of Turn models newest-first.
        """
        rows = await self._execute_read(
            self._get_recent_turns_tx,
            session_id=str(session_id),
            limit=limit,
        )
        return [self._row_to_turn(r) for r in rows]

    async def count_turns(self, session_id: UUID) -> int:
        """Return the total number of turns for a session.

        Args:
            session_id: Session UUID.

        Returns:
            Turn count as integer.
        """
        rows = await self._execute_read(
            self._count_turns_tx, session_id=str(session_id)
        )
        return int(rows[0]["turn_count"]) if rows else 0

    # ── Transaction functions ─────────────────────────────────────────────────

    @staticmethod
    async def _save_session_tx(
        tx: AsyncManagedTransaction, session: Session
    ) -> list[dict[str, object]]:
        return await BaseRepository._run(
            tx,
            _CREATE_SESSION,
            {
                "id": str(session.id),
                "user_id": session.user_id,
                "agent_type": session.agent_type,
                "status": session.status.value,
                "llm_config_snapshot": json.dumps(
                    session.llm_config_snapshot.model_dump()
                ),
                "session_update_policy": session.session_update_policy,
                "coverage_score": session.coverage_score,
                "turn_count": session.turn_count,
                "created_at": session.created_at,
                "updated_at": session.updated_at,
                "completed_at": session.completed_at,
                "metadata": json.dumps(session.metadata),
            },
        )

    @staticmethod
    async def _update_session_tx(
        tx: AsyncManagedTransaction, session: Session
    ) -> list[dict[str, object]]:
        return await BaseRepository._run(
            tx,
            _UPDATE_SESSION,
            {
                "id": str(session.id),
                "status": session.status.value,
                "coverage_score": session.coverage_score,
                "turn_count": session.turn_count,
                "updated_at": session.updated_at,
                "completed_at": session.completed_at,
            },
        )

    @staticmethod
    async def _get_session_tx(
        tx: AsyncManagedTransaction, session_id: str
    ) -> list[dict[str, object]]:
        return await BaseRepository._run(tx, _GET_SESSION_BY_ID, {"id": session_id})

    @staticmethod
    async def _get_sessions_by_user_tx(
        tx: AsyncManagedTransaction, user_id: str, limit: int
    ) -> list[dict[str, object]]:
        return await BaseRepository._run(
            tx, _GET_SESSIONS_BY_USER, {"user_id": user_id, "limit": limit}
        )

    @staticmethod
    async def _get_sessions_by_status_tx(
        tx: AsyncManagedTransaction, status: str, limit: int
    ) -> list[dict[str, object]]:
        return await BaseRepository._run(
            tx, _GET_SESSIONS_BY_STATUS, {"status": status, "limit": limit}
        )

    @staticmethod
    async def _save_turn_tx(
        tx: AsyncManagedTransaction, turn: Turn
    ) -> list[dict[str, object]]:
        return await BaseRepository._run(
            tx,
            _CREATE_TURN,
            {
                "id": str(turn.id),
                "session_id": str(turn.session_id),
                "sequence": turn.sequence,
                "user_input": turn.user_input,
                "agent_response": turn.agent_response,
                "intent_classified": turn.intent_classified,
                "provider_used": turn.provider_used,
                "modality": turn.modality.value,
                "status": turn.status.value,
                "coverage_delta": turn.coverage_delta,
                "latency_ms": turn.latency_ms,
                "hitl_triggered": turn.hitl_triggered,
                "created_at": turn.created_at,
            },
        )

    @staticmethod
    async def _get_turn_tx(
        tx: AsyncManagedTransaction, turn_id: str
    ) -> list[dict[str, object]]:
        return await BaseRepository._run(tx, _GET_TURN_BY_ID, {"id": turn_id})

    @staticmethod
    async def _get_turns_by_session_tx(
        tx: AsyncManagedTransaction, session_id: str, limit: int
    ) -> list[dict[str, object]]:
        return await BaseRepository._run(
            tx, _GET_TURNS_BY_SESSION, {"session_id": session_id, "limit": limit}
        )

    @staticmethod
    async def _get_recent_turns_tx(
        tx: AsyncManagedTransaction, session_id: str, limit: int
    ) -> list[dict[str, object]]:
        return await BaseRepository._run(
            tx, _GET_RECENT_TURNS, {"session_id": session_id, "limit": limit}
        )

    @staticmethod
    async def _count_turns_tx(
        tx: AsyncManagedTransaction, session_id: str
    ) -> list[dict[str, object]]:
        return await BaseRepository._run(tx, _COUNT_TURNS, {"session_id": session_id})

    # ── Mapping helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _row_to_session(record: dict[str, object]) -> Session:
        """Map a Neo4j record to a Session model."""
        node: dict[str, object] = record.get("s", record)  # type: ignore[assignment]
        raw_snap = node["llm_config_snapshot"]
        snap_dict: dict[str, object] = (
            json.loads(raw_snap) if isinstance(raw_snap, str) else raw_snap  # type: ignore[arg-type]
        )
        raw_meta = node.get("metadata", "{}")
        meta: dict[str, str] = (
            json.loads(raw_meta) if isinstance(raw_meta, str) else raw_meta  # type: ignore[arg-type]
        )
        return Session(
            id=UUID(str(node["id"])),
            user_id=str(node["user_id"]),
            agent_type=str(node["agent_type"]),
            status=SessionStatus(str(node["status"])),
            llm_config_snapshot=LLMConfigSnapshot.model_validate(snap_dict),
            session_update_policy=str(node["session_update_policy"]),
            coverage_score=float(node["coverage_score"]),  # type: ignore[arg-type]
            turn_count=int(node["turn_count"]),  # type: ignore[arg-type]
            created_at=str(node["created_at"]),
            updated_at=str(node["updated_at"]),
            completed_at=str(node["completed_at"]) if node.get("completed_at") else None,
            metadata=meta,
        )

    @staticmethod
    def _row_to_turn(record: dict[str, object]) -> Turn:
        """Map a Neo4j record to a Turn model."""
        node: dict[str, object] = record.get("t", record)  # type: ignore[assignment]
        return Turn(
            id=UUID(str(node["id"])),
            session_id=UUID(str(node["session_id"])),
            sequence=int(node["sequence"]),  # type: ignore[arg-type]
            user_input=str(node["user_input"]),
            agent_response=str(node["agent_response"]),
            intent_classified=str(node["intent_classified"]),
            provider_used=str(node["provider_used"]),
            modality=InputModality(str(node["modality"])),
            status=TurnStatus(str(node["status"])),
            coverage_delta=float(node["coverage_delta"]),  # type: ignore[arg-type]
            latency_ms=int(node["latency_ms"]),  # type: ignore[arg-type]
            hitl_triggered=bool(node["hitl_triggered"]),
            created_at=str(node["created_at"]),
        )
