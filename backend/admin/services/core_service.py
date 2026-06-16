from typing import Dict, List, Optional
from uuid import uuid4
from datetime import datetime

from admin.domain.models import ChatMessage, PromptTemplate
from admin.repositories.repository import IAgentRepository, IChatRepository, IPromptRepository
from admin.constants import MAX_CONVERSATION_HISTORY, MAX_PROMPT_VARIABLES
from config import GROQ_BASE_URL, get_groq_api_key
import asyncio


class AgentService:
    def __init__(self, agent_repo: IAgentRepository):
        self._repo = agent_repo

    def list_all_agents(self) -> List[Dict]:
        return [a.to_dict() for a in self._repo.get_all().values()]

    def get_agent(self, agent_id: str) -> Optional[Dict]:
        agent = self._repo.get_by_id(agent_id)
        return agent.to_dict() if agent else None

    def update_agent(self, agent_id: str, updates: Dict) -> bool:
        agent = self._repo.get_by_id(agent_id)
        if not agent:
            return False
        for key in ("name", "model", "temperature", "max_tokens", "system_prompt", "is_active"):
            if key in updates:
                if key == "temperature":
                    agent.config.temperature = float(updates[key])
                elif key == "max_tokens":
                    agent.config.max_tokens = int(updates[key])
                elif key == "system_prompt":
                    agent.config.system_prompt = updates[key]
                elif key == "is_active":
                    agent.is_active = bool(updates[key])
                elif key == "model":
                    agent.config.model = updates[key]
                elif key == "name":
                    agent.name = updates[key]
        agent.update_activity()
        self._repo.update(agent)
        return True


class ChatService:
    def __init__(self, chat_repo: IChatRepository, agent_repo: IAgentRepository):
        self._chat_repo = chat_repo
        self._agent_repo = agent_repo
        self._client: Optional[AsyncOpenAI] = None

    def _get_client(self) -> AsyncOpenAI:
        if self._client is None:
            self._client = AsyncOpenAI(api_key=get_groq_api_key(), base_url=GROQ_BASE_URL)
        return self._client

    def get_chat_history(self, agent_id: str, limit: int = 50) -> List[Dict]:
        return [m.to_dict() for m in self._chat_repo.get_by_agent(agent_id, limit)]

    def send_message(self, agent_id: str, content: str, variables: Optional[Dict] = None) -> Dict:
        agent = self._agent_repo.get_by_id(agent_id)
        if not agent or not agent.is_active:
            raise ValueError("Agent not available")
        user_msg = ChatMessage.create_user_message(agent_id, content, variables)
        self._chat_repo.add_message(user_msg)
        ai_content = asyncio.run(self._generate_response(agent, content))
        ai_msg = ChatMessage.create_ai_message(agent_id, ai_content, variables)
        self._chat_repo.add_message(ai_msg)
        agent.update_activity()
        self._agent_repo.update(agent)
        return {"user_message": user_msg.to_dict(), "ai_message": ai_msg.to_dict(), "response": ai_content}

    def clear_history(self, agent_id: str) -> None:
        self._chat_repo.clear_history(agent_id)

    async def _generate_response(self, agent, user_input: str) -> str:
        try:
            messages = []
            if agent.config.system_prompt:
                messages.append({"role": "system", "content": agent.config.system_prompt})
            for msg in self._chat_repo.get_by_agent(agent.id, 5)[:-1]:
                role = "assistant" if msg.role == "ai" else msg.role
                if role in ("user", "assistant"):
                    messages.append({"role": role, "content": msg.content})
            messages.append({"role": "user", "content": user_input})
            response = await self._get_client().chat.completions.create(
                model=agent.config.model,
                messages=messages,
                temperature=agent.config.temperature,
                max_tokens=agent.config.max_tokens,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"Error: {e}"


class PromptService:
    def __init__(self, prompt_repo: IPromptRepository):
        self._repo = prompt_repo

    def get_template(self, agent_id: str) -> Optional[Dict]:
        t = self._repo.get_by_agent(agent_id)
        return t.to_dict() if t else None

    def save_template(self, agent_id: str, template_str: str, variables: Optional[Dict] = None) -> str:
        existing = self._repo.get_by_agent(agent_id)
        if existing:
            existing.template = template_str
            existing.updated_at = datetime.now()
            if variables:
                existing.variables.update(variables)
            self._repo.save(existing)
            return existing.id
        t = PromptTemplate(id=f"prompt-{uuid4().hex[:8]}", agent_id=agent_id,
                           template=template_str, variables=variables or {})
        self._repo.save(t)
        return t.id

    def render_template(self, agent_id: str, runtime_vars: Optional[Dict] = None) -> Optional[str]:
        t = self._repo.get_by_agent(agent_id)
        return t.render(runtime_vars) if t else None

    def update_variables(self, agent_id: str, variables: Dict[str, str]) -> bool:
        t = self._repo.get_by_agent(agent_id)
        if not t:
            return False
        if len(variables) > MAX_PROMPT_VARIABLES:
            raise ValueError(f"Max {MAX_PROMPT_VARIABLES} variables allowed")
        t.variables.update(variables)
        t.updated_at = datetime.now()
        self._repo.save(t)
        return True
