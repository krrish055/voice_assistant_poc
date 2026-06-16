from admin.repositories.repository import AgentRepositoryImpl, ChatRepositoryImpl, PromptRepositoryImpl
from admin.services.core_service import AgentService, ChatService, PromptService


class AdminContainer:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init()
        return cls._instance

    def _init(self):
        self.agent_repo = AgentRepositoryImpl()
        self.chat_repo = ChatRepositoryImpl()
        self.prompt_repo = PromptRepositoryImpl()
        self.agent_service = AgentService(self.agent_repo)
        self.chat_service = ChatService(self.chat_repo, self.agent_repo)
        self.prompt_service = PromptService(self.prompt_repo)


container = AdminContainer()
