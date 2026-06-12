"""Inference result models produced by RequirementInferenceEngine."""

from __future__ import annotations

from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from backend.models.requirement import RequirementDimension


class InferenceStatus(StrEnum):
    """Lifecycle state of an inferred requirement."""

    PENDING = "pending"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"


class InferenceResult(BaseModel):
    """A single inference produced by the InferenceEngine for a session."""

    id: UUID = Field(default_factory=uuid4)
    session_id: UUID
    rule_id: UUID
    rule_name: str
    dimension: RequirementDimension
    inferred_content: str = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)
    status: InferenceStatus = InferenceStatus.PENDING
    created_at: str = Field(description="ISO 8601 datetime string")
    resolved_at: str | None = None
    resolved_by_turn_id: UUID | None = None

    model_config = {"frozen": True}


class SessionInferences(BaseModel):
    """Aggregated inference results for a session, stored in InferenceCache."""

    session_id: UUID
    results: list[InferenceResult] = Field(default_factory=list)
    computed_at: str = Field(description="ISO 8601 datetime string")

    model_config = {"frozen": True}

    @property
    def confirmed(self) -> list[InferenceResult]:
        """Return only confirmed inferences."""
        return [r for r in self.results if r.status == InferenceStatus.CONFIRMED]

    @property
    def pending(self) -> list[InferenceResult]:
        """Return inferences awaiting user confirmation."""
        return [r for r in self.results if r.status == InferenceStatus.PENDING]

    def with_result(self, result: InferenceResult) -> "SessionInferences":
        """Return a new SessionInferences with the given result appended."""
        existing_ids = {r.id for r in self.results}
        if result.id in existing_ids:
            updated = [r if r.id != result.id else result for r in self.results]
        else:
            updated = [*self.results, result]
        return SessionInferences(
            session_id=self.session_id,
            results=updated,
            computed_at=self.computed_at,
        )
