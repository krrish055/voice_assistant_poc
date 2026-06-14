import logging
import os
from datetime import datetime, timezone
from neo4j import GraphDatabase
import time

_log = logging.getLogger(__name__)


class GraphDBConnection:
    def __init__(self):
        try:
            self.driver = GraphDatabase.driver(
                os.getenv("NEO4J_URI"),
                auth=(os.getenv("NEO4J_USERNAME"), os.getenv("NEO4J_PASSWORD")),
                max_connection_lifetime=3600,
                max_connection_pool_size=50,
                connection_acquisition_timeout=60,
                connection_timeout=30,
                keep_alive=True
            )
            self.enabled = True
        except Exception as e:
            _log.error("[Neo4j] Failed to initialize driver: %s", e)
            self.driver = None
            self.enabled = False

    def test_connection(self):
        if not self.enabled or not self.driver:
            _log.warning("[Neo4j] Driver not initialized, skipping connection test")
            return
        try:
            with self.driver.session() as session:
                result = session.run("RETURN 1 AS n").single()
                _log.info("[Neo4j] Connection verified — RETURN 1 => %s", result["n"])
        except Exception as e:
            _log.warning("[Neo4j] Connection test failed: %s", e)
            self.enabled = False

    def save_turn(self, user_id: str, session_id: str, user_said: str, ai_response: str):
        if not self.enabled or not self.driver:
            return
        
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
        
        max_retries = 3
        for attempt in range(max_retries):
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
                    return
            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(0.5 * (attempt + 1))
                    continue
                else:
                    self.enabled = False

    def get_session_history(self, session_id: str, limit: int = 10) -> list:
        """Fetch last N turns for a session to use as LLM context."""
        if not self.enabled or not self.driver:
            return []
        
        query = """
        MATCH (s:Session {id: $session_id})-[:HAS_TURN]->(t:ChatTurn)
        RETURN t.user_said AS user_input, t.ai_response AS ai_response_text, t.timestamp AS timestamp
        ORDER BY t.timestamp ASC
        """
        try:
            with self.driver.session() as session:
                result = session.run(query, session_id=session_id)
                records = [
                    {"user_input": r["user_input"], "ai_response_text": r["ai_response_text"]}
                    for r in result
                ]
                return records[-limit:]
        except Exception as e:
            _log.warning("[Neo4j] Failed to fetch history: %s", e)
            self.enabled = False
            return []

    def close(self):
        if self.driver:
            self.driver.close()
