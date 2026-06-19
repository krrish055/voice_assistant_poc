"""
jobs/state_manager.py

Single responsibility: enforce legal Job FSM transitions.
Strategy pattern — transition_map replaces if/else chains.
"""
from jobs.models import JobStatus
from exceptions import AppBaseException
from constants import ERR_JOB_INVALID_TRANSITION


_TRANSITIONS: dict[JobStatus, set[JobStatus]] = {
    JobStatus.PENDING:    {JobStatus.PROCESSING, JobStatus.FAILED},
    JobStatus.PROCESSING: {JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.PENDING},
    JobStatus.COMPLETED:  set(),
    JobStatus.FAILED:     {JobStatus.PENDING},  # retry path
}


class JobStateManager:
    @staticmethod
    def transition(current: JobStatus, target: JobStatus) -> JobStatus:
        allowed = _TRANSITIONS.get(current, set())
        if target not in allowed:
            raise AppBaseException(
                f"{ERR_JOB_INVALID_TRANSITION}: {current} → {target}", status_code=409
            )
        return target
