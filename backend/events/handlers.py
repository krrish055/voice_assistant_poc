"""
events/handlers.py

Concrete event handlers wired at startup.
Each handler has exactly one responsibility.
Dependencies injected — no singletons imported directly.
"""
import logging
from typing import TYPE_CHECKING

from events.domain_events import DomainEvent, EventType
from events.handler_registry import IEventHandler

if TYPE_CHECKING:
    from notifications.service import NotificationService
    from jobs.service import JobService

_log = logging.getLogger(__name__)


class NotificationOnJobCompletedHandler(IEventHandler):
    def __init__(self, notification_service: "NotificationService") -> None:
        self._notif = notification_service

    async def handle(self, event: DomainEvent) -> None:
        from constants import NOTIF_JOB_COMPLETED, NOTIF_JOB_FAILED
        message_map = {
            EventType.JOB_COMPLETED: NOTIF_JOB_COMPLETED,
            EventType.JOB_FAILED:    NOTIF_JOB_FAILED,
        }
        message = message_map.get(event.event_type)
        if not message:
            return
        await self._notif.create(
            user_id=event.payload.get("user_id", ""),
            message=message,
            ref_type="job",
            ref_id=event.payload.get("job_id", ""),
        )


class NotificationOnApprovalHandler(IEventHandler):
    def __init__(self, notification_service: "NotificationService") -> None:
        self._notif = notification_service

    async def handle(self, event: DomainEvent) -> None:
        from constants import NOTIF_APPROVAL_APPROVED, NOTIF_APPROVAL_REJECTED
        message_map = {
            EventType.APPROVAL_APPROVED: NOTIF_APPROVAL_APPROVED,
            EventType.APPROVAL_REJECTED: NOTIF_APPROVAL_REJECTED,
        }
        message = message_map.get(event.event_type)
        if not message:
            return
        await self._notif.create(
            user_id=event.payload.get("user_id", ""),
            message=message,
            ref_type="approval",
            ref_id=event.payload.get("approval_id", ""),
        )


class JobEnqueueOnApprovalHandler(IEventHandler):
    def __init__(self, job_service: "JobService") -> None:
        self._jobs = job_service

    async def handle(self, event: DomainEvent) -> None:
        if event.event_type != EventType.APPROVAL_APPROVED:
            return
        _log.info(
            "[JobEnqueueOnApprovalHandler] approval_approved approval_id=%s",
            event.payload.get("approval_id"),
        )
        await self._jobs.enqueue(
            job_type="approval_execution",
            payload=event.payload.get("original_payload", {}),
            session_id=event.payload.get("session_id", ""),
            user_id=event.payload.get("user_id", ""),
        )
