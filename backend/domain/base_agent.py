"""BaseAgent — reusable agent foundation for prompt rendering and LLM completion.

All concrete agents extend this class. Contains no conversation-specific,
persistence, or caching logic.
"""

from __future__ import annotations

from pydantic import BaseModel

from backend.domain.llm_factory import LLMFactory
from backend.exceptions import ConfigurationError, LLMProcessingError
from backend.models.config import LLMProviderConfig, PromptTemplate
from backend.registry.prompt_registry import PromptRegistry


class RenderedPrompt(BaseModel):
    """The result of rendering a prompt template against a variable map."""

    key: str
    text: str

    model_config = {"frozen": True}


class LLMResponse(BaseModel):
    """Raw response envelope returned by a provider call."""

    content: str
    provider: str
    model: str

    model_config = {"frozen": True}


class BaseAgent:
    """Reusable agent foundation: load template → render → call LLM → return response.

    Args:
        prompt_registry: Injected PromptRegistry for template lookup.
        llm_factory: Injected LLMFactory for provider resolution.
    """

    def __init__(
        self,
        prompt_registry: PromptRegistry,
        llm_factory: LLMFactory,
    ) -> None:
        self._prompt_registry = prompt_registry
        self._llm_factory = llm_factory

    # ── public interface ──────────────────────────────────────────────────────

    def render_prompt(self, prompt_key: str, variables: dict[str, str]) -> RenderedPrompt:
        """Load a template from PromptRegistry and render it with variables.

        Args:
            prompt_key: Key to look up in PromptRegistry.
            variables: Variable substitutions for the template.

        Returns:
            RenderedPrompt with the interpolated text.

        Raises:
            KeyError: If prompt_key is not registered.
            ConfigurationError: If a declared variable is missing from variables.
        """
        template: PromptTemplate = self._prompt_registry.get_template(prompt_key)
        missing = [v for v in template.variables if v not in variables]
        if missing:
            raise ConfigurationError(
                f"Prompt '{prompt_key}' missing variables: {missing}"
            )
        text = template.template.format(**variables)
        return RenderedPrompt(key=prompt_key, text=text)

    async def complete(self, prompt: RenderedPrompt) -> LLMResponse:
        """Send a rendered prompt to the primary LLM provider.

        Falls back to the fallback provider if the primary raises.

        Args:
            prompt: A RenderedPrompt produced by render_prompt().

        Returns:
            LLMResponse with the provider's reply.

        Raises:
            LLMProcessingError: If both primary and fallback fail.
        """
        primary = self._llm_factory.get_primary_client()
        try:
            return await self._call_provider(primary, prompt.text)
        except Exception as primary_err:
            fallback = self._llm_factory.get_fallback_client()
            if fallback is None:
                raise LLMProcessingError(
                    f"Primary provider failed and no fallback configured: {primary_err}"
                ) from primary_err
            try:
                return await self._call_provider(fallback, prompt.text)
            except Exception as fallback_err:
                raise LLMProcessingError(
                    f"Both primary and fallback providers failed. "
                    f"Primary: {primary_err}. Fallback: {fallback_err}"
                ) from fallback_err

    async def turn(self, prompt_key: str, variables: dict[str, str]) -> LLMResponse:
        """Convenience: render prompt then call LLM in one step.

        Args:
            prompt_key: Key to look up in PromptRegistry.
            variables: Variable substitutions for the template.

        Returns:
            LLMResponse from the active provider.
        """
        rendered = self.render_prompt(prompt_key, variables)
        return await self.complete(rendered)

    # ── private helpers ───────────────────────────────────────────────────────

    async def _call_provider(
        self, config: LLMProviderConfig, prompt_text: str
    ) -> LLMResponse:
        """Dispatch a completion request to the given provider config.

        This is the single seam replaced in tests. In production this will
        delegate to a provider-specific HTTP client.

        Args:
            config: The resolved LLMProviderConfig.
            prompt_text: The fully rendered prompt string.

        Returns:
            LLMResponse with content and provider metadata.
        """
        raise NotImplementedError(
            "_call_provider must be implemented by a concrete subclass or test double."
        )
