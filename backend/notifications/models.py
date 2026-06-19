"""
notifications/models.py
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional
from uuid import uuid4


class NotificationStatus(str, Enum):
    UNREAD = "UNREAD"
    READ   = "READ"


@dataclass
class Notification:
    id:         str
    user_id:    str
    message:    str
    status:     NotificationStatus
    ref_type:   str
    ref_id:     str
    created_at: datetime         = field(default_factory=lambda: datetime.now(timezone.utc))
    seen_at:    Optional[datetime] = None

    @classmethod
    def create(cls, user_id: str, message: str, ref_type: str, ref_id: str) -> "Notification":
        return cls(
            id=str(uuid4()),
            user_id=user_id,
            message=message,
            status=NotificationStatus.UNREAD,
            ref_type=ref_type,
            ref_id=ref_id,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id":         self.id,
            "user_id":    self.user_id,
            "message":    self.message,
            "status":     self.status.value,
            "ref_type":   self.ref_type,
            "ref_id":     self.ref_id,
            "created_at": self.created_at.isoformat(),
            "seen_at":    self.seen_at.isoformat() if self.seen_at else None,
        }

    @classmethod
    def from_record(cls, r: Dict[str, Any]) -> "Notification":
        return cls(
            id=r["id"],
            user_id=r.get("user_id", ""),
            message=r.get("message", ""),
            status=NotificationStatus(r.get("status", "UNREAD")),
            ref_type=r.get("ref_type", ""),
            ref_id=r.get("ref_id", ""),
            created_at=datetime.fromisoformat(r["created_at"]),
            seen_at=datetime.fromisoformat(r["seen_at"]) if r.get("seen_at") else None,
        )
