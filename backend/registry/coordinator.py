"""RegistryCoordinator — facade providing unified access to all registries.

Single responsibility: route AdminRouter requests to the correct registry.

Design rules:
- Domain components (agents, engines, factories) NEVER import RegistryCoordinator.
- Domain components receive their specific registry via constructor injection.
- Only AdminRouter imports RegistryCoordinator.
- RegistryCoordinator owns no state. It holds references to registry instances.
"""

from __future__ import annotations

from backend.registry.agent_registry import AgentRegistry
from backend.registry.coverage_config_registry import CoverageConfigRegistry
from backend.registry.hitl_rule_registry import HITLRuleRegistry
from backend.registry.inference_rule_registry import InferenceRuleRegistry
from backend.registry.llm_provider_registry import LLMProviderRegistry
from backend.registry.prompt_registry import PromptRegistry
from backend.registry.routing_registry import RoutingRegistry


class RegistryCoordinator:
    """Facade providing a single entry point to all registry instances.

    Injected into AdminRouter only. Never imported by domain layer.

    All registry instances are constructed externally (in application lifespan)
    and injected here — RegistryCoordinator does not construct registries.

    Args:
        prompts: PromptRegistry instance.
        coverage: CoverageConfigRegistry instance.
        inference_rules: InferenceRuleRegistry instance.
        agents: AgentRegistry instance.
        llm_providers: LLMProviderRegistry instance.
        hitl_rules: HITLRuleRegistry instance.
        routing: RoutingRegistry instance.
    """

    def __init__(
        self,
        prompts: PromptRegistry,
        coverage: CoverageConfigRegistry,
        inference_rules: InferenceRuleRegistry,
        agents: AgentRegistry,
        llm_providers: LLMProviderRegistry,
        hitl_rules: HITLRuleRegistry,
        routing: RoutingRegistry,
    ) -> None:
        self.prompts = prompts
        self.coverage = coverage
        self.inference_rules = inference_rules
        self.agents = agents
        self.llm_providers = llm_providers
        self.hitl_rules = hitl_rules
        self.routing = routing

    def __repr__(self) -> str:
        """Return a developer-readable representation."""
        registries = [
            "prompts",
            "coverage",
            "inference_rules",
            "agents",
            "llm_providers",
            "hitl_rules",
            "routing",
        ]
        loaded_counts = {
            "prompts": len(self.prompts.get_all()),
            "coverage": len(self.coverage.get_all()),
            "inference_rules": len(self.inference_rules.get_all()),
            "agents": len(self.agents.get_all()),
            "llm_providers": len(self.llm_providers.get_all()),
            "hitl_rules": len(self.hitl_rules.get_all()),
            "routing": len(self.routing.get_all()),
        }
        summary = ", ".join(f"{k}={v}" for k, v in loaded_counts.items())
        return f"RegistryCoordinator({summary})"
