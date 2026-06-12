"""Coverage computation models.

Coverage state is computed — not stored as Neo4j nodes.
Only CoverageReport is persisted (at report generation time).
"""

from __future__ import annotations

from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from backend.models.requirement import RequirementDimension


class DimensionScore(BaseModel):
    """Coverage score for a single requirement dimension."""

    dimension: RequirementDimension
    score: float = Field(ge=0.0, le=1.0)
    covered_sub_dimensions: list[str] = Field(default_factory=list)
    missing_sub_dimensions: list[str] = Field(default_factory=list)
    weight: float = Field(gt=0.0, le=1.0)

    model_config = {"frozen": True}


class CoverageGap(BaseModel):
    """A single identified coverage gap, ordered by priority."""

    dimension: RequirementDimension
    missing_sub_dimension: str
    priority_score: float = Field(
        ge=0.0,
        description="weight × (1 - dimension_score): higher = more urgent",
    )
    suggested_question: str = ""

    model_config = {"frozen": True}


class CoverageSnapshot(BaseModel):
    """Computed coverage state for a session at a point in time.

    Returned by CoverageEngine. Cached in CoverageCache.
    Persisted to Neo4j only at report generation as CoverageReport.
    """

    session_id: UUID
    overall_score: float = Field(ge=0.0, le=1.0)
    dimension_scores: list[DimensionScore]
    gaps: list[CoverageGap] = Field(default_factory=list)
    computed_at: str = Field(description="ISO 8601 datetime string")

    model_config = {"frozen": True}

    @property
    def top_gap(self) -> CoverageGap | None:
        """Return the highest-priority uncovered gap, if any."""
        if not self.gaps:
            return None
        return max(self.gaps, key=lambda g: g.priority_score)


class CoverageReport(BaseModel):
    """Point-in-time coverage report persisted to Neo4j at report generation.

    Written once. Never updated.
    """

    id: UUID = Field(default_factory=uuid4)
    session_id: UUID
    generated_at: str = Field(description="ISO 8601 datetime string")
    overall_score: float = Field(ge=0.0, le=1.0)
    dimension_scores: dict[str, float] = Field(
        description="Dimension name → score mapping for compact Neo4j storage"
    )
    gap_dimensions: list[str]

    model_config = {"frozen": True}

    @classmethod
    def from_snapshot(cls, snapshot: CoverageSnapshot, generated_at: str) -> "CoverageReport":
        """Construct a CoverageReport from a computed CoverageSnapshot."""
        return cls(
            session_id=snapshot.session_id,
            generated_at=generated_at,
            overall_score=snapshot.overall_score,
            dimension_scores={
                ds.dimension.value: ds.score for ds in snapshot.dimension_scores
            },
            gap_dimensions=[g.dimension.value for g in snapshot.gaps],
        )
