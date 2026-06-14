"""Core Service Layer - Business Logic Orchestration"""
from typing import List, Optional, Dict
from uuid import uuid4
from datetime import datetime

from admin.domain import Agent, ChatMessage, PromptTemplate
from admin.repositories import IAgentRepository, IChatRepository, IPromptRepository
from admin.constants import *

from openai import AsyncOpenAI
from config import GROQ_BASE_URL, get_groq_api_key
import asyncio

# ═══════════════════════════════════════════════════════════════════════════
# C4 Level 4: Service Layer
# SOLID: Single Responsibility - Each service handles specific business logic
# SOLID: Dependency Inversion - Depends on repository interfaces
# ═══════════════════════════════════════════════════════════════════════════

class AgentService:
    """Agent Management Service"""
    
    def __init__(self, agent_repo: IAgentRepository):
        self._repo = agent_repo
    
    def list_all_agents(self) -> List[Dict]:
        """Get all agents"""
        agents = self._repo.get_all()
        return [agent.to_dict() for agent in agents.values()]
    
    def get_agent(self, agent_id: str) -> Optional[Dict]:
        """Get agent by ID"""
        agent = self._repo.get_by_id(agent_id)
        return agent.to_dict() if agent else None
    
    def create_agent(
        self, name: str, model: str, temperature: float,
        max_tokens: int, system_prompt: str = ""
    ) -> str:
        """Create new agent"""
        self._validate_agent_params(name, model, temperature, max_tokens, system_prompt)
        
        agent_id = f"agent-{uuid4().hex[:8]}"
        agent = Agent(
            id=agent_id,
            name=name,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            system_prompt=system_prompt,
            is_active=True
        )
        self._repo.add(agent)
        return agent_id
    
    def update_agent(self, agent_id: str, updates: Dict) -> bool:
        """Update agent configuration"""
        agent = self._repo.get_by_id(agent_id)
        if not agent:
            return False
        
        if "name" in updates:
            agent.name = updates["name"]
        if "model" in updates:
            agent.model = updates["model"]
        if "temperature" in updates:
            agent.temperature = float(updates["temperature"])
        if "max_tokens" in updates:
            agent.max_tokens = int(updates["max_tokens"])
        if "system_prompt" in updates:
            agent.system_prompt = updates["system_prompt"]
        if "is_active" in updates:
            agent.is_active = bool(updates["is_active"])
        
        agent.update_activity()
        self._repo.update(agent)
        return True
    
    def toggle_agent_status(self, agent_id: str, active: bool) -> bool:
        """Activate/deactivate agent"""
        agent = self._repo.get_by_id(agent_id)
        if not agent:
            return False
        agent.is_active = active
        agent.update_activity()
        self._repo.update(agent)
        return True
    
    def delete_agent(self, agent_id: str) -> bool:
        """Delete agent"""
        return self._repo.delete(agent_id)
    
    def _validate_agent_params(
        self, name: str, model: str, temperature: float,
        max_tokens: int, system_prompt: str
    ) -> None:
        """Validate agent parameters"""
        if not name or len(name) > MAX_AGENT_NAME_LENGTH:
            raise ValueError(f"Name must be 1-{MAX_AGENT_NAME_LENGTH} characters")
        
        if model not in SUPPORTED_MODELS:
            raise ValueError(f"Model must be one of {SUPPORTED_MODELS}")
        
        if not MIN_TEMPERATURE <= temperature <= MAX_TEMPERATURE:
            raise ValueError(f"Temperature must be between {MIN_TEMPERATURE} and {MAX_TEMPERATURE}")
        
        if not MIN_MAX_TOKENS <= max_tokens <= MAX_MAX_TOKENS:
            raise ValueError(f"Max tokens must be between {MIN_MAX_TOKENS} and {MAX_MAX_TOKENS}")
        
        if len(system_prompt) > MAX_SYSTEM_PROMPT_LENGTH:
            raise ValueError(f"System prompt too long (max {MAX_SYSTEM_PROMPT_LENGTH})")


