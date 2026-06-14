import json
from datetime import datetime

from openai import AsyncOpenAI
from pydantic import BaseModel

from base import BasePipeline
from config import GROQ_BASE_URL, SYSTEM_PROMPT, get_groq_api_key, get_model, LLM_TEMPERATURE, LLM_MAX_TOKENS
from exceptions import LLMProcessingError
from admin.services.orchestrator import orchestrator


class PipelineResponse(BaseModel):
    status           : str
    ai_response_text : str
    confidence_score : float
    data             : dict = {}


class VoicePipelineOrchestrator(BasePipeline):

    def __init__(self) -> None:
        self._client: AsyncOpenAI | None = None

    def _get_client(self) -> AsyncOpenAI:
        if self._client is None:
            self._client = AsyncOpenAI(api_key=get_groq_api_key(), base_url=GROQ_BASE_URL)
        return self._client

    @staticmethod
    def _strip_markdown(raw: str) -> str:
        if raw.startswith('```'):
            raw = raw.split('```')[1]
            if raw.startswith('json'):
                raw = raw[4:]
        return raw.strip()

    @staticmethod
    def _extract_clean_text(raw: str) -> str:
        """Extract only the natural language part — strip any appended JSON block."""
        # Try parsing the whole thing as JSON first
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                return parsed.get('ai_response_text') or raw
        except (json.JSONDecodeError, ValueError):
            pass
        # Strip trailing JSON block appended after natural text (e.g. "text...\n\n{...}")
        brace_pos = raw.rfind('\n{')
        if brace_pos != -1:
            tail = raw[brace_pos:].strip()
            try:
                parsed = json.loads(tail)
                if isinstance(parsed, dict) and 'intent' in parsed:
                    return raw[:brace_pos].strip()
            except (json.JSONDecodeError, ValueError):
                pass
        return raw.strip()

    def _build_messages(self, history: list, raw_text_input: str) -> list:
        messages = [{'role': 'system', 'content': SYSTEM_PROMPT}]
        for turn in history:
            messages.append({'role': 'user', 'content': turn['user_input']})
            # Sanitize saved ai_response_text — strip any appended JSON from old turns
            clean = self._extract_clean_text(turn.get('ai_response_text', ''))
            messages.append({'role': 'assistant', 'content': clean})
        messages.append({'role': 'user', 'content': raw_text_input})
        return messages

    async def execute_stream_pipeline(self, raw_text_input: str, history: list) -> dict:
        if not raw_text_input.strip():
            return PipelineResponse(
                status='ignored',
                ai_response_text='Please say something so I can help you.',
                confidence_score=0.0,
            ).model_dump()

        # Safe agent config extraction with fallback
        model = get_model()
        temperature = LLM_TEMPERATURE
        max_tokens = LLM_MAX_TOKENS
        system_prompt = SYSTEM_PROMPT
        source = "Hardcoded Config"
        
        try:
            # Try to get active agent from orchestrator
            if hasattr(orchestrator, '_agents') and orchestrator._agents:
                for agent_id, agent in orchestrator._agents.items():
                    if hasattr(agent, 'is_active') and agent.is_active and hasattr(agent, 'config'):
                        if agent.config and all(hasattr(agent.config, attr) for attr in ['model', 'temperature', 'max_tokens']):
                            model = agent.config.model
                            temperature = agent.config.temperature
                            max_tokens = agent.config.max_tokens
                            system_prompt = agent.config.system_prompt or SYSTEM_PROMPT
                            source = f"Agent: {agent.name}"
                            break
        except Exception as e:
            print(f"⚠️  Failed to load agent config, using fallback: {e}")

        try:
            # Build messages with dynamic system prompt
            messages = [{'role': 'system', 'content': system_prompt}]
            for turn in history:
                messages.append({'role': 'user', 'content': turn['user_input']})
                clean = self._extract_clean_text(turn.get('ai_response_text', ''))
                messages.append({'role': 'assistant', 'content': clean})
            messages.append({'role': 'user', 'content': raw_text_input})
            
            response = await self._get_client().chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except Exception as e:
            raise LLMProcessingError(f'Groq API call failed: {e}') from e

        raw_content = response.choices[0].message.content.strip()
        
        # Safe JSON parsing with multiple fallback layers
        try:
            ai_data = json.loads(self._strip_markdown(raw_content))
            if not isinstance(ai_data, dict):
                ai_data = {'intent': 'CHAT', 'ai_response_text': raw_content, 'confidence_score': 1.0}
        except (json.JSONDecodeError, ValueError, TypeError):
            ai_data = {'intent': 'CHAT', 'ai_response_text': raw_content, 'confidence_score': 1.0}

        # Extract clean natural language with safety
        try:
            ai_text = self._extract_clean_text(
                ai_data.get('ai_response_text') or raw_content
            )
        except Exception:
            ai_text = raw_content

        return PipelineResponse(
            status='success',
            ai_response_text=ai_text,
            confidence_score=float(ai_data.get('confidence_score', 1.0)),
            data=ai_data,
        ).model_dump()


voice_pipeline = VoicePipelineOrchestrator()
