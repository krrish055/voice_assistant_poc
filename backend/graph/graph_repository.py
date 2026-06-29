import json
from datetime import datetime, timezone
from typing import List

from graph.graph_client import graph_client
from graph.cypher_queries import SAVE_TURN, GET_SESSION_HISTORY, GET_CONVERSATIONS_BY_USER
from config import MAX_REPORT_HISTORY_LIMIT


class GraphRepository:
    """All Neo4j business operations. No driver code — delegates to graph_client."""

    def save_turn(self, user_id: str, session_id: str, user_said: str, ai_response: str) -> None:
        graph_client.run_write(
            SAVE_TURN,
            user_id=user_id,
            session_id=session_id,
            user_said=user_said,
            ai_response=ai_response,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    def get_session_history(self, session_id: str, limit: int = 50) -> List[dict]:
        rows = graph_client.run(GET_SESSION_HISTORY, session_id=session_id, limit=limit)
        turns = []
        for r in rows:
            ai_text = r.get("ai_response_text") or ""
            if ai_text.lstrip().startswith("{"):
                try:
                    parsed = json.loads(ai_text)
                    # Replay safety: only allow plain assistant text from ai_response_text.
                    # Do NOT replay structured report/tool payloads derived from ai_summary or sections[*].body.
                    ai_text = parsed.get("ai_response_text") or ""
                    if not ai_text.strip():
                        ai_text = "[Structured response omitted]"
                except Exception:
                    ai_text = "[Structured response omitted]"
            turns.append({"user_input": r.get("user_input") or "", "ai_response_text": ai_text})
        return turns


    def get_conversations_by_user(self, user_id: str) -> List[dict]:
        return graph_client.run(GET_CONVERSATIONS_BY_USER, user_id=user_id)

    def get_full_session_history(self, session_id: str) -> List[dict]:
        """Fetch every turn for a session from Neo4j — no limit.
        Used exclusively for report generation so the LLM sees the complete conversation.
        """
        return self.get_session_history(session_id, limit=MAX_REPORT_HISTORY_LIMIT)


graph_repo = GraphRepository()