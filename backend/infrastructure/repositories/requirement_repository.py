"""RequirementRepository — Neo4j persistence for Requirement graph nodes.

Single responsibility: read and write Requirement nodes and their
relationships (DEPENDS_ON, CONTRADICTS, REFINES, EXTRACTED_FROM).
No business logic. No coverage computation. No inference logic.
"""

from __future__ import annotations

from uuid import UUID

from neo4j import AsyncDriver, AsyncManagedTransaction

from backend.infrastructure.repositories.base_repository import BaseRepository
from backend.models.requirement import (
    Requirement,
    RequirementDimension,
    RequirementRelationship,
    RequirementRelationshipType,
    RequirementStatus,
)

# ── Cypher constants ──────────────────────────────────────────────────────────

_CREATE_REQUIREMENT = """
MATCH (s:Session {id: $session_id})
CREATE (r:Requirement {
    id:             $id,
    session_id:     $session_id,
    dimension:      $dimension,
    sub_dimension:  $sub_dimension,
    content:        $content,
    confidence:     $confidence,
    source_turn_id: $source_turn_id,
    status:         $status,
    created_at:     $created_at,
    updated_at:     $updated_at
})
CREATE (s)-[:HAS_REQUIREMENT]->(r)
"""

_UPDATE_REQUIREMENT_STATUS = """
MATCH (r:Requirement {id: $id})
SET r.status     = $status,
    r.confidence = $confidence,
    r.updated_at = $updated_at
"""

_GET_REQUIREMENT_BY_ID = """
MATCH (r:Requirement {id: $id})
RETURN r
"""

_GET_REQUIREMENTS_BY_SESSION = """
MATCH (s:Session {id: $session_id})-[:HAS_REQUIREMENT]->(r:Requirement)
RETURN r
ORDER BY r.created_at ASC
"""

_GET_REQUIREMENTS_BY_DIMENSION = """
MATCH (s:Session {id: $session_id})-[:HAS_REQUIREMENT]->(r:Requirement {dimension: $dimension})
RETURN r
ORDER BY r.created_at ASC
"""

_GET_REQUIREMENTS_BY_STATUS = """
MATCH (s:Session {id: $session_id})-[:HAS_REQUIREMENT]->(r:Requirement {status: $status})
RETURN r
ORDER BY r.created_at ASC
"""

_CREATE_RELATIONSHIP = """
MATCH (a:Requirement {id: $source_id})
MATCH (b:Requirement {id: $target_id})
CREATE (a)-[:{rel_type}]->(b)
"""

_GET_RELATIONSHIPS = """
MATCH (a:Requirement {id: $source_id})-[rel]->(b:Requirement)
WHERE type(rel) IN $rel_types
RETURN a.id AS source_id, b.id AS target_id, type(rel) AS relationship_type
"""

_COUNT_BY_DIMENSION = """
MATCH (s:Session {id: $session_id})-[:HAS_REQUIREMENT]->(r:Requirement)
RETURN r.dimension AS dimension, count(r) AS total
"""




