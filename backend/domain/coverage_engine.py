"""CoverageEngine — coverage calculation, gap detection, and snapshot generation.

Flow:
    CoverageCache (check hit)
        ↓ miss
    RequirementRepository (load requirements)
        ↓
    CoverageConfigRegistry (load dimension weights)
        ↓
    Compute CoverageSnapshot
        ↓
    CoverageCache (store result)

Subscribes to CoverageConfigRegistry: dimension weight changes invalidate
all cached snapshots so scores are recomputed on next request.

No Cypher. No direct Neo4j access.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from backend.infrastructure.domain_caches import CoverageCache
from backend.infrastructure.repositories.requirement_repository import RequirementRepository
from backend.models.config import CoverageDimensionConfig
from backend.models.coverage import CoverageGap, CoverageSnapshot, DimensionScore
from backend.models.requirement import Requirement, RequirementDimension
from backend.registry.coverage_config_registry import CoverageConfigRegistry


class CoverageEngine:
    """Computes coverage snapshots from elicited requirements.

    Args:
        coverage_registry: Injected CoverageConfigRegistry (dimension weights).
        requirement_repo: Injected RequirementRepository (read-only usage here).
        coverage_cache: Injected CoverageCache for read-through caching.
    """

    def __init__(
        self,
        coverage_registry: CoverageConfigRegistry,
        requirement_repo: RequirementRepository,
        coverage_cache: CoverageCache,
    ) -> None:
        self._registry = coverage_registry
        self._repo = requirement_repo
        self._cache = coverage_cache
        self._registry.subscribe(self._on_registry_change)

    # ── public interface ──────────────────────────────────────────────────────

    async def compute(self, session_id: UUID) -> CoverageSnapshot:
        """Return the current CoverageSnapshot for a session.

        Cache-first: returns a cached snapshot if present and fresh.
        On miss: loads requirements from Neo4j, computes scores, stores result.

        Args:
            session_id: Session UUID to compute coverage for.

        Returns:
            CoverageSnapshot with overall score, dimension scores, and gaps.
        """
        sid = str(session_id)
        cached = self._cache.get(sid)
        if cached is not None:
            return cached

        requirements = await self._repo.get_by_session(session_id)
        snapshot = self._compute_snapshot(session_id, requirements)
        await self._cache.set(sid, snapshot)
        return snapshot

    async def invalidate(self, session_id: UUID) -> None:
        """Evict cached snapshot for a session.

        Called after each new turn so coverage is recomputed on next request.

        Args:
            session_id: Session UUID to invalidate.
        """
        await self._cache.invalidate(str(session_id))

    # ── private computation ───────────────────────────────────────────────────

    def _compute_snapshot(
        self, session_id: UUID, requirements: list[Requirement]
    ) -> CoverageSnapshot:
        """Build a CoverageSnapshot from requirements and registry weights.

        Args:
            session_id: Owning session UUID.
            requirements: All Requirement nodes for this session.

        Returns:
            Fully computed CoverageSnapshot.
        """
        dim_configs = self._registry.get_all()
        covered: dict[str, set[str]] = {dim: set() for dim in dim_configs}

        for req in requirements:
            dim_key = req.dimension.value
            if dim_key in covered:
                covered[dim_key].add(req.sub_dimension)

        dimension_scores: list[DimensionScore] = []
        gaps: list[CoverageGap] = []

        for dim_key, config in dim_configs.items():
            covered_subs = covered.get(dim_key, set())
            all_subs = set(config.sub_dimensions)
            missing_subs = sorted(all_subs - covered_subs)

            score = (
                len(covered_subs & all_subs) / len(all_subs)
                if all_subs
                else 1.0
            )

            try:
                dimension = RequirementDimension(dim_key)
            except ValueError:
                continue

            dimension_scores.append(
                DimensionScore(
                    dimension=dimension,
                    score=score,
                    covered_sub_dimensions=sorted(covered_subs & all_subs),
                    missing_sub_dimensions=missing_subs,
                    weight=config.weight,
                )
            )

            for missing in missing_subs:
                gaps.append(
                    CoverageGap(
                        dimension=dimension,
                        missing_sub_dimension=missing,
                        priority_score=config.weight * (1.0 - score),
                    )
                )

        overall = self._weighted_overall(dimension_scores, dim_configs)

        return CoverageSnapshot(
            session_id=session_id,
            overall_score=overall,
            dimension_scores=dimension_scores,
            gaps=sorted(gaps, key=lambda g: g.priority_score, reverse=True),
            computed_at=datetime.now(timezone.utc).isoformat(),
        )

    @staticmethod
    def _weighted_overall(
        scores: list[DimensionScore],
        configs: dict[str, CoverageDimensionConfig],
    ) -> float:
        """Compute weighted overall score across all dimensions.

        Args:
            scores: Per-dimension DimensionScore list.
            configs: Registry dimension configs keyed by dimension name.

        Returns:
            Weighted average float in [0.0, 1.0].
        """
        total_weight = sum(c.weight for c in configs.values())
        if total_weight == 0.0:
            return 0.0
        weighted_sum = sum(ds.score * ds.weight for ds in scores)
        return min(weighted_sum / total_weight, 1.0)

    async def _on_registry_change(self, key: str, value: object) -> None:
        """CoverageConfigRegistry subscriber — awaits full cache invalidation.

        Declared async so _notify_subscribers awaits it directly, guaranteeing
        that invalidate_all() completes before registry.update() returns to
        its caller. This closes the stale-cache window entirely.

        Args:
            key: The dimension key that changed.
            value: New CoverageDimensionConfig, or None on deletion.
        """
        await self._cache.invalidate_all()
