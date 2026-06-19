"""
jobs/models.py

Pure value objects — no logic, no DB concerns.
"""
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional
from uuid import uuid4


class JobStatus(str, Enum):
    PENDING    = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED  = "COMPLETED"
    FAILED     = "FAILED"


@dataclass
class Job:
    id:            str
    job_type:      str
    status:        JobStatus
    payload:       Dict[str, Any]
    session_id:    str
    user_id:       str
    attempt_count: int               = 0
    created_at:    datetime          = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at:    datetime          = field(default_factory=lambda: datetime.now(timezone.utc))
    error_detail:  Optional[str]     = None

    @classmethod
    def create(cls, job_type: str, payload: Dict[str, Any], session_id: str, user_id: str) -> "Job":
        now = datetime.now(timezone.utc)
        return cls(
            id=str(uuid4()),
            job_type=job_type,
            status=JobStatus.PENDING,
            payload=payload,
            session_id=session_id,
            user_id=user_id,
            created_at=now,
            updated_at=now,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id":            self.id,
            "job_type":      self.job_type,
            "status":        self.status.value,
            "session_id":    self.session_id,
            "user_id":       self.user_id,
            "attempt_count": self.attempt_count,
            "created_at":    self.created_at.isoformat(),
            "updated_at":    self.updated_at.isoformat(),
            "error_detail":  self.error_detail,
        }

    @classmethod
    def from_record(cls, r: Dict[str, Any]) -> "Job":
        return cls(
            id=r["id"],
            job_type=r["job_type"],
            status=JobStatus(r["status"]),
            payload=json.loads(r.get("payload", "{}")),
            session_id=r.get("session_id", ""),
            user_id=r.get("user_id", ""),
            attempt_count=int(r.get("attempt_count", 0)),
            created_at=datetime.fromisoformat(r["created_at"]),
            updated_at=datetime.fromisoformat(r["updated_at"]),
            error_detail=r.get("error_detail"),
        )
