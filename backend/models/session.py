"""Session and conversation turn models."""

from __future__ import annotations

from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class SessionStatus(StrEnum):
    """Lifecycle states for a requirement elicitation session."""

    ACTIVE = "active"
    PAUSED = "paused"
    HITL_PENDING = "hitl_pending"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class InputModality(StrEnum):
    """Channel through which user input was received."""

    TEXT = "text"
    VOICE = "voice"


class TurnStatus(StrEnum):
    """Execution status of a single conversation turn."""

    COMPLETED = "completed"
    FALLBACK_USED = "fallback_used"
    HITL_TRIGGERED = "hitl_triggered"
    FAILED = "failed"


class Turn(BaseModel):
    """A single user↔agent exchange within a session."""

    id: UUID = Field(default_factory=uuid4)
    session_id: UUID
    sequence: int = Field(ge=1)
    user_input: str = Field(min_length=1)
    agent_response: str
    intent_classified: str
    provider_used: str
    modality: InputModality = InputModality.TEXT
    status: TurnStatus = TurnStatus.COMPLETED
    coverage_delta: float = Field(
        default=0.0,
        description="Change in overall coverage score after this turn",
    )
    latency_ms: int = Field(default=0, ge=0)
    hitl_triggered: bool = False
    created_at: str = Field(description="ISO 8601 datetime string")

    model_config = {"frozen": True}


class LLMConfigSnapshot(BaseModel):
    """Frozen copy of the LLM provider config active at session start.

    Stored on the session to ensure consistent replay and audit.
    """

    provider: str
    model: str
    temperature: float
    max_tokens: int
    base_url: str | None = None

    model_config = {"frozen": True}


class Session(BaseModel):
    """A complete requirement elicitation session."""

    id: UUID = Field(default_factory=uuid4)
    user_id: str = Field(min_length=1)
    agent_type: str = Field(min_length=1)
    status: SessionStatus = SessionStatus.ACTIVE
    llm_config_snapshot: LLMConfigSnapshot
    session_update_policy: str
    coverage_score: float = Field(default=0.0, ge=0.0, le=1.0)
    turn_count: int = Field(default=0, ge=0)
    created_at: str = Field(description="ISO 8601 datetime string")
    updated_at: str = Field(description="ISO 8601 datetime string")
    completed_at: str | None = None
    metadata: dict[str, str] = Field(default_factory=dict)

    model_config = {"frozen": True}


class SessionState(BaseModel):
    """Mutable in-memory session state held by SessionCache.

    Hydrated from Neo4j on cache miss, flushed to Neo4j on eviction.
    This is the only mutable representation of a session.
    """

    session: Session
    recent_turn_ids: list[UUID] = Field(default_factory=list)
    is_dirty: bool = Field(
        default=False,
        description="True when in-memory state has unflushed changes",
    )

    model_config = {"frozen": False}

    def with_turn(self, turn_id: UUID, new_coverage: float) -> "SessionState":
        """Return a new SessionState reflecting a completed turn."""
        updated_session = self.session.model_copy(
            update={
                "turn_count": self.session.turn_count + 1,
                "coverage_score": new_coverage,
            }
        )
        return SessionState(
            session=updated_session,
            recent_turn_ids=[*self.recent_turn_ids[-9:], turn_id],
            is_dirty=True,
        )

    def with_status(self, status: SessionStatus) -> "SessionState":
        """Return a new SessionState with updated status."""
        return SessionState(
            session=self.session.model_copy(update={"status": status}),
            recent_turn_ids=self.recent_turn_ids,
            is_dirty=True,
        )
