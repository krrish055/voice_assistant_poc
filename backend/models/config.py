"""Configuration models for LLM providers, agents, HITL rules, and routing."""

from __future__ import annotations

from enum import StrEnum
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, HttpUrl, SecretStr, field_validator


class LLMProvider(StrEnum):
    """Supported LLM provider identifiers."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GEMINI = "gemini"
    OLLAMA = "ollama"


class SessionUpdatePolicy(StrEnum):
    """Policy controlling how active sessions react to mid-session config changes."""

    IMMEDIATE = "immediate"
    SESSION_BOUNDARY = "session_boundary"
    GRACEFUL = "graceful"


class LLMProviderConfig(BaseModel):
    """Configuration for a single LLM provider slot.

    Immutable after construction — use registry.update() to hot-swap.
    """

    provider: LLMProvider
    model: str = Field(min_length=1)
    api_key: SecretStr
    base_url: HttpUrl | None = None
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=2048, gt=0)
    timeout_seconds: int = Field(default=30, gt=0)
    is_fallback: bool = False

    model_config = {"frozen": True}


class AgentConfiguration(BaseModel):
    """Runtime configuration for a single agent type.

    Loaded from registry — no hardcoded agent classes.
    """

    agent_type: str = Field(min_length=1)
    display_name: str = Field(min_length=1)
    provider_key: str = Field(min_length=1, description="Key into LLMProviderRegistry")
    prompt_key: str = Field(min_length=1, description="Key into PromptRegistry")
    enabled: bool = True
    max_turns: int = Field(default=50, gt=0)
    coverage_threshold: float = Field(
        default=0.85,
        ge=0.0,
        le=1.0,
        description="Coverage score required to trigger report generation",
    )
    session_update_policy: SessionUpdatePolicy = SessionUpdatePolicy.GRACEFUL
    metadata: dict[str, str] = Field(default_factory=dict)

    model_config = {"frozen": True}


class HITLConditionType(StrEnum):
    """Supported HITL trigger condition types."""

    COVERAGE_BELOW = "coverage_below"
    CONFIDENCE_BELOW = "confidence_below"
    TOPIC_FLAGGED = "topic_flagged"
    MANUAL_ESCALATION = "manual_escalation"
    TURN_LIMIT_REACHED = "turn_limit_reached"


class HITLRule(BaseModel):
    """A single Human-in-the-Loop rule evaluated after every turn."""

    id: UUID = Field(default_factory=uuid4)
    name: str = Field(min_length=1)
    condition_type: HITLConditionType
    threshold: float | None = Field(default=None, ge=0.0, le=1.0)
    flagged_topics: list[str] = Field(default_factory=list)
    enabled: bool = True
    priority: int = Field(default=0, ge=0, description="Higher = evaluated first")

    @field_validator("threshold")
    @classmethod
    def threshold_required_for_numeric_conditions(
        cls, v: float | None, info: object
    ) -> float | None:
        """Ensure threshold is set for conditions that require a numeric value."""
        numeric_conditions = {
            HITLConditionType.COVERAGE_BELOW,
            HITLConditionType.CONFIDENCE_BELOW,
        }
        data = getattr(info, "data", {})
        if data.get("condition_type") in numeric_conditions and v is None:
            raise ValueError(
                f"threshold required for condition_type={data.get('condition_type')}"
            )
        return v

    model_config = {"frozen": True}


class IntentRoute(BaseModel):
    """Maps an intent pattern to an agent type."""

    intent: str = Field(min_length=1)
    agent_type: str = Field(min_length=1)
    keywords: list[str] = Field(default_factory=list)
    priority: int = Field(default=0, ge=0)
    enabled: bool = True

    model_config = {"frozen": True}


class PromptTemplate(BaseModel):
    """A versioned prompt template with variable schema."""

    key: str = Field(min_length=1)
    template: str = Field(min_length=1)
    variables: list[str] = Field(
        default_factory=list,
        description="Expected variable names for template rendering",
    )
    version: int = Field(default=1, gt=0)
    description: str = ""

    model_config = {"frozen": True}


class ConfigSnapshot(BaseModel):
    """Point-in-time snapshot of registry state written to Neo4j on every update."""

    id: UUID = Field(default_factory=uuid4)
    registry_name: str = Field(min_length=1)
    config_key: str = Field(min_length=1)
    previous_value: dict[str, object] | None = None
    new_value: dict[str, object]
    changed_by: str = Field(min_length=1)
    changed_at: str = Field(description="ISO 8601 datetime string")
    supersedes_id: UUID | None = None

    model_config = {"frozen": True}


class CoverageDimensionConfig(BaseModel):
    """Weight and priority configuration for a single coverage dimension.

    Lives in CoverageConfigRegistry — not in Neo4j graph nodes.
    """

    dimension: str = Field(min_length=1)
    weight: float = Field(gt=0.0, le=1.0)
    sub_dimensions: list[str] = Field(min_length=1)
    priority_order: int = Field(ge=0)
    required_for_report: bool = True

    model_config = {"frozen": True}


class InferenceRule(BaseModel):
    """A domain inference rule applied by RequirementInferenceEngine."""

    id: UUID = Field(default_factory=uuid4)
    name: str = Field(min_length=1)
    condition_domain: str = Field(
        min_length=1, description="Domain keyword triggering this rule, e.g. 'AI application'"
    )
    missing_dimension: str = Field(min_length=1)
    inferred_requirements: list[str] = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)
    auto_confirm_above: float = Field(
        default=0.9,
        ge=0.0,
        le=1.0,
        description="Confidence above which inference is auto-confirmed without user prompt",
    )
    enabled: bool = True

    model_config = {"frozen": True}


# Valid registry names — used for ConfigSnapshot validation
REGISTRY_NAMES: frozenset[str] = frozenset(
    {
        "prompt",
        "coverage_config",
        "inference_rule",
        "agent",
        "llm_provider",
        "hitl_rule",
        "routing",
    }
)

RegistryName = Literal[
    "prompt",
    "coverage_config",
    "inference_rule",
    "agent",
    "llm_provider",
    "hitl_rule",
    "routing",
]
