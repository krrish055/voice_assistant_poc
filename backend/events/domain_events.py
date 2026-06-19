"""
events/domain_events.py

Single responsibility: define all domain event types and the DomainEvent value object.
No logic — pure data contracts.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict
from uuid import uuid4


class EventType(str, Enum):
    APPROVAL_REQUESTED  = "APPROVAL_REQUESTED"
    APPROVAL_APPROVED   = "APPROVAL_APPROVED"
    APPROVAL_REJECTED   = "APPROVAL_REJECTED"
    JOB_STARTED         = "JOB_STARTED"
    JOB_COMPLETED       = "JOB_COMPLETED"
    JOB_FAILED          = "JOB_FAILED"
    NOTIFICATION_CREATED = "NOTIFICATION_CREATED"
    MESSAGE_QUEUED      = "MESSAGE_QUEUED"


@dataclass(frozen=True)
class DomainEvent:
    event_type: EventType
    payload:    Dict[str, Any]
    event_id:   str      = field(default_factory=lambda: str(uuid4()))
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
