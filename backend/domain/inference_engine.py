"""InferenceEngine — applies active inference rules to session requirements.

Flow:
    InferenceCache (check hit)
        ↓ miss
    RequirementRepository (load confirmed requirements)
        ↓
    InferenceRuleRegistry (load enabled rules)
        ↓
    Apply rules → produce InferenceResult list
        ↓
    InferenceCache (store SessionInferences)

Subscribes to InferenceRuleRegistry: rule changes invalidate all cached
inferences so they are recomputed against the updated ruleset.

No Cypher. No direct Neo4j access.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from backend.infrastructure.domain_caches import InferenceCache
from backend.infrastructure.repositories.requirement_repository import RequirementRepository
from backend.models.config import InferenceRule
from backend.models.inference import InferenceResult, InferenceStatus, SessionInferences
from backend.models.requirement import Requirement, RequirementDimension, RequirementStatus
from backend.registry.inference_rule_registry import InferenceRuleRegistry


class InferenceEngine:
    """Applies active inference rules to a session's confirmed requirements.

    Args:
        inference_registry: Injected InferenceRuleRegistry (rule definitions).
        requirement_repo: Injected RequirementRepository (read-only here).
        inference_cache: Injected InferenceCache for read-through caching.
    """

    def __init__(
        self,
        inference_registry: InferenceRuleRegistry,
        requirement_repo: RequirementRepository,
        inference_cache: InferenceCache,
    ) -> None:
        self._registry = inference_registry
        self._repo = requirement_repo
        self._cache = inference_cache
        self._registry.subscribe(self._on_registry_change)

    # ── public interface ──────────────────────────────────────────────────────

    async def run(self, session_id: UUID) -> SessionInferences:
        """Return inferences for a session, computing if not cached.

        Cache-first: returns cached SessionInferences if present and fresh.
        On miss: loads confirmed requirements, applies all enabled rules,
        stores and returns SessionInferences.

        Args:
            session_id: Session UUID to run inference for.

        Returns:
            SessionInferences containing all inferred results for the session.
        """
        sid = str(session_id)
        cached = self._cache.get(sid)
        if cached is not None:
            return cached

        requirements = await self._repo.get_by_status(session_id, RequirementStatus.CONFIRMED)
        rules = self._registry.get_enabled_rules()
        inferences = self._apply_rules(session_id, requirements, rules)

        session_inferences = SessionInferences(
            session_id=session_id,
            results=inferences,
            computed_at=datetime.now(timezone.utc).isoformat(),
        )
        await self._cache.set(sid, session_inferences)
        return session_inferences

    async def invalidate(self, session_id: UUID) -> None:
        """Evict cached inferences for a session.

        Called after each turn so the next run() recomputes against
        the latest confirmed requirements.

        Args:
            session_id: Session UUID to invalidate.
        """
        await self._cache.invalidate(str(session_id))

    # ── private computation ───────────────────────────────────────────────────

    def _apply_rules(
        self,
        session_id: UUID,
        requirements: list[Requirement],
        rules: list[InferenceRule],
    ) -> list[InferenceResult]:
        """Apply each enabled inference rule against the confirmed requirements.

        A rule fires when its condition_domain appears in the content of any
        confirmed requirement. For each inferred_requirement string in the rule,
        one InferenceResult is produced (auto-confirmed when confidence exceeds
        rule.auto_confirm_above, otherwise PENDING).

        Args:
            session_id: Session UUID for the produced InferenceResult objects.
            requirements: Confirmed requirements to match rules against.
            rules: Enabled InferenceRule list from InferenceRuleRegistry.

        Returns:
            List of InferenceResult objects produced by matching rules.
        """
        now = datetime.now(timezone.utc).isoformat()
        results: list[InferenceResult] = []

        for rule in rules:
            if not self._rule_matches(rule, requirements):
                continue

            status = (
                InferenceStatus.CONFIRMED
                if rule.confidence >= rule.auto_confirm_above
                else InferenceStatus.PENDING
            )

            try:
                dimension = RequirementDimension(rule.missing_dimension)
            except ValueError:
                continue

            for inferred_content in rule.inferred_requirements:
                results.append(
                    InferenceResult(
                        session_id=session_id,
                        rule_id=rule.id,
                        rule_name=rule.name,
                        dimension=dimension,
                        inferred_content=inferred_content,
                        confidence=rule.confidence,
                        status=status,
                        created_at=now,
                    )
                )

        return results

    @staticmethod
    def _rule_matches(rule: InferenceRule, requirements: list[Requirement]) -> bool:
        """Return True if the rule's condition_domain appears in any requirement.

        Args:
            rule: InferenceRule whose condition_domain is used as search term.
            requirements: Confirmed requirements to search.

        Returns:
            True if at least one requirement content contains the domain keyword.
        """
        domain_lower = rule.condition_domain.lower()
        return any(domain_lower in req.content.lower() for req in requirements)

    async def _on_registry_change(self, key: str, value: object) -> None:
        """InferenceRuleRegistry subscriber — awaits full cache invalidation.

        Declared async so _notify_subscribers awaits it directly, guaranteeing
        that invalidate_all() completes before registry.update() returns to
        its caller. This closes the stale-cache window entirely.

        Args:
            key: The rule key that changed.
            value: New InferenceRule, or None on deletion.
        """
        await self._cache.invalidate_all()
