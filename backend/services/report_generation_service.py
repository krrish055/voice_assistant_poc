import logging
from typing import Any, Dict

from config import COMPANY_NAME, LLM_TEMPERATURE, REPORT_MAX_TOKENS, get_model
from graph.graph_repository import graph_repo
from prompts.system_prompts import REPORT_GENERATION_PROMPT
from prompts.template_engine import render
from services.session_memory import ISessionMemory
from services.tool_executor import ToolExecutorService

_log = logging.getLogger(__name__)


class ReportGenerationService:
    """Generate a PDF/PPTX report once all required slots are present.

    Contract:
      - Pure orchestration extracted from OrchestratorAgent._generate_report()
      - No API/routes imports
      - No internal session state; callers pass the session_id and memory
    """

    async def generate(
        self,
        *,
        result: Dict[str, Any],
        session_id: str,
        user_id: str,
        memory: ISessionMemory,
    ) -> Dict[str, Any]:
        slots = memory.get_slots(session_id)
        memory_context = memory.get_context_block(session_id)
        full_history = graph_repo.get_full_session_history(session_id)

        turns_text = "\n".join(
            f"User: {t.get('user_input', '')}\nAssistant: {t.get('ai_response_text', '')}"
            for t in full_history
        )
        # Cap conversation history injected into the generation prompt to avoid
        # exhausting the model's context window and causing truncated JSON output.
        if len(turns_text) > 3000:
            turns_text = turns_text[-3000:]
        full_context = (
            f"{memory_context}\n\n[COMPLETE CONVERSATION HISTORY]\n{turns_text}"
            if full_history
            else memory_context
        )

        topic = slots.get("topic", "Report")
        page_count = min(int(slots.get("page_count") or 5), 7)
        output_format = slots.get("output_format", "PDF")
        key_facts = slots.get("key_facts") or []
        goal = slots.get("goal") or ""
        report_title = result["data"].get("report_title") or topic

        key_facts_text = "\n".join(f"- {f}" for f in key_facts) if key_facts else "(none provided)"

        gen_prompt = render(
            REPORT_GENERATION_PROMPT,
            {
                "company": COMPANY_NAME,
                "topic": topic,
                "page_count": str(page_count),
                "output_format": output_format,
                "report_title": report_title,
                "key_facts": key_facts_text,
                "goal": goal or "Provide a comprehensive overview.",
                "memory_context": full_context,
            },
        )

        from services.pipeline import VoicePipeline

        gen_output = await VoicePipeline().execute(
            system_prompt=gen_prompt,
            model=get_model(),
            temperature=LLM_TEMPERATURE,
            max_tokens=REPORT_MAX_TOKENS,
            history=[],
            user_input=f"Generate a {page_count}-page {output_format} report on: {topic}",
        )

        sections = gen_output.get("sections") or []
        _log.info(
            "[ReportGenerationService] keys=%s sections=%d session=%s",
            list(gen_output.keys()), len(sections), session_id,
        )
        if not sections:
            _log.error(
                "[ReportGenerationService] no sections — full llm output: %s",
                str(gen_output)[:2000],
            )
            result["ai_response_text"] = "Sorry, I could not generate the report. Please try again."
            return result

        report_data = {
            **gen_output,
            "report_title": gen_output.get("report_title") or report_title,
            "structured_data": gen_output.get("structured_data")
            or [
                {"item": "Topic", "value": topic},
                {"item": "Pages", "value": str(page_count)},
                {"item": "Format", "value": output_format},
            ],
            "ai_summary": gen_output.get("ai_summary") or f"Report on {topic}.",
        }

        tool_urls = ToolExecutorService.execute(output_format, report_data, session_id)
        download_url = tool_urls.get("download_url")
        pptx_url     = tool_urls.get("pptx_url")

        if not download_url and not pptx_url:
            _log.error("[ReportGenerationService] file generation failed session=%s", session_id)

        memory.set_last_report_urls(session_id, download_url, pptx_url)
        memory.clear_slots(session_id)

        result["status"] = "success"
        result["ai_response_text"] = gen_output.get("ai_response_text") or "Your report has been generated."
        result["data"] = {**result["data"], **tool_urls}
        result["download_url"] = download_url
        result["pptx_url"]     = pptx_url
        return result

