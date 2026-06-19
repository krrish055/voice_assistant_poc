"""
admin/api/jobs_router.py

Endpoints: query jobs by status, get a specific job.
"""
from fastapi import APIRouter, HTTPException
from typing import Dict

from jobs.models import JobStatus
from admin.constants import SUCCESS_CODE
from constants import ERR_JOB_NOT_FOUND
from services.container import job_service

router = APIRouter(prefix="/api/admin/jobs", tags=["Jobs"])


@router.get("")
def list_jobs(status: JobStatus = JobStatus.PENDING, limit: int = 50) -> Dict:
    jobs = job_service.get_by_status(status, limit=limit)
    return {
        "status": SUCCESS_CODE,
        "jobs":   [j.to_dict() for j in jobs],
        "total":  len(jobs),
    }


@router.get("/{job_id}")
def get_job(job_id: str) -> Dict:
    job = job_service.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=ERR_JOB_NOT_FOUND)
    return {"status": SUCCESS_CODE, "job": job.to_dict()}
