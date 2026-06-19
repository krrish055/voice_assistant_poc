"""
notifications/manager.py

Single responsibility: factory + routing for notification creation.
Decouples callers from NotificationService construction details.
"""
from notifications.service import NotificationService


class NotificationManager:
    def __init__(self, service: NotificationService) -> None:
        self._service = service

    async def notify_job_completed(self, user_id: str, job_id: str) -> None:
        from constants import NOTIF_JOB_COMPLETED
        await self._service.create(user_id, NOTIF_JOB_COMPLETED, "job", job_id)

    async def notify_job_failed(self, user_id: str, job_id: str) -> None:
        from constants import NOTIF_JOB_FAILED
        await self._service.create(user_id, NOTIF_JOB_FAILED, "job", job_id)

    async def notify_approval_approved(self, user_id: str, approval_id: str) -> None:
        from constants import NOTIF_APPROVAL_APPROVED
        await self._service.create(user_id, NOTIF_APPROVAL_APPROVED, "approval", approval_id)

    async def notify_approval_rejected(self, user_id: str, approval_id: str) -> None:
        from constants import NOTIF_APPROVAL_REJECTED
        await self._service.create(user_id, NOTIF_APPROVAL_REJECTED, "approval", approval_id)
