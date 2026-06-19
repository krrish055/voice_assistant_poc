from events.handler_registry import EventHandlerRegistry
from events.dispatcher import EventDispatcher
from events.domain_events import EventType
from events.handlers import (
    NotificationOnJobCompletedHandler,
    NotificationOnApprovalHandler,
    JobEnqueueOnApprovalHandler,
)

from notifications.repository import Neo4jNotificationRepository
from notifications.service import NotificationService
from notifications.manager import NotificationManager

from approvals.repository import Neo4jApprovalRepository
from approvals.service import ApprovalService

from jobs.repository import Neo4jJobRepository
from jobs.service import JobService
from jobs.worker import JobWorker

from services.session_memory import SessionMemoryService
from services.pipeline import VoicePipeline
from agents.orchestrator_agent import OrchestratorAgent
from registry.agent_registry import registry

# ── Event Infrastructure ──────────────────────────────────────────────────────
_handler_registry = EventHandlerRegistry()
dispatcher        = EventDispatcher(_handler_registry)

# ── Notification Service ──────────────────────────────────────────────────────
_notif_repo          = Neo4jNotificationRepository()
notification_service = NotificationService(repository=_notif_repo, dispatcher=dispatcher)
notification_manager = NotificationManager(service=notification_service)

# ── Approval Service ──────────────────────────────────────────────────────────
_approval_repo   = Neo4jApprovalRepository()
approval_service = ApprovalService(repository=_approval_repo, dispatcher=dispatcher)

# ── Job Service + Worker ──────────────────────────────────────────────────────
_job_repo   = Neo4jJobRepository()
job_service = JobService(repository=_job_repo, dispatcher=dispatcher)

_handler_registry.register(EventType.JOB_COMPLETED,     NotificationOnJobCompletedHandler(notification_service))
_handler_registry.register(EventType.JOB_FAILED,        NotificationOnJobCompletedHandler(notification_service))
_handler_registry.register(EventType.APPROVAL_APPROVED, NotificationOnApprovalHandler(notification_service))
_handler_registry.register(EventType.APPROVAL_REJECTED, NotificationOnApprovalHandler(notification_service))
_handler_registry.register(EventType.APPROVAL_APPROVED, JobEnqueueOnApprovalHandler(job_service))


def _build_report_executor():
    async def execute(job) -> dict:
        import logging
        _elog = logging.getLogger("job.report_executor")
        from services.tool_executor import ToolExecutorService
        from services.pipeline import VoicePipeline
        from config import get_model, LLM_TEMPERATURE, REPORT_MAX_TOKENS

        payload       = job.payload
        gen_prompt    = payload.get("gen_prompt", "")
        session_id    = job.session_id
        output_format = payload.get("output_format", "PDF")
        topic         = payload.get("topic", "Report")
        page_count    = payload.get("page_count", 3)
        report_title  = payload.get("report_title", topic)

        pipeline   = VoicePipeline()
        gen_output = await pipeline.execute(
            system_prompt=gen_prompt,
            model=get_model(),
            temperature=LLM_TEMPERATURE,
            max_tokens=REPORT_MAX_TOKENS,
            history=[],
            user_input=f"Generate a {page_count}-page {output_format} report on: {topic}",
        )

        sections = gen_output.get("sections") or []
        if not sections:
            raise RuntimeError(f"LLM returned no sections for job {job.id}")

        report_data = {
            **gen_output,
            "report_title":    gen_output.get("report_title") or report_title,
            "structured_data": gen_output.get("structured_data") or [
                {"item": "Topic",  "value": topic},
                {"item": "Pages",  "value": str(page_count)},
                {"item": "Format", "value": output_format},
            ],
            "ai_summary": gen_output.get("ai_summary") or f"Report on {topic}.",
        }

        tool_urls = ToolExecutorService.execute(output_format, report_data, session_id)
        if not tool_urls.get("download_url") and not tool_urls.get("pptx_url"):
            raise RuntimeError(f"ToolExecutor produced no output for job {job.id}")

        _elog.info("[ReportExecutor] done job_id=%s urls=%s", job.id, tool_urls)
        return tool_urls
    return execute


job_worker = JobWorker(
    repository=_job_repo,
    dispatcher=dispatcher,
    executors={
        "report_generation":  _build_report_executor(),
        "approval_execution": _build_report_executor(),
    },
)

# ── Voice Pipeline ────────────────────────────────────────────────────────────
memory: SessionMemoryService = SessionMemoryService()
registry.seed_defaults(memory=memory)

voice_pipeline: VoicePipeline   = VoicePipeline()
orchestrator:   OrchestratorAgent = OrchestratorAgent(
    pipeline=voice_pipeline,
    memory=memory,
    approval_service=approval_service,
    job_service=job_service,
    dispatcher=dispatcher,
)
