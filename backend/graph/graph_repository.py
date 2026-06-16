from datetime import datetime, timezone
from typing import List

from graph.graph_client import graph_client
from graph.cypher_queries import SAVE_TURN, GET_SESSION_HISTORY, GET_CONVERSATIONS_BY_USER


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

    def get_session_history(self, session_id: str, limit: int = 10) -> List[dict]:
        rows = graph_client.run(GET_SESSION_HISTORY, session_id=session_id)
        turns = []
        for r in rows:
            ai_text = r["ai_response_text"] or ""
            # Strip any accidentally-stored raw JSON — only keep the spoken text field
            if ai_text.lstrip().startswith("{"):
                try:
                    import json
                    parsed = json.loads(ai_text)
                    ai_text = (
                        parsed.get("ai_response_text")
                        or parsed.get("ai_summary")
                        or next((s["body"] for s in parsed.get("sections", []) if s.get("body")), "")
                        or ""
                    )
                except Exception:
                    ai_text = ""
            turns.append({"user_input": r["user_input"] or "", "ai_response_text": ai_text})
        return turns[-limit:]

    def get_conversations_by_user(self, user_id: str) -> List[dict]:
        return graph_client.run(GET_CONVERSATIONS_BY_USER, user_id=user_id)


graph_repo = GraphRepository()
