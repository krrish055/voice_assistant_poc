"""Report models for generated enterprise specification reports."""

from __future__ import annotations

from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class ReportFormat(StrEnum):
    """Supported output formats for generated reports."""

    MARKDOWN = "markdown"
    JSON = "json"
    PDF_READY = "pdf_ready"


class ReportStatus(StrEnum):
    """Generation status of a report."""

    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"


class ReportSection(BaseModel):
    """A single named section within a generated report."""

    title: str = Field(min_length=1)
    content: str = Field(min_length=1)
    dimension: str | None = None
    order: int = Field(ge=0)

    model_config = {"frozen": True}


class Report(BaseModel):
    """A generated enterprise-grade project specification report."""

    id: UUID = Field(default_factory=uuid4)
    session_id: UUID
    status: ReportStatus = ReportStatus.GENERATING
    format: ReportFormat = ReportFormat.MARKDOWN
    coverage_score_at_generation: float = Field(ge=0.0, le=1.0)
    sections: list[ReportSection] = Field(default_factory=list)
    raw_content: str = ""
    generated_at: str = Field(description="ISO 8601 datetime string")
    generation_duration_ms: int = Field(default=0, ge=0)
    provider_used: str = ""
    error_message: str | None = None

    model_config = {"frozen": True}

    @property
    def is_complete(self) -> bool:
        """Return True if the report was successfully generated."""
        return self.status == ReportStatus.COMPLETED

    def as_completed(
        self,
        sections: list[ReportSection],
        raw_content: str,
        provider_used: str,
        duration_ms: int,
    ) -> "Report":
        """Return a completed copy of this report."""
        return self.model_copy(
            update={
                "status": ReportStatus.COMPLETED,
                "sections": sections,
                "raw_content": raw_content,
                "provider_used": provider_used,
                "generation_duration_ms": duration_ms,
            }
        )

    def as_failed(self, error_message: str) -> "Report":
        """Return a failed copy of this report."""
        return self.model_copy(
            update={
                "status": ReportStatus.FAILED,
                "error_message": error_message,
            }
        )
