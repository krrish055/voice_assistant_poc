import logging
import os
import time
from typing import Optional
from neo4j import GraphDatabase, Driver

_log = logging.getLogger(__name__)


class GraphClient:
    """Neo4j driver wrapper. No business logic — only connection management."""

    def __init__(self):
        try:
            self._driver: Optional[Driver] = GraphDatabase.driver(
                os.getenv("NEO4J_URI"),
                auth=(os.getenv("NEO4J_USERNAME"), os.getenv("NEO4J_PASSWORD")),
                max_connection_lifetime=3600,
                max_connection_pool_size=50,
                connection_acquisition_timeout=60,
                connection_timeout=30,
                keep_alive=True,
            )
            self.enabled = True
        except Exception as e:
            _log.error("[Neo4j] Driver init failed: %s", e)
            self._driver = None
            self.enabled = False

    def verify(self) -> None:
        if not self.enabled:
            return
        try:
            with self._driver.session() as s:
                s.run("RETURN 1").single()
                _log.info("[Neo4j] Connection verified")
        except Exception as e:
            _log.warning("[Neo4j] Verification failed: %s", e)
            self.enabled = False

    def run(self, query: str, **params) -> list:
        """Execute a read query with retry. Returns list of record dicts."""
        if not self.enabled:
            return []
        for attempt in range(3):
            try:
                with self._driver.session() as s:
                    return [dict(r) for r in s.run(query, **params)]
            except Exception as e:
                if attempt == 2:
                    _log.warning("[Neo4j] Query failed after retries: %s", e)
                    self.enabled = False
                    return []
                time.sleep(0.5 * (attempt + 1))
        return []

    def run_write(self, query: str, **params) -> None:
        """Execute a write query with retry."""
        if not self.enabled:
            return
        for attempt in range(3):
            try:
                with self._driver.session() as s:
                    s.run(query, **params)
                    return
            except Exception as e:
                if attempt == 2:
                    _log.warning("[Neo4j] Write failed after retries: %s", e)
                    self.enabled = False
                time.sleep(0.5 * (attempt + 1))

    def close(self) -> None:
        if self._driver:
            self._driver.close()


graph_client = GraphClient()
