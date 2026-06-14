"""Dependency Injection Container"""
from admin.repositories import (
    AgentRepositoryImpl, ChatRepositoryImpl, PromptRepositoryImpl
)
from admin.services import AgentService, ChatService, PromptService
from admin.services.orchestrator import orchestrator

# ═══════════════════════════════════════════════════════════════════════════
# C4 Level 4: Dependency Injection
# SOLID: Dependency Inversion - Centralized dependency management
# ═══════════════════════════════════════════════════════════════════════════

class AdminContainer:
    """Singleton Container for Admin Dependencies"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_dependencies()
        return cls._instance
    
    def _init_dependencies(self):
        """Initialize all dependencies"""
        # Repositories
        self.agent_repo = AgentRepositoryImpl()
        self.chat_repo = ChatRepositoryImpl()
        self.prompt_repo = PromptRepositoryImpl()
        
        # Services
        self.agent_service = AgentService(self.agent_repo)
        self.chat_service = ChatService(self.chat_repo, self.agent_repo)
        self.prompt_service = PromptService(self.prompt_repo)

        # Seed orchestrator with repository's default agents
        for agent in self.agent_repo.get_all().values():
            orchestrator._agents[agent.id] = agent
            orchestrator._configs[agent.id] = agent.config
        
        # 🔥 LINK ORCHESTRATOR TO REPOSITORY FOR PERSISTENCE
        orchestrator.set_repository(self.agent_repo)


# Global container instance
container = AdminContainer()
