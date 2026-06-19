"""
approvals/repository.py

Neo4j persistence for ApprovalRequest nodes.
"""
import json
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import List, Optional

from graph.graph_client import graph_client
from approvals.models import ApprovalRequest, ApprovalStatus

_log = logging.getLogger(__name__)

_SAVE_APPROVAL = """
MERGE (a:ApprovalRequest {id: $id})
SET a.session_id   = $session_id,
    a.user_id      = $user_id,
    a.request_type = $request_type,
    a.payload      = $payload,
    a.status       = $status,
    a.created_at   = $created_at,
    a.updated_at   = $updated_at,
    a.reviewed_by  = $reviewed_by,
    a.notes        = $notes
WITH a
MATCH (u:User {id: $user_id})
MERGE (u)-[:HAS_APPROVAL]->(a)
"""

_GET_APPROVAL_BY_ID = """
MATCH (a:ApprovalRequest {id: $id})
RETURN a.id AS id, a.session_id AS session_id, a.user_id AS user_id,
       a.request_type AS request_type, a.payload AS payload, a.status AS status,
       a.created_at AS created_at, a.updated_at AS updated_at,
       a.reviewed_by AS reviewed_by, a.notes AS notes
"""

_GET_APPROVALS_BY_STATUS = """
MATCH (a:ApprovalRequest {status: $status})
RETURN a.id AS id, a.session_id AS session_id, a.user_id AS user_id,
       a.request_type AS request_type, a.payload AS payload, a.status AS status,
       a.created_at AS created_at, a.updated_at AS updated_at,
       a.reviewed_by AS reviewed_by, a.notes AS notes
ORDER BY a.created_at ASC
LIMIT $limit
"""

_UPDATE_APPROVAL = """
MATCH (a:ApprovalRequest {id: $id})
SET a.status      = $status,
    a.reviewed_by = $reviewed_by,
    a.notes       = $notes,
    a.updated_at  = $updated_at
"""


class IApprovalRepository(ABC):
    @abstractmethod
    def save(self, approval: ApprovalRequest) -> None: ...

    @abstractmethod
    def get_by_id(self, approval_id: str) -> Optional[ApprovalRequest]: ...

    @abstractmethod
    def get_by_status(self, status: ApprovalStatus, limit: int = 50) -> List[ApprovalRequest]: ...

    @abstractmethod
    def update(self, approval: ApprovalRequest) -> None: ...


class Neo4jApprovalRepository(IApprovalRepository):

    def save(self, approval: ApprovalRequest) -> None:
        graph_client.run_write(
            _SAVE_APPROVAL,
            id=approval.id,
            session_id=approval.session_id,
            user_id=approval.user_id,
            request_type=approval.request_type,
            payload=json.dumps(approval.payload),
            status=approval.status.value,
            created_at=approval.created_at.isoformat(),
            updated_at=approval.updated_at.isoformat(),
            reviewed_by=approval.reviewed_by,
            notes=approval.notes,
        )

    def get_by_id(self, approval_id: str) -> Optional[ApprovalRequest]:
        rows = graph_client.run(_GET_APPROVAL_BY_ID, id=approval_id)
        return ApprovalRequest.from_record(rows[0]) if rows else None

    def get_by_status(self, status: ApprovalStatus, limit: int = 50) -> List[ApprovalRequest]:
        rows = graph_client.run(_GET_APPROVALS_BY_STATUS, status=status.value, limit=limit)
        return [ApprovalRequest.from_record(r) for r in rows]

    def update(self, approval: ApprovalRequest) -> None:
        graph_client.run_write(
            _UPDATE_APPROVAL,
            id=approval.id,
            status=approval.status.value,
            reviewed_by=approval.reviewed_by,
            notes=approval.notes,
            updated_at=datetime.now(timezone.utc).isoformat(),
        )
