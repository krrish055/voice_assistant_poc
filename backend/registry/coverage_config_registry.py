"""CoverageConfigRegistry — manages coverage dimension weights and thresholds."""

from __future__ import annotations

from typing import Literal

from backend.infrastructure.repositories.config_repository import ConfigRepository
from backend.models.config import CoverageDimensionConfig
from backend.registry.base_registry import BaseRegistry


class CoverageConfigRegistry(BaseRegistry[str, CoverageDimensionConfig]):
    """Registry for coverage dimension weights, sub-dimensions, and priority.

    Key: dimension name string (matches RequirementDimension enum values).
    Value: CoverageDimensionConfig.

    Changes When: coverage scoring logic or dimension model changes.
    Does NOT own: prompt templates, agent config, or Neo4j node state.

    Admin changes here automatically invalidate CoverageCache via subscriber.
    """

    registry_name: Literal["coverage_config"] = "coverage_config"

    def __init__(self, config_repo: ConfigRepository, changed_by: str = "system") -> None:
        """Initialise CoverageConfigRegistry.

        Args:
            config_repo: Injected ConfigRepository.
            changed_by: Default actor for audit trail.
        """
        super().__init__(config_repo, changed_by)

    def _serialize(self, value: CoverageDimensionConfig) -> dict[str, object]:
        """Serialize CoverageDimensionConfig for ConfigSnapshot storage."""
        return value.model_dump()

    def get_dimension(self, dimension: str) -> CoverageDimensionConfig:
        """Return config for a named coverage dimension.

        Args:
            dimension: Dimension name (e.g. "functional", "security").

        Returns:
            CoverageDimensionConfig for the dimension.

        Raises:
            KeyError: If the dimension is not configured.
        """
        return self.get_or_raise(dimension)

    def get_required_dimensions(self) -> list[CoverageDimensionConfig]:
        """Return all dimensions marked as required for report generation."""
        return [d for d in self._store.values() if d.required_for_report]

    def total_weight(self) -> float:
        """Return sum of all dimension weights (should equal 1.0 when normalized)."""
        return sum(d.weight for d in self._store.values())
