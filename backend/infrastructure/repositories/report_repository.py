"""ReportRepository — Neo4j persistence for Report nodes.

Single responsibility: read and write Report and ReportSection nodes.
No business logic. No LLM calls. No synthesis logic.
"""

from __future__ import annotations

import json
from uuid import UUID

from neo4j import AsyncDriver, AsyncManagedTransaction

from backend.infrastructure.repositories.base_repository import BaseRepository
from backend.models.report import Report, ReportFormat, ReportSection, ReportStatus

# ── Cypher constants ──────────────────────────────────────────────────────────

_CREATE_REPORT = """
MATCH (s:Session {id: $session_id})
CREATE (r:Report {
    id:                          $id,
    session_id:                  $session_id,
    status:                      $status,
    format:                      $format,
    coverage_score_at_generation: $coverage_score_at_generation,
    sections:                    $sections,
    raw_content:                 $raw_content,
    generated_at:                $generated_at,
    generation_duration_ms:      $generation_duration_ms,
    provider_used:               $provider_used,
    error_message:               $error_message
})
CREATE (s)-[:GENERATED_REPORT]->(r)
"""

_UPDATE_REPORT = """
MATCH (r:Report {id: $id})
SET r.status                 = $status,
    r.sections               = $sections,
    r.raw_content            = $raw_content,
    r.generation_duration_ms = $generation_duration_ms,
    r.provider_used          = $provider_used,
    r.error_message          = $error_message
"""

_GET_REPORT_BY_ID = """
MATCH (r:Report {id: $id})
RETURN r
"""

_GET_REPORTS_BY_SESSION = """
MATCH (s:Session {id: $session_id})-[:GENERATED_REPORT]->(r:Report)
RETURN r
ORDER BY r.generated_at DESC
"""

_GET_LATEST_REPORT_BY_SESSION = """
MATCH (s:Session {id: $session_id})-[:GENERATED_REPORT]->(r:Report)
WHERE r.status = 'completed'
RETURN r
ORDER BY r.generated_at DESC
LIMIT 1
"""


