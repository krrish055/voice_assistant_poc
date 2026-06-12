"""SynthesizerAgent — main conversation agent.

Extends BaseAgent. Dialogue responsibility only: no report generation,
no persistence, no caching.
"""

from __future__ import annotations

from pydantic import BaseModel, Field
from uuid import UUID

from backend.domain.base_agent import BaseAgent, LLMResponse
from backend.domain.llm_factory import LLMFactory
from backend.registry.prompt_registry import PromptRegistry


class TurnContext(BaseModel):
    """Input context for a single conversation turn.

    Args:
        session_id: The owning session identifier.
        user_input: The user's utterance for this turn.
        prompt_key: PromptRegistry key to use for this turn.
        variables: Template variables (must include 'user_input' at minimum).
    """

    session_id: UUID
    user_input: str = Field(min_length=1)
    prompt_key: str = Field(min_length=1)
    variables: dict[str, str] = Field(default_factory=dict)

    model_config = {"frozen": True}


class RawTurnResult(BaseModel):
    """Raw output from a single synthesizer turn, before any post-processing.

    Args:
        session_id: The owning session identifier.
        agent_response: The LLM-generated reply text.
        provider_used: The provider identifier that produced the response.
        model_used: The model identifier used.
    """

    session_id: UUID
    agent_response: str
    provider_used: str
    model_used: str

    model_config = {"frozen": True}


class SynthesizerAgent(BaseAgent):
    """Conversational synthesizer agent.

    Loads the prompt template identified by TurnContext.prompt_key,
    renders it with the supplied variables (injecting user_input automatically),
    calls the LLM, and returns a RawTurnResult.

    Args:
        prompt_registry: Injected PromptRegistry.
        llm_factory: Injected LLMFactory.
    """

    def __init__(
        self,
        prompt_registry: PromptRegistry,
        llm_factory: LLMFactory,
    ) -> None:
        super().__init__(prompt_registry, llm_factory)

    async def turn(self, context: TurnContext) -> RawTurnResult:  # type: ignore[override]
        """Execute one conversation turn and return a RawTurnResult.

        Merges context.variables with user_input so templates can reference
        {user_input} without the caller duplicating it.

        Args:
            context: TurnContext carrying session_id, user_input, prompt_key,
                     and any additional template variables.

        Returns:
            RawTurnResult containing the agent's response and provider metadata.

        Raises:
            KeyError: If prompt_key is not found in PromptRegistry.
            LLMProcessingError: If all configured providers fail.
        """
        variables = {**context.variables, "user_input": context.user_input}
        rendered = self.render_prompt(context.prompt_key, variables)
        response: LLMResponse = await self.complete(rendered)
        return RawTurnResult(
            session_id=context.session_id,
            agent_response=response.content,
            provider_used=response.provider,
            model_used=response.model,
        )
