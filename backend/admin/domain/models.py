"""Domain Models - Dynamic Multi-Agent State Entities"""
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from uuid import uuid4
from enum import Enum
from string import Template

# ═══════════════════════════════════════════════════════════════════════════
# C4 Level 4: Domain Entities (State Orchestration Pattern)
# SOLID: Single Responsibility - Each entity manages its runtime state
# ═══════════════════════════════════════════════════════════════════════════

class AgentStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"

@dataclass
class AgentConfig:
    """Dynamic Agent Configuration (Registry Pattern)"""
    agent_id: str
    name: str
    model: str
    temperature: float = 0.7
    max_tokens: int = 2000
    system_prompt: str = ""
    extra_params: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "system_prompt": self.system_prompt,
            "extra_params": self.extra_params
        }

@dataclass
class Agent:
    """Runtime Agent Entity with Live State"""
    id: str
    name: str
    config: AgentConfig
    status: AgentStatus = AgentStatus.IDLE
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)
    memory_context: List[Dict] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)
    
    def update_config(self, new_config: AgentConfig) -> None:
        """Hot-swap config without restart"""
        self.config = new_config
        self.last_activity = datetime.now()
    
    def update_activity(self) -> None:
        self.last_activity = datetime.now()
    
    def reset_memory(self) -> None:
        """Restart agent memory"""
        self.memory_context.clear()
        self.status = AgentStatus.IDLE
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "config": self.config.to_dict(),
            "status": self.status.value,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "memory_size": len(self.memory_context),
            "metadata": self.metadata
        }

@dataclass
class ChatMessage:
    """Chat Message Entity"""
    id: str
    agent_id: str
    role: str  # "user" | "ai" | "system"
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    variables: Dict = field(default_factory=dict)
    
    @classmethod
    def create_user_message(cls, agent_id: str, content: str, variables: Dict = None):
        return cls(
            id=str(uuid4()),
            agent_id=agent_id,
            role="user",
            content=content,
            variables=variables or {}
        )
    
    @classmethod
    def create_ai_message(cls, agent_id: str, content: str, variables: Dict = None):
        return cls(
            id=str(uuid4()),
            agent_id=agent_id,
            role="ai",
            content=content,
            variables=variables or {}
        )
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "variables": self.variables
        }

@dataclass
class PromptTemplate:
    """Dynamic Prompt Template with Runtime Variable Injection"""
    id: str
    agent_id: str
    template: str
    variables: Dict[str, str] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def render(self, runtime_vars: Optional[Dict[str, str]] = None) -> str:
        """Render using Python Template (supports ${variable} syntax)"""
        merged_vars = {**self.variables, **(runtime_vars or {})}
        template = Template(self.template)
        return template.safe_substitute(**merged_vars)
    
    def update_template(self, template: str) -> None:
        self.template = template
        self.updated_at = datetime.now()
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "template": self.template,
            "variables": self.variables,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }

@dataclass
class AgentLog:
    """Real-time Agent Activity Log"""
    id: str
    agent_id: str
    event_type: str  # "config_update" | "prompt_change" | "execution" | "error"
    details: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)
    user: str = "system"
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "event_type": self.event_type,
            "details": self.details,
            "timestamp": self.timestamp.isoformat(),
            "user": self.user
        }