class ChatService:
    """Chat Message Service"""
    
    def __init__(self, chat_repo: IChatRepository, agent_repo: IAgentRepository):
        self._chat_repo = chat_repo
        self._agent_repo = agent_repo
        self._client = None
    
    def _get_client(self) -> AsyncOpenAI:
        """Reuse single client instance"""
        if self._client is None:
            self._client = AsyncOpenAI(api_key=get_groq_api_key(), base_url=GROQ_BASE_URL)
        return self._client
    
    def get_chat_history(self, agent_id: str, limit: int = 50) -> List[Dict]:
        """Get chat history for agent"""
        messages = self._chat_repo.get_by_agent(agent_id, limit)
        return [msg.to_dict() for msg in messages]
    
    def send_message(
        self, agent_id: str, content: str,
        variables: Optional[Dict] = None
    ) -> Dict:
        """Send user message and get AI response"""
        agent = self._agent_repo.get_by_id(agent_id)
        if not agent or not agent.is_active:
            raise ValueError("Agent not available")
        
        # Add user message
        user_msg = ChatMessage.create_user_message(agent_id, content, variables)
        self._chat_repo.add_message(user_msg)
        
        # Generate AI response using agent's dynamic config
        ai_content = asyncio.run(self._generate_response(agent, content))
        ai_msg = ChatMessage.create_ai_message(agent_id, ai_content, variables)
        self._chat_repo.add_message(ai_msg)
        
        agent.update_activity()
        self._agent_repo.update(agent)
        
        return {
            "user_message": user_msg.to_dict(),
            "ai_message": ai_msg.to_dict(),
            "response": ai_content
        }
    
    def clear_history(self, agent_id: str) -> None:
        """Clear chat history"""
        self._chat_repo.clear_history(agent_id)
    
    async def _generate_response(self, agent: Agent, user_input: str) -> str:
        """Generate AI response using agent's dynamic temperature and config"""
        try:
            # Build messages with agent's system prompt
            messages = []
            if agent.config.system_prompt:
                messages.append({'role': 'system', 'content': agent.config.system_prompt})
            
            # Get OLD chat history for context (not including current user message)
            history = self._chat_repo.get_by_agent(agent.id, limit=10)
            # Skip the last message (current user message that was just added)
            for msg in history[:-1][-5:]:
                # Convert 'ai' role to 'assistant' for OpenAI API compatibility
                role = 'assistant' if msg.role == 'ai' else msg.role
                # Only include user and assistant messages
                if role in ['user', 'assistant']:
                    messages.append({'role': role, 'content': msg.content})
            
            # Add current user input
            messages.append({'role': 'user', 'content': user_input})
            
            # Call LLM with agent's DYNAMIC config (temperature, max_tokens)
            response = await self._get_client().chat.completions.create(
                model=agent.config.model,
                messages=messages,
                temperature=agent.config.temperature,
                max_tokens=agent.config.max_tokens,
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            return f"Error generating response: {str(e)}"


class PromptService:
    """Dynamic Prompt Management Service"""
    
    def __init__(self, prompt_repo: IPromptRepository):
        self._repo = prompt_repo
    
    def get_template(self, agent_id: str) -> Optional[Dict]:
        """Get prompt template for agent"""
        template = self._repo.get_by_agent(agent_id)
        return template.to_dict() if template else None
    
    def save_template(
        self, agent_id: str, template_str: str,
        variables: Optional[Dict[str, str]] = None
    ) -> str:
        """Save/update prompt template"""
        existing = self._repo.get_by_agent(agent_id)
        
        if existing:
            existing.update_template(template_str)
            if variables:
                existing.variables.update(variables)
            template = existing
        else:
            template = PromptTemplate(
                id=f"prompt-{uuid4().hex[:8]}",
                agent_id=agent_id,
                template=template_str,
                variables=variables or {}
            )
        
        self._repo.save(template)
        return template.id
    
    def render_template(
        self, agent_id: str,
        runtime_vars: Optional[Dict[str, str]] = None
    ) -> Optional[str]:
        """Render template with variables"""
        template = self._repo.get_by_agent(agent_id)
        return template.render(runtime_vars) if template else None
    
    def update_variables(self, agent_id: str, variables: Dict[str, str]) -> bool:
        """Update template variables"""
        template = self._repo.get_by_agent(agent_id)
        if not template:
            return False
        
        if len(variables) > MAX_PROMPT_VARIABLES:
            raise ValueError(f"Maximum {MAX_PROMPT_VARIABLES} variables allowed")
        
        for key, value in variables.items():
            if len(key) > MAX_VARIABLE_NAME_LENGTH:
                raise ValueError(f"Variable name too long: {key}")
            if len(value) > MAX_VARIABLE_VALUE_LENGTH:
                raise ValueError(f"Variable value too long for: {key}")
        
        template.variables.update(variables)
        template.updated_at = datetime.now()
        self._repo.save(template)
        return True
