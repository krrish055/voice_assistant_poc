import logging
import os
from neo4j import GraphDatabase

_log = logging.getLogger(__name__)


class GraphDBConnection:
    def __init__(self):
        self.driver = GraphDatabase.driver(
            os.getenv("NEO4J_URI"),
            auth=(os.getenv("NEO4J_USERNAME"), os.getenv("NEO4J_PASSWORD")),
        )

    def test_connection(self):
        try:
            with self.driver.session() as session:
                result = session.run("RETURN 1 AS n").single()
                _log.info("[Neo4j] Connection verified — RETURN 1 => %s", result["n"])
        except Exception as e:
            _log.warning("[Neo4j] Connection test failed: %s", e)

    def close(self):
        self.driver.close()