class RequirementRepository(BaseRepository):
    """Read and write Requirement nodes and relationships in Neo4j.

    All methods are async. All queries run through execute_write or
    execute_read — no sync driver, no run_in_executor.
    """

    def __init__(self, driver: AsyncDriver, database: str = "neo4j") -> None:
        """Initialise RequirementRepository.

        Args:
            driver: Injected async Neo4j driver.
            database: Target database name.
        """
        super().__init__(driver, database)

    # ── Requirement writes ────────────────────────────────────────────────────

    async def save_requirement(self, requirement: Requirement) -> None:
        """Persist a new Requirement node linked to its parent Session.

        Args:
            requirement: Requirement to create in Neo4j.
        """
        await self._execute_write(
            self._save_requirement_tx, requirement=requirement
        )

    async def save_many(self, requirements: list[Requirement]) -> None:
        """Persist multiple Requirement nodes in a single transaction.

        Args:
            requirements: List of Requirement instances to create.
        """
        await self._execute_write(
            self._save_many_tx, requirements=requirements
        )

    async def update_status(
        self,
        requirement_id: UUID,
        status: RequirementStatus,
        confidence: float,
        updated_at: str,
    ) -> None:
        """Update the status and confidence of an existing Requirement.

        Args:
            requirement_id: Requirement UUID to update.
            status: New RequirementStatus value.
            confidence: Updated confidence score.
            updated_at: ISO 8601 timestamp string.
        """
        await self._execute_write(
            self._update_status_tx,
            req_id=str(requirement_id),
            status=status.value,
            confidence=confidence,
            updated_at=updated_at,
        )

    async def save_relationship(self, rel: RequirementRelationship) -> None:
        """Create a directed relationship between two Requirement nodes.

        Args:
            rel: RequirementRelationship defining source, target, and type.
        """
        await self._execute_write(self._save_relationship_tx, rel=rel)

    # ── Requirement reads ─────────────────────────────────────────────────────

    async def get_requirement(self, requirement_id: UUID) -> Requirement | None:
        """Return a Requirement by id, or None if not found.

        Args:
            requirement_id: Requirement UUID.

        Returns:
            Requirement model or None.
        """
        rows = await self._execute_read(
            self._get_requirement_tx, req_id=str(requirement_id)
        )
        return self._row_to_requirement(rows[0]) if rows else None

    async def get_by_session(self, session_id: UUID) -> list[Requirement]:
        """Return all requirements for a session ordered by creation time.

        Args:
            session_id: Session UUID.

        Returns:
            List of Requirement models.
        """
        rows = await self._execute_read(
            self._get_by_session_tx, session_id=str(session_id)
        )
        return [self._row_to_requirement(r) for r in rows]

    async def get_by_dimension(
        self, session_id: UUID, dimension: RequirementDimension
    ) -> list[Requirement]:
        """Return requirements for a specific dimension within a session.

        Args:
            session_id: Session UUID.
            dimension: RequirementDimension to filter by.

        Returns:
            List of Requirement models for that dimension.
        """
        rows = await self._execute_read(
            self._get_by_dimension_tx,
            session_id=str(session_id),
            dimension=dimension.value,
        )
        return [self._row_to_requirement(r) for r in rows]

    async def get_by_status(
        self, session_id: UUID, status: RequirementStatus
    ) -> list[Requirement]:
        """Return requirements filtered by status within a session.

        Args:
            session_id: Session UUID.
            status: RequirementStatus filter.

        Returns:
            List of Requirement models.
        """
        rows = await self._execute_read(
            self._get_by_status_tx,
            session_id=str(session_id),
            status=status.value,
        )
        return [self._row_to_requirement(r) for r in rows]

    async def get_relationships(
        self,
        source_id: UUID,
        rel_types: list[RequirementRelationshipType] | None = None,
    ) -> list[RequirementRelationship]:
        """Return outgoing relationships from a Requirement node.

        Args:
            source_id: Source Requirement UUID.
            rel_types: Optional filter list. If None returns all types.

        Returns:
            List of RequirementRelationship instances.
        """
        all_types = [r.value for r in RequirementRelationshipType]
        filter_types = (
            [r.value for r in rel_types] if rel_types else all_types
        )
        rows = await self._execute_read(
            self._get_relationships_tx,
            source_id=str(source_id),
            rel_types=filter_types,
        )
        return [self._row_to_relationship(r) for r in rows]

    async def count_by_dimension(
        self, session_id: UUID
    ) -> dict[RequirementDimension, int]:
        """Return requirement counts grouped by dimension for a session.

        Args:
            session_id: Session UUID.

        Returns:
            Dict mapping RequirementDimension to integer count.
        """
        rows = await self._execute_read(
            self._count_by_dimension_tx, session_id=str(session_id)
        )
        result: dict[RequirementDimension, int] = {}
        for row in rows:
            dim = RequirementDimension(str(row["dimension"]))
            result[dim] = int(row["total"])  # type: ignore[arg-type]
        return result

    # ── Transaction functions ─────────────────────────────────────────────────

    @staticmethod
    async def _save_requirement_tx(
        tx: AsyncManagedTransaction, requirement: Requirement
    ) -> list[dict[str, object]]:
        return await BaseRepository._run(
            tx,
            _CREATE_REQUIREMENT,
            {
                "id": str(requirement.id),
                "session_id": str(requirement.session_id),
                "dimension": requirement.dimension.value,
                "sub_dimension": requirement.sub_dimension,
                "content": requirement.content,
                "confidence": requirement.confidence,
                "source_turn_id": (
                    str(requirement.source_turn_id)
                    if requirement.source_turn_id
                    else None
                ),
                "status": requirement.status.value,
                "created_at": requirement.created_at,
                "updated_at": requirement.updated_at,
            },
        )

    @staticmethod
    async def _save_many_tx(
        tx: AsyncManagedTransaction, requirements: list[Requirement]
    ) -> list[dict[str, object]]:
        for req in requirements:
            await BaseRepository._run(
                tx,
                _CREATE_REQUIREMENT,
                {
                    "id": str(req.id),
                    "session_id": str(req.session_id),
                    "dimension": req.dimension.value,
                    "sub_dimension": req.sub_dimension,
                    "content": req.content,
                    "confidence": req.confidence,
                    "source_turn_id": (
                        str(req.source_turn_id) if req.source_turn_id else None
                    ),
                    "status": req.status.value,
                    "created_at": req.created_at,
                    "updated_at": req.updated_at,
                },
            )
        return []

    @staticmethod
    async def _update_status_tx(
        tx: AsyncManagedTransaction,
        req_id: str,
        status: str,
        confidence: float,
        updated_at: str,
    ) -> list[dict[str, object]]:
        return await BaseRepository._run(
            tx,
            _UPDATE_REQUIREMENT_STATUS,
            {"id": req_id, "status": status, "confidence": confidence, "updated_at": updated_at},
        )

    @staticmethod
    async def _save_relationship_tx(
        tx: AsyncManagedTransaction, rel: RequirementRelationship
    ) -> list[dict[str, object]]:
        query = _CREATE_RELATIONSHIP.format(rel_type=rel.relationship_type.value)
        return await BaseRepository._run(
            tx,
            query,
            {"source_id": str(rel.source_id), "target_id": str(rel.target_id)},
        )

    @staticmethod
    async def _get_requirement_tx(
        tx: AsyncManagedTransaction, req_id: str
    ) -> list[dict[str, object]]:
        return await BaseRepository._run(tx, _GET_REQUIREMENT_BY_ID, {"id": req_id})

    @staticmethod
    async def _get_by_session_tx(
        tx: AsyncManagedTransaction, session_id: str
    ) -> list[dict[str, object]]:
        return await BaseRepository._run(
            tx, _GET_REQUIREMENTS_BY_SESSION, {"session_id": session_id}
        )

    @staticmethod
    async def _get_by_dimension_tx(
        tx: AsyncManagedTransaction, session_id: str, dimension: str
    ) -> list[dict[str, object]]:
        return await BaseRepository._run(
            tx,
            _GET_REQUIREMENTS_BY_DIMENSION,
            {"session_id": session_id, "dimension": dimension},
        )

    @staticmethod
    async def _get_by_status_tx(
        tx: AsyncManagedTransaction, session_id: str, status: str
    ) -> list[dict[str, object]]:
        return await BaseRepository._run(
            tx,
            _GET_REQUIREMENTS_BY_STATUS,
            {"session_id": session_id, "status": status},
        )

    @staticmethod
    async def _get_relationships_tx(
        tx: AsyncManagedTransaction, source_id: str, rel_types: list[str]
    ) -> list[dict[str, object]]:
        return await BaseRepository._run(
            tx, _GET_RELATIONSHIPS, {"source_id": source_id, "rel_types": rel_types}
        )

    @staticmethod
    async def _count_by_dimension_tx(
        tx: AsyncManagedTransaction, session_id: str
    ) -> list[dict[str, object]]:
        return await BaseRepository._run(
            tx, _COUNT_BY_DIMENSION, {"session_id": session_id}
        )

    # ── Mapping helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _row_to_requirement(record: dict[str, object]) -> Requirement:
        """Map a Neo4j record to a Requirement model."""
        node: dict[str, object] = record.get("r", record)  # type: ignore[assignment]
        return Requirement(
            id=UUID(str(node["id"])),
            session_id=UUID(str(node["session_id"])),
            dimension=RequirementDimension(str(node["dimension"])),
            sub_dimension=str(node["sub_dimension"]),
            content=str(node["content"]),
            confidence=float(node["confidence"]),  # type: ignore[arg-type]
            source_turn_id=(
                UUID(str(node["source_turn_id"]))
                if node.get("source_turn_id")
                else None
            ),
            status=RequirementStatus(str(node["status"])),
            created_at=str(node["created_at"]),
            updated_at=str(node["updated_at"]),
        )

    @staticmethod
    def _row_to_relationship(record: dict[str, object]) -> RequirementRelationship:
        """Map a Neo4j record to a RequirementRelationship model."""
        return RequirementRelationship(
            source_id=UUID(str(record["source_id"])),
            target_id=UUID(str(record["target_id"])),
            relationship_type=RequirementRelationshipType(
                str(record["relationship_type"])
            ),
        )
