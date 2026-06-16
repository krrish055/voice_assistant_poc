from datetime import datetime
from dataclasses import dataclass, field
from typing import Dict, Optional
from uuid import uuid4
from agents.base_agent import AgentConfig  # single source of truth
from prompts.template_engine import render  # single render implementation


@dataclass
class ChatMessage:
    id: str
    agent_id: str
    role: str  # "user" | "ai"
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    variables: Dict = field(default_factory=dict)

    @classmethod
    def create_user_message(cls, agent_id: str, content: str, variables: Dict = None):
        return cls(id=str(uuid4()), agent_id=agent_id, role="user", content=content, variables=variables or {})

    @classmethod
    def create_ai_message(cls, agent_id: str, content: str, variables: Dict = None):
        return cls(id=str(uuid4()), agent_id=agent_id, role="ai", content=content, variables=variables or {})

    def to_dict(self) -> Dict:
        return {"id": self.id, "agent_id": self.agent_id, "role": self.role,
                "content": self.content, "timestamp": self.timestamp.isoformat()}


@dataclass
class PromptTemplate:
    id: str
    agent_id: str
    template: str
    variables: Dict[str, str] = field(default_factory=dict)
    updated_at: datetime = field(default_factory=datetime.now)

    def render(self, runtime_vars: Optional[Dict[str, str]] = None) -> str:
        return render(self.template, {**self.variables, **(runtime_vars or {})})

    def to_dict(self) -> Dict:
        return {"id": self.id, "agent_id": self.agent_id, "template": self.template,
                "variables": self.variables, "updated_at": self.updated_at.isoformat()}
