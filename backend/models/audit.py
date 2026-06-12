"""Audit event models for structured audit trail persistence."""

from __future__ import annotations

from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class AuditEventType(StrEnum):
    """Categorised audit event types across the platform."""

    # Session lifecycle
    SESSION_CREATED = "session.created"
    SESSION_COMPLETED = "session.completed"
    SESSION_ABANDONED = "session.abandoned"
    SESSION_PAUSED = "session.paused"
    SESSION_RESUMED = "session.resumed"

    # Turn execution
    TURN_COMPLETED = "turn.completed"
    TURN_FALLBACK_USED = "turn.fallback_used"
    TURN_FAILED = "turn.failed"

    # HITL
    HITL_TRIGGERED = "hitl.triggered"
    HITL_RESOLVED = "hitl.resolved"

    # Config changes
    CONFIG_UPDATED = "config.updated"

    # Report
    REPORT_GENERATED = "report.generated"
    REPORT_FAILED = "report.failed"

    # Inference
    INFERENCE_CONFIRMED = "inference.confirmed"
    INFERENCE_REJECTED = "inference.rejected"

    # System
    AUDIT_QUEUE_OVERFLOW = "system.audit_queue_overflow"


class AuditSeverity(StrEnum):
    """Severity classification for audit events."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AuditEvent(BaseModel):
    """A single structured audit event written by AuditLogger.

    Immutable. Written to Neo4j and stdout. Never mutated after creation.
    """

    id: UUID = Field(default_factory=uuid4)
    event_type: AuditEventType
    severity: AuditSeverity = AuditSeverity.INFO
    actor: str = Field(min_length=1, description="user_id, system, or admin identifier")
    session_id: UUID | None = None
    turn_id: UUID | None = None
    timestamp: str = Field(description="ISO 8601 datetime string")
    payload: dict[str, str | int | float | bool | None] = Field(default_factory=dict)
    message: str = ""

    model_config = {"frozen": True}
