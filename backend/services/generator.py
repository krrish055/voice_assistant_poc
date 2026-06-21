import re
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "reports"))

from exceptions import DocumentGenerationError
from utils import safe_path, REPORTS_DIR


def _sanitize(value: str) -> str:
    return re.sub(r'[\x00-\x1f\x7f]', '', str(value))


def _clean_ai_data(ai_data: dict) -> dict:
    """Sanitize all string values in the ai_data dict recursively."""
    cleaned = {}
    for k, v in ai_data.items():
        if isinstance(v, str):
            cleaned[k] = _sanitize(v)
        elif isinstance(v, list):
            cleaned[k] = [
                {ik: _sanitize(iv) if isinstance(iv, str) else iv
                 for ik, iv in item.items()} if isinstance(item, dict)
                else (_sanitize(item) if isinstance(item, str) else item)
                for item in v
            ]
        else:
            cleaned[k] = v
    return cleaned


class GeneratorService:

    @staticmethod
    def generate_dynamic_pdf(ai_data: dict, session_id: str) -> str:
        try:
            from itt_report_template import ITTPDFTemplate
        except ImportError as e:
            raise DocumentGenerationError(f"PDF template import failed: {e}") from e

        try:
            Path(REPORTS_DIR).mkdir(parents=True, exist_ok=True)
            output_path = str(safe_path(REPORTS_DIR, f"Report_{session_id}.pdf"))
            template = ITTPDFTemplate()
            template.render(_clean_ai_data(ai_data), session_id, output_path)
            return output_path
        except DocumentGenerationError:
            raise
        except Exception as e:
            raise DocumentGenerationError(f"PDF generation failed: {e}") from e

    @staticmethod
    def generate_dynamic_pptx(ai_data: dict, session_id: str) -> Path:
        try:
            from itt_pptx_template import ITTPPTXTemplate
        except ImportError as e:
            raise DocumentGenerationError(f"PPTX template import failed: {e}") from e

        try:
            Path(REPORTS_DIR).mkdir(parents=True, exist_ok=True)
            output_path = str(safe_path(REPORTS_DIR, f"Presentation_{session_id}.pptx"))
            template = ITTPPTXTemplate()
            template.render(_clean_ai_data(ai_data), session_id, output_path)
            return Path(output_path)
        except DocumentGenerationError:
            raise
        except Exception as e:
            raise DocumentGenerationError(f"PPTX generation failed: {e}") from e
