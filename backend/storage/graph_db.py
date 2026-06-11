import logging
import os
from datetime import datetime, timezone
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

    def save_turn(self, user_id: str, session_id: str, user_said: str, ai_response: str):
        query = """
        MERGE (u:User {id: $user_id})
        MERGE (s:Session {id: $session_id})
        MERGE (u)-[:STARTED_SESSION]->(s)
        CREATE (t:ChatTurn {
            user_said: $user_said,
            ai_response: $ai_response,
            timestamp: $timestamp
        })
        CREATE (s)-[:HAS_TURN]->(t)
        """
        try:
            with self.driver.session() as session:
                session.run(
                    query,
                    user_id=user_id,
                    session_id=session_id,
                    user_said=user_said,
                    ai_response=ai_response,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                )
                _log.info("[Neo4j] Turn saved for session: %s", session_id)
        except Exception as e:
            _log.warning("[Neo4j] Failed to save turn: %s", e)

    def close(self):
        self.driver.close()
