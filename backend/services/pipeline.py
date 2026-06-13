import json
from openai import AsyncOpenAI
from pydantic import BaseModel

from base import BasePipeline
from config import GROQ_BASE_URL, SYSTEM_PROMPT, get_groq_api_key, get_model, LLM_TEMPERATURE, LLM_MAX_TOKENS
from exceptions import LLMProcessingError


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
    def _build_messages(history: list, raw_text_input: str) -> list:
        messages = [{'role': 'system', 'content': SYSTEM_PROMPT}]
        for turn in history:
            messages.append({'role': 'user', 'content': turn['user_input']})
            ai_context = turn.get('ai_response_text', '')
            if turn.get('ai_data'):
                try:
                    ai_context = json.dumps(turn['ai_data'])
                except Exception:
                    pass
            messages.append({'role': 'assistant', 'content': ai_context})
        messages.append({'role': 'user', 'content': raw_text_input})
        return messages

    async def execute_stream_pipeline(self, raw_text_input: str, history: list) -> dict:
        if not raw_text_input.strip():
            return PipelineResponse(
                status='ignored',
                ai_response_text='Please say something so I can help you.',
                confidence_score=0.0,
            ).model_dump()

        try:
            response = await self._get_client().chat.completions.create(
                model=get_model(),
                messages=self._build_messages(history, raw_text_input),
                temperature=LLM_TEMPERATURE,
                max_tokens=LLM_MAX_TOKENS,
            )
        except Exception as e:
            raise LLMProcessingError(f'Groq API call failed: {e}') from e

        raw_content = response.choices[0].message.content.strip()
        try:
            ai_data = json.loads(self._strip_markdown(raw_content))
        except (json.JSONDecodeError, ValueError):
            # LLM returned plain text instead of JSON — treat it as a CHAT response
            ai_data = {'intent': 'CHAT', 'ai_response_text': raw_content, 'confidence_score': 1.0}

        return PipelineResponse(
            status='success',
            ai_response_text=ai_data.get('ai_response_text') or raw_content,
            confidence_score=float(ai_data.get('confidence_score', 1.0)),
            data=ai_data,
        ).model_dump()


voice_pipeline = VoicePipelineOrchestrator()
