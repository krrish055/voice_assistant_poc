"""
jobs/repository.py

Single responsibility: Neo4j persistence for Job nodes.
Interface + implementation for DIP compliance.
"""
import json
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import List, Optional

from graph.graph_client import graph_client
from jobs.models import Job, JobStatus

_log = logging.getLogger(__name__)

# ── Cypher queries (kept here; job-specific and not shared) ───────────────────

_SAVE_JOB = """
MERGE (j:Job {id: $id})
SET j.job_type      = $job_type,
    j.status        = $status,
    j.payload       = $payload,
    j.session_id    = $session_id,
    j.user_id       = $user_id,
    j.attempt_count = $attempt_count,
    j.created_at    = $created_at,
    j.updated_at    = $updated_at,
    j.error_detail  = $error_detail
WITH j
MATCH (s:Session {id: $session_id})
MERGE (s)-[:HAS_JOB]->(j)
"""

_GET_JOB_BY_ID = """
MATCH (j:Job {id: $id})
RETURN j.id AS id, j.job_type AS job_type, j.status AS status,
       j.payload AS payload, j.session_id AS session_id, j.user_id AS user_id,
       j.attempt_count AS attempt_count, j.created_at AS created_at,
       j.updated_at AS updated_at, j.error_detail AS error_detail
"""

_GET_JOBS_BY_STATUS = """
MATCH (j:Job {status: $status})
RETURN j.id AS id, j.job_type AS job_type, j.status AS status,
       j.payload AS payload, j.session_id AS session_id, j.user_id AS user_id,
       j.attempt_count AS attempt_count, j.created_at AS created_at,
       j.updated_at AS updated_at, j.error_detail AS error_detail
ORDER BY j.created_at ASC
LIMIT $limit
"""

_UPDATE_JOB_STATUS = """
MATCH (j:Job {id: $id})
SET j.status       = $status,
    j.updated_at   = $updated_at,
    j.error_detail = $error_detail,
    j.attempt_count = $attempt_count
"""


class IJobRepository(ABC):
    @abstractmethod
    def save(self, job: Job) -> None: ...

    @abstractmethod
    def get_by_id(self, job_id: str) -> Optional[Job]: ...

    @abstractmethod
    def get_by_status(self, status: JobStatus, limit: int = 50) -> List[Job]: ...

    @abstractmethod
    def update_status(self, job: Job) -> None: ...


class Neo4jJobRepository(IJobRepository):

    def save(self, job: Job) -> None:
        graph_client.run_write(
            _SAVE_JOB,
            id=job.id,
            job_type=job.job_type,
            status=job.status.value,
            payload=json.dumps(job.payload),
            session_id=job.session_id,
            user_id=job.user_id,
            attempt_count=job.attempt_count,
            created_at=job.created_at.isoformat(),
            updated_at=job.updated_at.isoformat(),
            error_detail=job.error_detail,
        )

    def get_by_id(self, job_id: str) -> Optional[Job]:
        rows = graph_client.run(_GET_JOB_BY_ID, id=job_id)
        return Job.from_record(rows[0]) if rows else None

    def get_by_status(self, status: JobStatus, limit: int = 50) -> List[Job]:
        rows = graph_client.run(_GET_JOBS_BY_STATUS, status=status.value, limit=limit)
        return [Job.from_record(r) for r in rows]

    def update_status(self, job: Job) -> None:
        graph_client.run_write(
            _UPDATE_JOB_STATUS,
            id=job.id,
            status=job.status.value,
            updated_at=datetime.now(timezone.utc).isoformat(),
            error_detail=job.error_detail,
            attempt_count=job.attempt_count,
        )
