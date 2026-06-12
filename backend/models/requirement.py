"""Requirement graph node models."""

from __future__ import annotations

from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class RequirementDimension(StrEnum):
    """Top-level requirement dimensions tracked by CoverageEngine."""

    FUNCTIONAL = "functional"
    NON_FUNCTIONAL = "non_functional"
    SECURITY = "security"
    INTEGRATIONS = "integrations"
    DEPLOYMENT = "deployment"
    STAKEHOLDERS = "stakeholders"
    CONSTRAINTS = "constraints"
    TIMELINE = "timeline"


class RequirementStatus(StrEnum):
    """Lifecycle of a single requirement node."""

    INFERRED = "inferred"
    CONFIRMED = "confirmed"
    CONTRADICTED = "contradicted"


class Requirement(BaseModel):
    """A single elicited or inferred requirement node in the graph."""

    id: UUID = Field(default_factory=uuid4)
    session_id: UUID
    dimension: RequirementDimension
    sub_dimension: str = Field(min_length=1)
    content: str = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)
    source_turn_id: UUID | None = None
    status: RequirementStatus = RequirementStatus.INFERRED
    created_at: str = Field(description="ISO 8601 datetime string")
    updated_at: str = Field(description="ISO 8601 datetime string")

    model_config = {"frozen": True}


class RequirementRelationshipType(StrEnum):
    """Types of relationships between requirement nodes."""

    DEPENDS_ON = "DEPENDS_ON"
    CONTRADICTS = "CONTRADICTS"
    REFINES = "REFINES"
    EXTRACTED_FROM = "EXTRACTED_FROM"


class RequirementRelationship(BaseModel):
    """A directed relationship between two requirement nodes."""

    source_id: UUID
    target_id: UUID
    relationship_type: RequirementRelationshipType

    model_config = {"frozen": True}