class ReportRepository(BaseRepository):
    """Read and write Report nodes in Neo4j.

    A Report is created when ReportGenerator begins synthesis (status=generating)
    and updated when synthesis completes or fails. Sections are stored as a
    JSON-serialised list on the Report node.

    All methods are async. All queries run through execute_write or
    execute_read — no sync driver, no run_in_executor.
    """

    def __init__(self, driver: AsyncDriver, database: str = "neo4j") -> None:
        """Initialise ReportRepository.

        Args:
            driver: Injected async Neo4j driver.
            database: Target database name.
        """
        super().__init__(driver, database)

    # ── Writes ────────────────────────────────────────────────────────────────

    async def save_report(self, report: Report) -> None:
        """Persist a new Report node linked to its parent Session.

        Called by ReportGenerator when synthesis begins (status=generating)
        and again when synthesis completes via update_report.

        Args:
            report: Report to create in Neo4j.
        """
        await self._execute_write(self._save_report_tx, report=report)

    async def update_report(self, report: Report) -> None:
        """Update mutable fields on an existing Report node.

        Updates status, sections, raw_content, duration, provider, and
        error_message. id, session_id, and generated_at are never changed.

        Args:
            report: Report with updated field values.
        """
        await self._execute_write(self._update_report_tx, report=report)

    # ── Reads ─────────────────────────────────────────────────────────────────

    async def get_report(self, report_id: UUID) -> Report | None:
        """Return a Report by id, or None if not found.

        Args:
            report_id: Report UUID.

        Returns:
            Report model or None.
        """
        records = await self._execute_read(
            self._get_report_tx, report_id=str(report_id)
        )
        rows = list(records)  # type: ignore[arg-type]
        return self._row_to_report(rows[0]) if rows else None

    async def get_by_session(self, session_id: UUID) -> list[Report]:
        """Return all reports for a session ordered newest first.

        Args:
            session_id: Session UUID.

        Returns:
            List of Report models.
        """
        records = await self._execute_read(
            self._get_by_session_tx, session_id=str(session_id)
        )
        return [self._row_to_report(r) for r in records]  # type: ignore[union-attr]

    async def get_latest_completed(self, session_id: UUID) -> Report | None:
        """Return the most recent completed Report for a session.

        Args:
            session_id: Session UUID.

        Returns:
            Latest completed Report or None.
        """
        records = await self._execute_read(
            self._get_latest_completed_tx, session_id=str(session_id)
        )
        rows = list(records)  # type: ignore[arg-type]
        return self._row_to_report(rows[0]) if rows else None

    # ── Transaction functions ─────────────────────────────────────────────────

    @staticmethod
    async def _save_report_tx(
        tx: AsyncManagedTransaction, report: Report
    ) -> None:
        await BaseRepository._run(
            tx,
            _CREATE_REPORT,
            {
                "id": str(report.id),
                "session_id": str(report.session_id),
                "status": report.status.value,
                "format": report.format.value,
                "coverage_score_at_generation": report.coverage_score_at_generation,
                "sections": json.dumps(
                    [s.model_dump() for s in report.sections]
                ),
                "raw_content": report.raw_content,
                "generated_at": report.generated_at,
                "generation_duration_ms": report.generation_duration_ms,
                "provider_used": report.provider_used,
                "error_message": report.error_message,
            },
        )

    @staticmethod
    async def _update_report_tx(
        tx: AsyncManagedTransaction, report: Report
    ) -> None:
        await BaseRepository._run(
            tx,
            _UPDATE_REPORT,
            {
                "id": str(report.id),
                "status": report.status.value,
                "sections": json.dumps(
                    [s.model_dump() for s in report.sections]
                ),
                "raw_content": report.raw_content,
                "generation_duration_ms": report.generation_duration_ms,
                "provider_used": report.provider_used,
                "error_message": report.error_message,
            },
        )

    @staticmethod
    async def _get_report_tx(
        tx: AsyncManagedTransaction, report_id: str
    ) -> list[dict[str, object]]:
        return await BaseRepository._run(tx, _GET_REPORT_BY_ID, {"id": report_id})

    @staticmethod
    async def _get_by_session_tx(
        tx: AsyncManagedTransaction, session_id: str
    ) -> list[dict[str, object]]:
        return await BaseRepository._run(
            tx, _GET_REPORTS_BY_SESSION, {"session_id": session_id}
        )

    @staticmethod
    async def _get_latest_completed_tx(
        tx: AsyncManagedTransaction, session_id: str
    ) -> list[dict[str, object]]:
        return await BaseRepository._run(
            tx, _GET_LATEST_REPORT_BY_SESSION, {"session_id": session_id}
        )

    # ── Mapping helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _row_to_report(record: dict[str, object]) -> Report:
        """Map a Neo4j record to a Report model."""
        node: dict[str, object] = record.get("r", record)  # type: ignore[assignment]
        raw_sections = node.get("sections", "[]")
        sections_data: list[dict[str, object]] = (
            json.loads(raw_sections)
            if isinstance(raw_sections, str)
            else list(raw_sections)  # type: ignore[arg-type]
        )
        sections = [ReportSection(**s) for s in sections_data]
        return Report(
            id=UUID(str(node["id"])),
            session_id=UUID(str(node["session_id"])),
            status=ReportStatus(str(node["status"])),
            format=ReportFormat(str(node["format"])),
            coverage_score_at_generation=float(node["coverage_score_at_generation"]),  # type: ignore[arg-type]
            sections=sections,
            raw_content=str(node.get("raw_content", "")),
            generated_at=str(node["generated_at"]),
            generation_duration_ms=int(node.get("generation_duration_ms", 0)),  # type: ignore[arg-type]
            provider_used=str(node.get("provider_used", "")),
            error_message=(
                str(node["error_message"]) if node.get("error_message") else None
            ),
        )
