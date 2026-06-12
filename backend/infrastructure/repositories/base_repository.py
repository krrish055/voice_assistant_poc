"""BaseRepository — shared async Neo4j driver wrapper.

All repositories extend this class.
No sync driver. No run_in_executor. No threading.Lock.
The neo4j async driver manages its own connection pool internally.

Transaction paths:
  _execute_write / _execute_read  — auto-commit, driver-managed retry.
  _execute_with_tx                — accepts an externally supplied
                                    AsyncManagedTransaction for use by
                                    TransactionManager (Phase 5).
"""

from __future__ import annotations

from abc import ABC
from collections.abc import Callable, Coroutine
from typing import Concatenate, ParamSpec

from neo4j import AsyncDriver, AsyncManagedTransaction

_P = ParamSpec("_P")
_TxFn = Callable[Concatenate[AsyncManagedTransaction, _P], Coroutine[object, object, list[dict[str, object]]]]


class BaseRepository(ABC):
    """Abstract base providing a shared async Neo4j driver to all repositories.

    Construction requires an AsyncDriver injected from the application lifespan.
    No global driver state — each repository instance holds a reference to the
    shared driver supplied at startup.

    Usage (auto-commit):
        records = await self._execute_write(self._some_tx, key=value)

    Usage (external transaction — TransactionManager):
        records = await self._execute_with_tx(tx, self._some_tx, key=value)
    """

    def __init__(self, driver: AsyncDriver, database: str = "neo4j") -> None:
        """Initialise with an injected async Neo4j driver.

        Args:
            driver: AsyncDriver instance created in application lifespan.
            database: Target Neo4j database name. Defaults to "neo4j".
        """
        self._driver = driver
        self._database = database

    async def _execute_write(
        self,
        query_fn: object,
        **kwargs: object,
    ) -> list[dict[str, object]]:
        """Execute a write transaction with automatic retry on transient errors.

        Opens its own session and auto-commit transaction. Use this for
        single-repository operations that do not need to participate in a
        cross-repository atomic unit.

        Args:
            query_fn: Async callable (AsyncManagedTransaction, **kwargs) -> list.
            **kwargs: Keyword arguments forwarded to query_fn.

        Returns:
            List of result record dicts.
        """
        async with self._driver.session(database=self._database) as session:
            result = await session.execute_write(query_fn, **kwargs)
            return result if isinstance(result, list) else []

    async def _execute_read(
        self,
        query_fn: object,
        **kwargs: object,
    ) -> list[dict[str, object]]:
        """Execute a read transaction with automatic retry on transient errors.

        Opens its own session and read transaction. Use this for single-
        repository read operations.

        Args:
            query_fn: Async callable (AsyncManagedTransaction, **kwargs) -> list.
            **kwargs: Keyword arguments forwarded to query_fn.

        Returns:
            List of result record dicts.
        """
        async with self._driver.session(database=self._database) as session:
            result = await session.execute_read(query_fn, **kwargs)
            return result if isinstance(result, list) else []

    @staticmethod
    async def _execute_with_tx(
        tx: AsyncManagedTransaction,
        query_fn: object,
        **kwargs: object,
    ) -> list[dict[str, object]]:
        """Execute a query function within an externally supplied transaction.

        Called by TransactionManager (Phase 5) to compose multiple repository
        operations into a single atomic unit. The caller owns the transaction
        lifecycle (commit / rollback).

        Args:
            tx: An open AsyncManagedTransaction supplied by the caller.
            query_fn: Async callable (AsyncManagedTransaction, **kwargs) -> list.
            **kwargs: Keyword arguments forwarded to query_fn.

        Returns:
            List of result record dicts.
        """
        result = await query_fn(tx, **kwargs)  # type: ignore[operator]
        return result if isinstance(result, list) else []

    async def verify_connectivity(self) -> None:
        """Verify the driver can reach the Neo4j instance.

        Raises:
            neo4j.exceptions.ServiceUnavailable: If the database is unreachable.
        """
        await self._driver.verify_connectivity()

    @staticmethod
    async def _run(
        tx: AsyncManagedTransaction,
        query: str,
        parameters: dict[str, object] | None = None,
    ) -> list[dict[str, object]]:
        """Execute a single Cypher query within a transaction and return all records.

        Args:
            tx: The active managed transaction.
            query: Cypher query string.
            parameters: Optional query parameters.

        Returns:
            List of records as dicts.
        """
        result = await tx.run(query, parameters or {})
        return [record.data() async for record in result]
