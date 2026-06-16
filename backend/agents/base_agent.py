from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional


@dataclass
class AgentConfig:
    agent_id: str
    name: str
    model: str
    temperature: float = 0.7
    max_tokens: int = 1000
    system_prompt: str = ""

    def to_dict(self) -> Dict:
        return self.__dict__.copy()


@dataclass
class AgentInput:
    user_text: str
    session_history: List[Dict] = field(default_factory=list)
    compliance_rules: List[str] = field(default_factory=list)


@dataclass
class AgentOutput:
    text: str
    intent: str = "CHAT"
    data: Dict = field(default_factory=dict)
    confidence: float = 1.0


@dataclass
class BaseAgent(ABC):
    id: str
    name: str
    config: AgentConfig
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)

    @abstractmethod
    def agent_type(self) -> str: ...

    @abstractmethod
    def build_prompt(self, agent_input: AgentInput) -> str: ...

    @abstractmethod
    def post_process(self, raw_output: Dict) -> AgentOutput: ...

    def update_activity(self) -> None:
        self.last_activity = datetime.now()

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.agent_type(),
            "config": self.config.to_dict(),
            "is_active": self.is_active,
            "last_activity": self.last_activity.isoformat(),
        }
