"""
Route: /api/automation-logs/{job_id}
Returns persisted log entries from PostgreSQL (REST fallback for WebSocket).
"""

from fastapi import APIRouter, Depends, HTTPException
from services.job_store import job_store
from services.database import db_get_logs
from core.auth import require_api_key

router = APIRouter()


@router.get("/automation-logs/{job_id}", dependencies=[Depends(require_api_key)])
async def get_logs(job_id: str):
    row = await job_store.get_job_row(job_id)
    if not row:
        raise HTTPException(status_code=404, detail="Job not found")
    logs = await db_get_logs(job_id)
    attempts = await job_store.get_attempts(job_id)
    return {
        "job_id":   job_id,
        "logs":     logs,
        "attempts": [a.model_dump() for a in attempts],
    }
