"""
notifications/repository.py
"""
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import List, Optional

from graph.graph_client import graph_client
from notifications.models import Notification, NotificationStatus

_log = logging.getLogger(__name__)

_SAVE_NOTIFICATION = """
MERGE (n:Notification {id: $id})
SET n.user_id    = $user_id,
    n.message    = $message,
    n.status     = $status,
    n.ref_type   = $ref_type,
    n.ref_id     = $ref_id,
    n.created_at = $created_at,
    n.seen_at    = $seen_at
WITH n
MATCH (u:User {id: $user_id})
MERGE (u)-[:HAS_NOTIFICATION]->(n)
"""

_GET_BY_USER_UNREAD = """
MATCH (n:Notification {user_id: $user_id, status: 'UNREAD'})
RETURN n.id AS id, n.user_id AS user_id, n.message AS message,
       n.status AS status, n.ref_type AS ref_type, n.ref_id AS ref_id,
       n.created_at AS created_at, n.seen_at AS seen_at
ORDER BY n.created_at DESC
LIMIT $limit
"""

_GET_BY_USER_ALL = """
MATCH (n:Notification {user_id: $user_id})
RETURN n.id AS id, n.user_id AS user_id, n.message AS message,
       n.status AS status, n.ref_type AS ref_type, n.ref_id AS ref_id,
       n.created_at AS created_at, n.seen_at AS seen_at
ORDER BY n.created_at DESC
LIMIT $limit
"""

_GET_BY_ID = """
MATCH (n:Notification {id: $id})
RETURN n.id AS id, n.user_id AS user_id, n.message AS message,
       n.status AS status, n.ref_type AS ref_type, n.ref_id AS ref_id,
       n.created_at AS created_at, n.seen_at AS seen_at
"""

_MARK_SEEN = """
MATCH (n:Notification {id: $id})
SET n.status  = 'READ',
    n.seen_at = $seen_at
"""


class INotificationRepository(ABC):
    @abstractmethod
    def save(self, notification: Notification) -> None: ...

    @abstractmethod
    def get_by_user(self, user_id: str, unread_only: bool, limit: int) -> List[Notification]: ...

    @abstractmethod
    def get_by_id(self, notification_id: str) -> Optional[Notification]: ...

    @abstractmethod
    def mark_seen(self, notification_id: str) -> None: ...


class Neo4jNotificationRepository(INotificationRepository):

    def save(self, notification: Notification) -> None:
        graph_client.run_write(
            _SAVE_NOTIFICATION,
            id=notification.id,
            user_id=notification.user_id,
            message=notification.message,
            status=notification.status.value,
            ref_type=notification.ref_type,
            ref_id=notification.ref_id,
            created_at=notification.created_at.isoformat(),
            seen_at=notification.seen_at.isoformat() if notification.seen_at else None,
        )

    def get_by_user(self, user_id: str, unread_only: bool = True, limit: int = 50) -> List[Notification]:
        query = _GET_BY_USER_UNREAD if unread_only else _GET_BY_USER_ALL
        rows  = graph_client.run(query, user_id=user_id, limit=limit)
        return [Notification.from_record(r) for r in rows]

    def get_by_id(self, notification_id: str) -> Optional[Notification]:
        rows = graph_client.run(_GET_BY_ID, id=notification_id)
        return Notification.from_record(rows[0]) if rows else None

    def mark_seen(self, notification_id: str) -> None:
        graph_client.run_write(
            _MARK_SEEN,
            id=notification_id,
            seen_at=datetime.now(timezone.utc).isoformat(),
        )
