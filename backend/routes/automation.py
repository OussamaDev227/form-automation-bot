"""
Routes: /api/start-automation, /api/stop-automation/{job_id}, /api/automation-status/{job_id}
"""

import uuid
import asyncio
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks

from models import (
    StartAutomationRequest,
    AutomationStatusResponse,
    AttemptRecord,
    JobStatus,
    AttemptStatus,
)
from services.job_store import job_store
from services.automation_engine import run_automation
from services.log_broadcaster import broadcaster
from core.auth import require_api_key
from core.limiter import automation_semaphore

router = APIRouter()


async def _run_job(job_id: str, body: StartAutomationRequest):
    """Background task that drives the automation engine."""
    stop_event = job_store.get_stop_event(job_id)
    if stop_event is None:
        return

    await job_store.set_status(job_id, JobStatus.running)
    await broadcaster.emit(job_id, "━━━━ AUTOMATION STARTED ━━━━", "info")
    await broadcaster.emit(
        job_id,
        f"Strategy: {body.settings.retry_strategy} | "
        f"Sessions: {body.settings.parallel_sessions} | "
        f"Max attempts: {body.settings.max_attempts}",
        "info",
    )

    async def on_attempt_done(result):
        record = AttemptRecord(
            attempt_number=result.attempt,
            status=result.status,
            message=result.message,
            delay_used=result.delay_used,
            response_time=result.response_ms,
            http_status=result.http_status,
        )
        await job_store.add_attempt(job_id, record)

    async with automation_semaphore:
        final = await run_automation(
            url=body.url,
            fields=body.fields,
            values=body.values,
            settings=body.settings,
            job_id=job_id,
            log_fn=broadcaster.emit,
            stop_event=stop_event,
            on_attempt_done=on_attempt_done,
        )

    final_status = (
        JobStatus.success if final.status == AttemptStatus.success
        else JobStatus.stopped if stop_event.is_set()
        else JobStatus.failed
    )
    await job_store.set_status(job_id, final_status, final.message)


@router.post("/start-automation", dependencies=[Depends(require_api_key)])
async def start_automation(body: StartAutomationRequest, background: BackgroundTasks):
    from core.url_validator import validate_url
    try:
        validate_url(body.url)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    job_id = str(uuid.uuid4())
    await job_store.create(job_id, body.url)
    await job_store.set_status(job_id, JobStatus.running)
    background.add_task(_run_job, job_id, body)
    return {"job_id": job_id, "status": JobStatus.running}


@router.post("/stop-automation/{job_id}", dependencies=[Depends(require_api_key)])
async def stop_automation(job_id: str):
    row = await job_store.get_job_row(job_id)
    if not row:
        raise HTTPException(status_code=404, detail="Job not found")
    stopped = job_store.signal_stop(job_id)
    await job_store.set_status(job_id, JobStatus.stopped, "Stopped by user")
    await broadcaster.emit(job_id, "■ Automation stopped by user.", "warn")
    return {"job_id": job_id, "status": JobStatus.stopped}


@router.get(
    "/automation-status/{job_id}",
    response_model=AutomationStatusResponse,
    dependencies=[Depends(require_api_key)],
)
async def automation_status(job_id: str):
    row = await job_store.get_job_row(job_id)
    if not row:
        raise HTTPException(status_code=404, detail="Job not found")
    attempts = await job_store.get_attempts(job_id)
    return AutomationStatusResponse(
        job_id=job_id,
        status=JobStatus(row["status"]),
        attempts=attempts,
        message=row["message"],
    )
