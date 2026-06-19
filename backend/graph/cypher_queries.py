SAVE_TURN = """
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

# FIXED: Added LIMIT $limit at the end
GET_SESSION_HISTORY = """
MATCH (s:Session {id: $session_id})-[:HAS_TURN]->(t:ChatTurn)
RETURN t.user_said AS user_input, t.ai_response AS ai_response_text, t.timestamp AS timestamp
ORDER BY t.timestamp ASC
LIMIT $limit
"""

GET_CONVERSATIONS_BY_USER = """
MATCH (u:User {id: $user_id})-[:STARTED_SESSION]->(s:Session)-[:HAS_TURN]->(t:ChatTurn)
RETURN s.id AS session_id, t.user_said AS user_input,
       t.ai_response AS ai_response_text, t.timestamp AS timestamp
ORDER BY t.timestamp ASC
"""