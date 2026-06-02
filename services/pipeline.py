import os
from openai import AsyncOpenAI
from pydantic import BaseModel
from base import BasePipeline
from exceptions import LLMProcessingError, ConfigurationError

class PipelineResponse(BaseModel):
    status: str
    ai_response_text: str
    next_step: str
    confidence_score: float

class VoicePipelineOrchestrator(BasePipeline):
    def __init__(self):
        self.client = None

    def _get_client(self) -> AsyncOpenAI:
        if self.client is None:
            api_key = os.getenv("GROQ_API_KEY")
            if not api_key:
                raise ConfigurationError("GROQ_API_KEY not found in environment.")
            self.client = AsyncOpenAI(api_key=api_key, base_url="https://api.groq.com/openai/v1")
        return self.client

    def _get_model(self) -> str:
        return os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")  # Fallback to default

    async def execute_stream_pipeline(self, user_id: str, session_id: str, raw_text_input: str) -> dict:
        try:
            if not raw_text_input.strip():
                raise ValueError("Input cannot be empty.")

            response = await self._get_client().chat.completions.create(
                model=self._get_model(),
                messages=[
                    {"role": "system", "content": "You are a professional Startup Consultant. Analyze requirements and ask for missing info."},
                    {"role": "user", "content": raw_text_input}
                ],
                temperature=0.7,
                max_tokens=150
            )

            ai_reply = response.choices[0].message.content.strip()
            question_count = ai_reply.count('?')
            word_count = len(ai_reply.split())
            base_score = min(0.85, round(word_count / 100, 2))
            confidence_score = round(max(0.1, base_score - (question_count * 0.05)), 2)  # Penalize per question asked

            return PipelineResponse(
                status="success",
                ai_response_text=ai_reply,
                next_step="GATHERING_INFO",
                confidence_score=confidence_score
            ).model_dump()

        except ValueError as e:
            return PipelineResponse(
                status="ignored",
                ai_response_text=str(e),
                next_step="GATHERING_INFO",
                confidence_score=0.0
            ).model_dump()

        except Exception as e:
            raise LLMProcessingError(f"Groq API Failure: {str(e)}")

voice_pipeline = VoicePipelineOrchestrator()
