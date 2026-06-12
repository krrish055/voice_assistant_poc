"""CoverageRepository — Neo4j persistence for CoverageReport nodes.

Single responsibility: write and read CoverageReport nodes.

Design note (v2.3):
  CoverageNode and CoverageDimension were removed from the graph schema.
  Coverage state is computed on demand by CoverageEngine (graph-driven,
  derived from Requirement nodes + CoverageConfigRegistry weights).
  CoverageReport is persisted exactly once per session at report generation
  as a point-in-time audit record. It is never updated after creation.
"""

from __future__ import annotations

from uuid import UUID

from neo4j import AsyncDriver, AsyncManagedTransaction

from backend.infrastructure.repositories.base_repository import BaseRepository
from backend.models.coverage import CoverageReport

# ── Cypher constants ──────────────────────────────────────────────────────────

_CREATE_COVERAGE_REPORT = """
MATCH (s:Session {id: $session_id})
CREATE (cr:CoverageReport {
    id:               $id,
    session_id:       $session_id,
    generated_at:     $generated_at,
    overall_score:    $overall_score,
    dimension_scores: $dimension_scores,
    gap_dimensions:   $gap_dimensions
})
CREATE (s)-[:HAS_COVERAGE_REPORT]->(cr)
"""

_GET_COVERAGE_REPORT_BY_SESSION = """
MATCH (s:Session {id: $session_id})-[:HAS_COVERAGE_REPORT]->(cr:CoverageReport)
RETURN cr
ORDER BY cr.generated_at DESC
LIMIT 1
"""

_GET_ALL_COVERAGE_REPORTS_BY_SESSION = """
MATCH (s:Session {id: $session_id})-[:HAS_COVERAGE_REPORT]->(cr:CoverageReport)
RETURN cr
ORDER BY cr.generated_at DESC
"""

_GET_COVERAGE_REPORT_BY_ID = """
MATCH (cr:CoverageReport {id: $id})
RETURN cr
"""


class CoverageRepository(BaseRepository):
    """Write and read CoverageReport nodes in Neo4j.

    CoverageReport is written once per session at the point of report
    generation. It is an audit record — never updated after creation.

    All methods are async. All queries run through execute_write or
    execute_read — no sync driver, no run_in_executor.
    """

    def __init__(self, driver: AsyncDriver, database: str = "neo4j") -> None:
        """Initialise CoverageRepository.

        Args:
            driver: Injected async Neo4j driver.
            database: Target database name.
        """
        super().__init__(driver, database)

    # ── Writes ────────────────────────────────────────────────────────────────

    async def save_coverage_report(self, report: CoverageReport) -> None:
        """Persist a CoverageReport node linked to its parent Session.

        Called once at report generation time. The report is immutable
        after this write.

        Args:
            report: CoverageReport to persist.
        """
        await self._execute_write(self._save_coverage_report_tx, report=report)

    # ── Reads ─────────────────────────────────────────────────────────────────

    async def get_latest_report(self, session_id: UUID) -> CoverageReport | None:
        """Return the most recent CoverageReport for a session.

        Args:
            session_id: Session UUID.

        Returns:
            CoverageReport or None if no report has been generated.
        """
        records = await self._execute_read(
            self._get_latest_report_tx, session_id=str(session_id)
        )
        rows = list(records)  # type: ignore[arg-type]
        return self._row_to_report(rows[0]) if rows else None

    async def get_all_reports(self, session_id: UUID) -> list[CoverageReport]:
        """Return all CoverageReports for a session, newest first.

        Args:
            session_id: Session UUID.

        Returns:
            List of CoverageReport models ordered newest-first.
        """
        records = await self._execute_read(
            self._get_all_reports_tx, session_id=str(session_id)
        )
        return [self._row_to_report(r) for r in records]  # type: ignore[union-attr]

    async def get_report_by_id(self, report_id: UUID) -> CoverageReport | None:
        """Return a CoverageReport by its id.

        Args:
            report_id: CoverageReport UUID.

        Returns:
            CoverageReport or None.
        """
        records = await self._execute_read(
            self._get_report_by_id_tx, report_id=str(report_id)
        )
        rows = list(records)  # type: ignore[arg-type]
        return self._row_to_report(rows[0]) if rows else None

    # ── Transaction functions ─────────────────────────────────────────────────

    @staticmethod
    async def _save_coverage_report_tx(
        tx: AsyncManagedTransaction, report: CoverageReport
    ) -> None:
        await BaseRepository._run(
            tx,
            _CREATE_COVERAGE_REPORT,
            {
                "id": str(report.id),
                "session_id": str(report.session_id),
                "generated_at": report.generated_at,
                "overall_score": report.overall_score,
                "dimension_scores": dict(report.dimension_scores),
                "gap_dimensions": list(report.gap_dimensions),
            },
        )

    @staticmethod
    async def _get_latest_report_tx(
        tx: AsyncManagedTransaction, session_id: str
    ) -> list[dict[str, object]]:
        return await BaseRepository._run(
            tx, _GET_COVERAGE_REPORT_BY_SESSION, {"session_id": session_id}
        )

    @staticmethod
    async def _get_all_reports_tx(
        tx: AsyncManagedTransaction, session_id: str
    ) -> list[dict[str, object]]:
        return await BaseRepository._run(
            tx, _GET_ALL_COVERAGE_REPORTS_BY_SESSION, {"session_id": session_id}
        )

    @staticmethod
    async def _get_report_by_id_tx(
        tx: AsyncManagedTransaction, report_id: str
    ) -> list[dict[str, object]]:
        return await BaseRepository._run(
            tx, _GET_COVERAGE_REPORT_BY_ID, {"id": report_id}
        )

    # ── Mapping helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _row_to_report(record: dict[str, object]) -> CoverageReport:
        """Map a Neo4j record to a CoverageReport model."""
        node: dict[str, object] = record.get("cr", record)  # type: ignore[assignment]
        raw_scores = node["dimension_scores"]
        scores: dict[str, float] = (
            dict(raw_scores)  # type: ignore[arg-type]
            if isinstance(raw_scores, dict)
            else {}
        )
        raw_gaps = node["gap_dimensions"]
        gaps: list[str] = list(raw_gaps) if raw_gaps else []  # type: ignore[arg-type]
        return CoverageReport(
            id=UUID(str(node["id"])),
            session_id=UUID(str(node["session_id"])),
            generated_at=str(node["generated_at"]),
            overall_score=float(node["overall_score"]),  # type: ignore[arg-type]
            dimension_scores=scores,
            gap_dimensions=gaps,
        )
