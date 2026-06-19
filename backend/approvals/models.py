"""
approvals/models.py

Pure value objects for the Approval Workflow domain.
"""
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional
from uuid import uuid4


class ApprovalStatus(str, Enum):
    PENDING    = "PENDING"
    APPROVED   = "APPROVED"
    REJECTED   = "REJECTED"
    PROCESSING = "PROCESSING"
    COMPLETED  = "COMPLETED"
    FAILED     = "FAILED"
    SEEN       = "SEEN"


class ApprovalAction(str, Enum):
    APPROVE = "APPROVE"
    REJECT  = "REJECT"


@dataclass
class ApprovalRequest:
    id:           str
    session_id:   str
    user_id:      str
    request_type: str
    payload:      Dict[str, Any]
    status:       ApprovalStatus
    created_at:   datetime          = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at:   datetime          = field(default_factory=lambda: datetime.now(timezone.utc))
    reviewed_by:  Optional[str]     = None
    notes:        Optional[str]     = None

    @classmethod
    def create(
        cls,
        session_id: str,
        user_id: str,
        request_type: str,
        payload: Dict[str, Any],
    ) -> "ApprovalRequest":
        now = datetime.now(timezone.utc)
        return cls(
            id=str(uuid4()),
            session_id=session_id,
            user_id=user_id,
            request_type=request_type,
            payload=payload,
            status=ApprovalStatus.PENDING,
            created_at=now,
            updated_at=now,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id":           self.id,
            "session_id":   self.session_id,
            "user_id":      self.user_id,
            "request_type": self.request_type,
            "status":       self.status.value,
            "created_at":   self.created_at.isoformat(),
            "updated_at":   self.updated_at.isoformat(),
            "reviewed_by":  self.reviewed_by,
            "notes":        self.notes,
        }

    @classmethod
    def from_record(cls, r: Dict[str, Any]) -> "ApprovalRequest":
        return cls(
            id=r["id"],
            session_id=r.get("session_id", ""),
            user_id=r.get("user_id", ""),
            request_type=r.get("request_type", ""),
            payload=json.loads(r.get("payload", "{}")),
            status=ApprovalStatus(r["status"]),
            created_at=datetime.fromisoformat(r["created_at"]),
            updated_at=datetime.fromisoformat(r["updated_at"]),
            reviewed_by=r.get("reviewed_by"),
            notes=r.get("notes"),
        )
