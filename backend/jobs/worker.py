"""
jobs/worker.py

Single responsibility: poll for PENDING jobs and execute them asynchronously.
Runs as a long-lived asyncio background task started at app startup.

Design:
  - Polls Neo4j for PENDING jobs on a configurable interval.
  - Respects JOB_MAX_CONCURRENT semaphore.
  - Delegates execution to the registered executor strategy map.
  - Emits JOB_COMPLETED / JOB_FAILED domain events.
  - Retries up to JOB_MAX_RETRIES before final failure.
"""
import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, Callable, Awaitable

from config import JOB_POLL_INTERVAL_SECS, JOB_MAX_CONCURRENT, JOB_MAX_RETRIES, JOB_EXECUTION_TIMEOUT
from events.domain_events import DomainEvent, EventType
from events.dispatcher import EventDispatcher
from jobs.models import Job, JobStatus
from jobs.repository import IJobRepository
from jobs.state_manager import JobStateManager

_log = logging.getLogger(__name__)

# Type alias for an executor function
JobExecutor = Callable[[Job], Awaitable[Dict]]


class JobWorker:
    """
    Background asyncio task. Started once at app startup.
    Executor map is open for extension — register new job_type handlers
    without modifying this class.
    """

    def __init__(
        self,
        repository: IJobRepository,
        dispatcher: EventDispatcher,
        executors: Dict[str, JobExecutor],
    ) -> None:
        self._repo       = repository
        self._dispatcher = dispatcher
        self._executors  = executors
        self._sem        = asyncio.Semaphore(JOB_MAX_CONCURRENT)
        self._running    = False

    def start(self) -> None:
        if not self._running:
            self._running = True
            asyncio.create_task(self._loop(), name="job-worker-loop")
            _log.info("[JobWorker] started poll_interval=%.1fs max_concurrent=%d", JOB_POLL_INTERVAL_SECS, JOB_MAX_CONCURRENT)

    async def _loop(self) -> None:
        while self._running:
            try:
                pending = self._repo.get_by_status(JobStatus.PENDING, limit=JOB_MAX_CONCURRENT)
                tasks   = [asyncio.create_task(self._process(job)) for job in pending]
                if tasks:
                    await asyncio.gather(*tasks, return_exceptions=True)
            except Exception as e:
                _log.error("[JobWorker] poll_error: %s", e)
            await asyncio.sleep(JOB_POLL_INTERVAL_SECS)

    async def _process(self, job: Job) -> None:
        async with self._sem:
            executor = self._executors.get(job.job_type)
            if not executor:
                _log.warning("[JobWorker] no_executor job_type=%s job_id=%s", job.job_type, job.id)
                return

            job.status = JobStateManager.transition(job.status, JobStatus.PROCESSING)
            job.updated_at = datetime.now(timezone.utc)
            self._repo.update_status(job)
            _log.info("[JobWorker] processing job_id=%s type=%s attempt=%d", job.id, job.job_type, job.attempt_count)

            try:
                await asyncio.wait_for(executor(job), timeout=JOB_EXECUTION_TIMEOUT)
                job.status = JobStateManager.transition(job.status, JobStatus.COMPLETED)
                job.updated_at = datetime.now(timezone.utc)
                self._repo.update_status(job)
                _log.info("[JobWorker] completed job_id=%s", job.id)
                await self._dispatcher.emit(DomainEvent(
                    event_type=EventType.JOB_COMPLETED,
                    payload={"job_id": job.id, "session_id": job.session_id, "user_id": job.user_id},
                ))
            except Exception as e:
                job.attempt_count += 1
                job.error_detail   = str(e)
                if job.attempt_count < JOB_MAX_RETRIES:
                    job.status = JobStateManager.transition(job.status, JobStatus.PENDING)
                    _log.warning("[JobWorker] retry job_id=%s attempt=%d error=%s", job.id, job.attempt_count, e)
                else:
                    job.status = JobStateManager.transition(job.status, JobStatus.FAILED)
                    _log.error("[JobWorker] failed job_id=%s error=%s", job.id, e)
                    await self._dispatcher.emit(DomainEvent(
                        event_type=EventType.JOB_FAILED,
                        payload={"job_id": job.id, "session_id": job.session_id, "user_id": job.user_id, "error": str(e)},
                    ))
                job.updated_at = datetime.now(timezone.utc)
                self._repo.update_status(job)
