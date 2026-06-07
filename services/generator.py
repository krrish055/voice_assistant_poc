import re
from pathlib import Path

from fpdf import FPDF

from exceptions import DocumentGenerationError


_REPORTS_DIR = str(Path(__file__).parent.parent / 'reports')


def _safe_session_id(session_id: str) -> str:
    """Strip any characters that are not alphanumeric, dash, or underscore."""
    return re.sub(r"[^a-zA-Z0-9_\-]", "", session_id)


def _sanitize(value: str) -> str:
    """Remove control characters from user-supplied text before writing to PDF."""
    return re.sub(r"[\x00-\x1f\x7f]", "", str(value))


class GeneratorService:

    @staticmethod
    def generate_dynamic_pdf(ai_data: dict, session_id: str) -> str:
        """
        Build a professional PDF report from structured AI data.
        Returns the absolute path to the generated file.
        Raises DocumentGenerationError on failure.
        """
        try:
            safe_id = _safe_session_id(session_id)
            base   = Path(_REPORTS_DIR).resolve()
            base.mkdir(parents=True, exist_ok=True)
            target = (base / f'Report_{safe_id}.pdf').resolve()
            if not str(target).startswith(str(base)):
                raise DocumentGenerationError('Invalid session_id')

            pdf = FPDF()
            pdf.add_page()

            # ── Title ─────────────────────────────────────────────────────────
            pdf.set_font("Arial", size=18, style="B")
            pdf.set_text_color(44, 62, 80)
            title = _sanitize(ai_data.get("report_title", "EXECUTIVE REPORT")).upper()
            pdf.cell(0, 15, txt=title, ln=True, align="C")
            pdf.ln(3)

            # ── Report ID ─────────────────────────────────────────────────────
            pdf.set_font("Arial", size=10, style="I")
            pdf.set_text_color(127, 140, 141)
            pdf.cell(0, 5, txt=f"Report ID: EXP-{safe_id.upper()}", ln=True, align="R")
            pdf.ln(8)

            # ── Table header ──────────────────────────────────────────────────
            pdf.set_fill_color(52, 73, 94)
            pdf.set_text_color(255, 255, 255)
            pdf.set_font("Arial", size=11, style="B")
            pdf.cell(100, 10, txt="Parameter / Component", border=1, fill=True)
            pdf.cell(90, 10, txt="Value / Calculation", border=1, fill=True, align="C")
            pdf.ln()

            # ── Table rows ────────────────────────────────────────────────────
            pdf.set_text_color(44, 62, 80)
            pdf.set_font("Arial", size=11)
            for row in ai_data.get("structured_data", []):
                pdf.cell(100, 10, txt=_sanitize(row.get("item", "N/A")), border=1)
                pdf.cell(90, 10, txt=_sanitize(row.get("value", "N/A")), border=1, align="C")
                pdf.ln()

            pdf.ln(8)

            # ── AI Summary ────────────────────────────────────────────────────
            pdf.set_font("Arial", size=12, style="B")
            pdf.set_text_color(44, 62, 80)
            pdf.cell(0, 10, txt="AI Summary & Analytical Insights:", ln=True)

            pdf.set_font("Arial", size=11, style="I")
            pdf.set_text_color(52, 73, 94)
            pdf.multi_cell(0, 7, txt=_sanitize(ai_data.get("ai_summary", "No details provided.")))

            filepath = str(target)
            pdf.output(filepath)
            return filepath

        except Exception as e:
            raise DocumentGenerationError(f"PDF generation failed: {e}") from e
