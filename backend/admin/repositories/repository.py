from abc import ABC, abstractmethod
from typing import Dict, List, Optional

from admin.domain.models import ChatMessage, PromptTemplate
from admin.constants import MAX_CONVERSATION_HISTORY
from agents.base_agent import BaseAgent


class IAgentRepository(ABC):
    @abstractmethod
    def get_all(self) -> Dict[str, BaseAgent]: ...
    @abstractmethod
    def get_by_id(self, agent_id: str) -> Optional[BaseAgent]: ...
    @abstractmethod
    def update(self, agent: BaseAgent) -> None: ...


class IChatRepository(ABC):
    @abstractmethod
    def get_by_agent(self, agent_id: str, limit: int) -> List[ChatMessage]: ...
    @abstractmethod
    def add_message(self, message: ChatMessage) -> None: ...
    @abstractmethod
    def clear_history(self, agent_id: str) -> None: ...


class IPromptRepository(ABC):
    @abstractmethod
    def get_by_agent(self, agent_id: str) -> Optional[PromptTemplate]: ...
    @abstractmethod
    def save(self, template: PromptTemplate) -> None: ...


class AgentRepositoryImpl(IAgentRepository):
    """Delegates to the global registry. Lazy import breaks the init-time cycle."""

    def _registry(self):
        from registry.agent_registry import registry  # lazy — avoids cyclic import at module load
        return registry

    def get_all(self) -> Dict[str, BaseAgent]:
        return {a["id"]: self._registry().get(a["id"]) for a in self._registry().list_all()}

    def get_by_id(self, agent_id: str) -> Optional[BaseAgent]:
        return self._registry().get(agent_id)

    def update(self, agent: BaseAgent) -> None:
        self._registry().register(agent)


class ChatRepositoryImpl(IChatRepository):
    def __init__(self):
        self._chats: Dict[str, List[ChatMessage]] = {}

    def get_by_agent(self, agent_id: str, limit: int = MAX_CONVERSATION_HISTORY) -> List[ChatMessage]:
        return self._chats.get(agent_id, [])[-limit:]

    def add_message(self, message: ChatMessage) -> None:
        self._chats.setdefault(message.agent_id, []).append(message)
        self._chats[message.agent_id] = self._chats[message.agent_id][-MAX_CONVERSATION_HISTORY:]

    def clear_history(self, agent_id: str) -> None:
        self._chats[agent_id] = []


class PromptRepositoryImpl(IPromptRepository):
    def __init__(self):
        self._prompts: Dict[str, PromptTemplate] = {}

    def get_by_agent(self, agent_id: str) -> Optional[PromptTemplate]:
        return self._prompts.get(agent_id)

    def save(self, template: PromptTemplate) -> None:
        self._prompts[template.agent_id] = template
