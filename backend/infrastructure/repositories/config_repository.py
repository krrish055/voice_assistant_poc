"""ConfigRepository — persists registry ConfigSnapshot nodes to Neo4j.

Single responsibility: write and read ConfigSnapshot chain for all registries.
Called exclusively by BaseRegistry.update() as part of the persist-first pattern.
"""

from __future__ import annotations

from uuid import UUID

from neo4j import AsyncDriver, AsyncManagedTransaction

from backend.infrastructure.repositories.base_repository import BaseRepository
from backend.models.config import ConfigSnapshot


class ConfigRepository(BaseRepository):
    """Persists and retrieves ConfigSnapshot nodes for all registries.

    ConfigSnapshot chain semantics:
    - Every registry update writes a new ConfigSnapshot node.
    - The new snapshot points to the previous via a SUPERSEDES relationship.
    - The latest snapshot for a registry+key is the one with no outgoing
      SUPERSEDES relationship (i.e., nothing supersedes it yet).
    """

    def __init__(self, driver: AsyncDriver, database: str = "neo4j") -> None:
        """Initialise ConfigRepository.

        Args:
            driver: Injected async Neo4j driver.
            database: Target database. Defaults to "neo4j".
        """
        super().__init__(driver, database)

    async def save_snapshot(self, snapshot: ConfigSnapshot) -> None:
        """Persist a new ConfigSnapshot and link it to its predecessor.

        This is called by BaseRegistry BEFORE the in-memory update is applied
        (persist-first pattern). If this raises, the caller aborts the update.

        Args:
            snapshot: The ConfigSnapshot to persist.
        """
        await self._execute_write(self._save_snapshot_tx, snapshot=snapshot)

    async def get_latest_snapshot(
        self, registry_name: str, config_key: str
    ) -> ConfigSnapshot | None:
        """Return the most recent ConfigSnapshot for a registry+key combination.

        Args:
            registry_name: Name of the registry (e.g. "llm_provider").
            config_key: The specific key within that registry.

        Returns:
            The latest ConfigSnapshot, or None if no snapshot exists.
        """
        result = await self._execute_read(
            self._get_latest_snapshot_tx,
            registry_name=registry_name,
            config_key=config_key,
        )
        records = list(result)  # type: ignore[arg-type]
        if not records:
            return None
        return self._record_to_snapshot(records[0])

    async def get_snapshot_history(
        self, registry_name: str, config_key: str, limit: int = 20
    ) -> list[ConfigSnapshot]:
        """Return the N most recent snapshots for a registry+key, newest first.

        Args:
            registry_name: Name of the registry.
            config_key: The specific key within that registry.
            limit: Maximum number of snapshots to return.

        Returns:
            List of ConfigSnapshot instances ordered newest-first.
        """
        result = await self._execute_read(
            self._get_snapshot_history_tx,
            registry_name=registry_name,
            config_key=config_key,
            limit=limit,
        )
        return [self._record_to_snapshot(r) for r in result]  # type: ignore[union-attr]

    # ──────────────────────────── transaction functions ────────────────────────

    @staticmethod
    async def _save_snapshot_tx(
        tx: AsyncManagedTransaction,
        snapshot: ConfigSnapshot,
    ) -> None:
        """Cypher: create ConfigSnapshot node and SUPERSEDES relationship."""
        create_query = """
        CREATE (s:ConfigSnapshot {
            id:              $id,
            registry_name:   $registry_name,
            config_key:      $config_key,
            new_value:       $new_value,
            previous_value:  $previous_value,
            changed_by:      $changed_by,
            changed_at:      $changed_at
        })
        """
        params: dict[str, object] = {
            "id": str(snapshot.id),
            "registry_name": snapshot.registry_name,
            "config_key": snapshot.config_key,
            "new_value": str(snapshot.new_value),
            "previous_value": str(snapshot.previous_value) if snapshot.previous_value else None,
            "changed_by": snapshot.changed_by,
            "changed_at": snapshot.changed_at,
        }
        await BaseRepository._run(tx, create_query, params)

        if snapshot.supersedes_id is not None:
            link_query = """
            MATCH (new:ConfigSnapshot {id: $new_id})
            MATCH (old:ConfigSnapshot {id: $old_id})
            CREATE (new)-[:SUPERSEDES]->(old)
            """
            await BaseRepository._run(
                tx,
                link_query,
                {"new_id": str(snapshot.id), "old_id": str(snapshot.supersedes_id)},
            )

    @staticmethod
    async def _get_latest_snapshot_tx(
        tx: AsyncManagedTransaction,
        registry_name: str,
        config_key: str,
    ) -> list[dict[str, object]]:
        """Cypher: find the latest ConfigSnapshot (no outgoing SUPERSEDES)."""
        query = """
        MATCH (s:ConfigSnapshot {registry_name: $registry_name, config_key: $config_key})
        WHERE NOT (s)-[:SUPERSEDES]->(:ConfigSnapshot)
        RETURN s
        ORDER BY s.changed_at DESC
        LIMIT 1
        """
        return await BaseRepository._run(
            tx, query, {"registry_name": registry_name, "config_key": config_key}
        )

    @staticmethod
    async def _get_snapshot_history_tx(
        tx: AsyncManagedTransaction,
        registry_name: str,
        config_key: str,
        limit: int,
    ) -> list[dict[str, object]]:
        """Cypher: return N most recent snapshots newest-first."""
        query = """
        MATCH (s:ConfigSnapshot {registry_name: $registry_name, config_key: $config_key})
        RETURN s
        ORDER BY s.changed_at DESC
        LIMIT $limit
        """
        return await BaseRepository._run(
            tx,
            query,
            {"registry_name": registry_name, "config_key": config_key, "limit": limit},
        )

    # ──────────────────────────── mapping helpers ───────────────────────────────

    @staticmethod
    def _record_to_snapshot(record: dict[str, object]) -> ConfigSnapshot:
        """Map a Neo4j record dict to a ConfigSnapshot model."""
        node = record.get("s", record)
        return ConfigSnapshot(
            id=UUID(str(node["id"])),  # type: ignore[arg-type]
            registry_name=str(node["registry_name"]),
            config_key=str(node["config_key"]),
            new_value={"_raw": str(node["new_value"])},
            previous_value={"_raw": str(node["previous_value"])} if node.get("previous_value") else None,
            changed_by=str(node["changed_by"]),
            changed_at=str(node["changed_at"]),
        )
