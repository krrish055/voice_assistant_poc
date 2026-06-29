"""
services/tool_executor.py

Single responsibility: execute document-generation tools.

Orchestrator calls this after all slots are confirmed.
No business logic. No slot validation. No LLM calls.

Extensible: add execute_neo4j(), execute_email(), etc. without touching
any other layer.
"""
import logging
from pathlib import Path
from typing import Optional

from services.generator import GeneratorService

_log = logging.getLogger(__name__)


class ToolExecutorService:

    @staticmethod
    def execute_pdf(report_data: dict, session_id: str) -> Optional[str]:
        try:
            path = GeneratorService.generate_dynamic_pdf(report_data, session_id)
            _log.info("[ToolExecutor] PDF generated path=%s", path)
            return f"/api/voice/download-report/{session_id}"
        except Exception as e:
            _log.error("[ToolExecutor] PDF generation FAILED session=%s error=%s", session_id, e, exc_info=True)
            return None

    @staticmethod
    def execute_ppt(report_data: dict, session_id: str) -> Optional[str]:
        try:
            path = GeneratorService.generate_dynamic_pptx(report_data, session_id)
            _log.info("[ToolExecutor] PPTX generated path=%s", path)
            return f"/api/voice/download-pptx/{session_id}"
        except Exception as e:
            _log.error("[ToolExecutor] PPTX generation FAILED session=%s error=%s", session_id, e, exc_info=True)
            return None

    @staticmethod
    def execute(output_format: str, report_data: dict, session_id: str) -> dict:
        """
        Always generate both PDF and PPTX so the frontend always has both links.
        output_format is ignored for dispatch — both tools run every time.
        Returns: {"download_url": str|None, "pptx_url": str|None}
        """
        return {
            "download_url": ToolExecutorService.execute_pdf(report_data, session_id),
            "pptx_url":     ToolExecutorService.execute_ppt(report_data, session_id),
        }
