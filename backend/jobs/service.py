"""
jobs/service.py

Single responsibility: enqueue jobs and serve job queries.
No execution logic — that lives in JobWorker.
"""
import logging
from typing import Dict, List, Optional

from events.domain_events import DomainEvent, EventType
from events.dispatcher import EventDispatcher
from jobs.models import Job, JobStatus
from jobs.repository import IJobRepository

_log = logging.getLogger(__name__)


class JobService:
    def __init__(self, repository: IJobRepository, dispatcher: EventDispatcher) -> None:
        self._repo       = repository
        self._dispatcher = dispatcher

    async def enqueue(
        self,
        job_type: str,
        payload: Dict,
        session_id: str,
        user_id: str,
    ) -> Job:
        job = Job.create(job_type=job_type, payload=payload, session_id=session_id, user_id=user_id)
        self._repo.save(job)
        _log.info("[JobService] job_enqueued id=%s type=%s session=%s", job.id, job_type, session_id)
        await self._dispatcher.emit(DomainEvent(
            event_type=EventType.JOB_STARTED,
            payload={"job_id": job.id, "job_type": job_type, "session_id": session_id, "user_id": user_id},
        ))
        return job

    def get(self, job_id: str) -> Optional[Job]:
        return self._repo.get_by_id(job_id)

    def get_pending(self, limit: int = 50) -> List[Job]:
        return self._repo.get_by_status(JobStatus.PENDING, limit=limit)

    def get_by_status(self, status: JobStatus, limit: int = 50) -> List[Job]:
        return self._repo.get_by_status(status, limit=limit)
