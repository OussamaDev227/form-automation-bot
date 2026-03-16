"""
Job Store — PostgreSQL-backed with in-memory stop_events.

Persistent state (status, attempts, logs) lives in PostgreSQL.
The asyncio.Event for stopping a running job lives in memory only
(it doesn't need to survive restarts — a restarted server has no
running jobs to stop).
"""

from __future__ import annotations

import asyncio
from typing import Dict, List, Optional

from models import AttemptRecord, JobStatus
from services.database import (
    db_create_job,
    db_set_job_status,
    db_get_job,
    db_add_attempt,
    db_get_attempts,
)


class JobStore:
    """
    Thin coordination layer on top of the database.
    Keeps a dict of asyncio.Event objects for in-flight jobs.
    """

    def __init__(self) -> None:
        # job_id → asyncio.Event  (only for jobs started in this process)
        self._stop_events: Dict[str, asyncio.Event] = {}

    # ── Lifecycle ─────────────────────────────────────────

    async def create(self, job_id: str, url: str) -> asyncio.Event:
        """Insert a new job row and return its stop_event."""
        await db_create_job(job_id, url)
        event = asyncio.Event()
        self._stop_events[job_id] = event
        return event

    def get_stop_event(self, job_id: str) -> Optional[asyncio.Event]:
        return self._stop_events.get(job_id)

    # ── Status ────────────────────────────────────────────

    async def set_status(
        self,
        job_id: str,
        status: JobStatus,
        message: Optional[str] = None,
    ) -> None:
        await db_set_job_status(job_id, status, message)
        if status in (JobStatus.success, JobStatus.failed, JobStatus.stopped):
            self._stop_events.pop(job_id, None)

    async def get_job_row(self, job_id: str):
        return await db_get_job(job_id)

    # ── Attempts ──────────────────────────────────────────

    async def add_attempt(self, job_id: str, record: AttemptRecord) -> None:
        await db_add_attempt(job_id, record)

    async def get_attempts(self, job_id: str) -> List[AttemptRecord]:
        return await db_get_attempts(job_id)

    # ── Stop signal ───────────────────────────────────────

    def signal_stop(self, job_id: str) -> bool:
        """Set the stop event. Returns False if job is not running here."""
        event = self._stop_events.get(job_id)
        if event:
            event.set()
            return True
        return False


# Singleton
job_store = JobStore()
