from services.speech_processor import SpeechProcessorService
from services.response_builder import ResponseBuilderService
from services.memory_service import MemoryService
from services.tool_executor import ToolExecutorService


def _get_singletons():
    from services.container import voice_pipeline, orchestrator, memory
    return voice_pipeline, orchestrator, memory


__all__ = [
    'SpeechProcessorService', 'ResponseBuilderService',
    'MemoryService', 'ToolExecutorService',
]
