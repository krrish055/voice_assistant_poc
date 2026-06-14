"""Repository Layer - Data Access Abstraction"""
from abc import ABC, abstractmethod
from typing import List, Optional, Dict
from datetime import datetime
from uuid import uuid4
import json
from pathlib import Path

from admin.domain import Agent, AgentConfig, ChatMessage, PromptTemplate
from admin.constants import *

# ═══════════════════════════════════════════════════════════════════════════
# C4 Level 4: Repository Pattern
# SOLID: Dependency Inversion - Abstract interfaces for data access
# SOLID: Interface Segregation - Specific interfaces for each entity
# ═══════════════════════════════════════════════════════════════════════════

class IAgentRepository(ABC):
    """Agent Repository Interface"""
    
    @abstractmethod
    def get_all(self) -> Dict[str, Agent]:
        pass
    
    @abstractmethod
    def get_by_id(self, agent_id: str) -> Optional[Agent]:
        pass
    
    @abstractmethod
    def add(self, agent: Agent) -> None:
        pass
    
    @abstractmethod
    def update(self, agent: Agent) -> None:
        pass
    
    @abstractmethod
    def delete(self, agent_id: str) -> bool:
        pass


class IChatRepository(ABC):
    """Chat Message Repository Interface"""
    
    @abstractmethod
    def get_by_agent(self, agent_id: str, limit: int) -> List[ChatMessage]:
        pass
    
    @abstractmethod
    def add_message(self, message: ChatMessage) -> None:
        pass
    
    @abstractmethod
    def clear_history(self, agent_id: str) -> None:
        pass


class IPromptRepository(ABC):
    """Prompt Template Repository Interface"""
    
    @abstractmethod
    def get_by_agent(self, agent_id: str) -> Optional[PromptTemplate]:
        pass
    
    @abstractmethod
    def save(self, template: PromptTemplate) -> None:
        pass


# ═══════════════════════════════════════════════════════════════════════════
# In-Memory Implementation (can be replaced with database)
# ═══════════════════════════════════════════════════════════════════════════

class AgentRepositoryImpl(IAgentRepository):
    """In-Memory + JSON File Agent Repository"""
    
    def __init__(self, db_file: str = "admin_agents.json"):
        self._db_file = Path(db_file)
        self._agents: Dict[str, Agent] = self._load_from_file() or self._init_default_agents()
        self._save_to_file()
    
    def _load_from_file(self) -> Optional[Dict[str, Agent]]:
        """Load agents from JSON file"""
        if not self._db_file.exists():
            return None
        try:
            with open(self._db_file, 'r') as f:
                data = json.load(f)
            agents = {}
            for agent_id, agent_data in data.items():
                config = AgentConfig(
                    agent_id=agent_data['config']['agent_id'],
                    name=agent_data['config']['name'],
                    model=agent_data['config']['model'],
                    temperature=agent_data['config']['temperature'],
                    max_tokens=agent_data['config']['max_tokens'],
                    system_prompt=agent_data['config']['system_prompt'],
                    extra_params=agent_data['config'].get('extra_params', {})
                )
                agent = Agent(
                    id=agent_data['id'],
                    name=agent_data['name'],
                    config=config,
                    is_active=agent_data.get('is_active', True),
                    metadata=agent_data.get('metadata', {})
                )
                agents[agent_id] = agent
            return agents
        except Exception as e:
            print(f"Error loading agents from file: {e}")
            return None
    
    def _save_to_file(self):
        """Save agents to JSON file"""
        try:
            data = {}
            for agent_id, agent in self._agents.items():
                data[agent_id] = {
                    'id': agent.id,
                    'name': agent.name,
                    'config': {
                        'agent_id': agent.config.agent_id,
                        'name': agent.config.name,
                        'model': agent.config.model,
                        'temperature': agent.config.temperature,
                        'max_tokens': agent.config.max_tokens,
                        'system_prompt': agent.config.system_prompt,
                        'extra_params': agent.config.extra_params
                    },
                    'is_active': agent.is_active,
                    'metadata': agent.metadata
                }
            with open(self._db_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving agents to file: {e}")
    
    def _init_default_agents(self) -> Dict[str, Agent]:
        """Initialize with 3 default agents"""
        return {
            "agent-1": Agent(
                id="agent-1",
                name="Primary Agent",
                config=AgentConfig(agent_id="agent-1", name="Primary Agent", model=DEFAULT_MODEL, temperature=0.7, max_tokens=1000, system_prompt="You are a professional AI assistant."),
                is_active=True,
                metadata={"type": "Voice Assistant", "uptime": "4d 2h"}
            ),
            "agent-2": Agent(
                id="agent-2",
                name="Backup Agent",
                config=AgentConfig(agent_id="agent-2", name="Backup Agent", model=DEFAULT_MODEL, temperature=0.6, max_tokens=1000, system_prompt="You are a backup AI assistant."),
                is_active=False,
                metadata={"type": "Voice Assistant", "uptime": "12h"}
            ),
            "agent-3": Agent(
                id="agent-3",
                name="Compliance Agent",
                config=AgentConfig(agent_id="agent-3", name="Compliance Agent", model=DEFAULT_MODEL, temperature=0.5, max_tokens=1500, system_prompt="You are a compliance specialist AI."),
                is_active=True,
                metadata={"type": "Text Processor", "uptime": "2d"}
            ),
        }
    
    def get_all(self) -> Dict[str, Agent]:
        return self._agents.copy()
    
    def get_by_id(self, agent_id: str) -> Optional[Agent]:
        return self._agents.get(agent_id)
    
    def add(self, agent: Agent) -> None:
        if len(self._agents) >= MAX_AGENTS:
            raise ValueError(f"Maximum {MAX_AGENTS} agents allowed")
        self._agents[agent.id] = agent
        self._save_to_file()
    
    def update(self, agent: Agent) -> None:
        if agent.id in self._agents:
            self._agents[agent.id] = agent
            self._save_to_file()
    
    def delete(self, agent_id: str) -> bool:
        if agent_id in self._agents:
            del self._agents[agent_id]
            self._save_to_file()
            return True
        return False


class ChatRepositoryImpl(IChatRepository):
    """In-Memory Chat Repository"""
    
    def __init__(self):
        self._chats: Dict[str, List[ChatMessage]] = {}
    
    def get_by_agent(self, agent_id: str, limit: int = MAX_CONVERSATION_HISTORY) -> List[ChatMessage]:
        messages = self._chats.get(agent_id, [])
        return messages[-limit:]
    
    def add_message(self, message: ChatMessage) -> None:
        if message.agent_id not in self._chats:
            self._chats[message.agent_id] = []
        self._chats[message.agent_id].append(message)
        # Keep only recent messages
        self._chats[message.agent_id] = self._chats[message.agent_id][-MAX_CONVERSATION_HISTORY:]
    
    def clear_history(self, agent_id: str) -> None:
        if agent_id in self._chats:
            self._chats[agent_id] = []


class PromptRepositoryImpl(IPromptRepository):
    """In-Memory Prompt Template Repository"""
    
    def __init__(self):
        self._prompts: Dict[str, PromptTemplate] = {}
    
    def get_by_agent(self, agent_id: str) -> Optional[PromptTemplate]:
        return self._prompts.get(agent_id)
    
    def save(self, template: PromptTemplate) -> None:
        self._prompts[template.agent_id] = template
