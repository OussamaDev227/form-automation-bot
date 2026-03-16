"""
Database Service — PostgreSQL via asyncpg.

Manages:
  - Connection pool lifecycle (startup / shutdown)
  - Schema migration (idempotent CREATE TABLE IF NOT EXISTS)
  - CRUD helpers for jobs, attempts, and logs

Schema
──────
  jobs       : one row per automation job
  attempts   : one row per attempt, FK → jobs
  job_logs   : append-only log lines, FK → jobs
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import List, Optional

import asyncpg

from models import AttemptRecord, AttemptStatus, JobStatus

# ── DSN ───────────────────────────────────────────────────
# Set DATABASE_URL in the environment, e.g.:
#   postgresql://formbot:secret@db:5432/formbot
DATABASE_URL: str = os.environ.get(
    "DATABASE_URL",
    "postgresql://formbot:formbot@db:5432/formbot",
)

_pool: Optional[asyncpg.Pool] = None


# ── Pool lifecycle ────────────────────────────────────────

async def init_db() -> None:
    """Create the connection pool and run schema migrations."""
    global _pool
    _pool = await asyncpg.create_pool(
        DATABASE_URL,
        min_size=2,
        max_size=10,
        command_timeout=30,
    )
    await _migrate()


async def close_db() -> None:
    global _pool
    if _pool:
        await _pool.close()
        _pool = None


def get_pool() -> asyncpg.Pool:
    if _pool is None:
        raise RuntimeError("Database pool is not initialised. Call init_db() first.")
    return _pool


# ── Schema migration ──────────────────────────────────────

_SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    job_id      TEXT        PRIMARY KEY,
    target_url  TEXT        NOT NULL,
    status      TEXT        NOT NULL DEFAULT 'created',
    message     TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS attempts (
    id              SERIAL      PRIMARY KEY,
    job_id          TEXT        NOT NULL REFERENCES jobs(job_id) ON DELETE CASCADE,
    attempt_number  INT         NOT NULL,
    status          TEXT        NOT NULL,
    message         TEXT,
    delay_used      FLOAT       NOT NULL DEFAULT 0,
    response_time   FLOAT,
    http_status     INT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS job_logs (
    id          SERIAL      PRIMARY KEY,
    job_id      TEXT        NOT NULL REFERENCES jobs(job_id) ON DELETE CASCADE,
    seq         INT         NOT NULL,
    level       TEXT        NOT NULL DEFAULT 'default',
    message     TEXT        NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_attempts_job_id ON attempts(job_id);
CREATE INDEX IF NOT EXISTS idx_job_logs_job_id ON job_logs(job_id);
"""


async def _migrate() -> None:
    async with get_pool().acquire() as conn:
        await conn.execute(_SCHEMA)


# ── Job CRUD ──────────────────────────────────────────────

async def db_create_job(job_id: str, url: str) -> None:
    await get_pool().execute(
        """
        INSERT INTO jobs (job_id, target_url, status, created_at, updated_at)
        VALUES ($1, $2, 'created', NOW(), NOW())
        ON CONFLICT (job_id) DO NOTHING
        """,
        job_id, url,
    )


async def db_set_job_status(
    job_id: str,
    status: JobStatus,
    message: Optional[str] = None,
) -> None:
    await get_pool().execute(
        """
        UPDATE jobs
           SET status = $2, message = COALESCE($3, message), updated_at = NOW()
         WHERE job_id = $1
        """,
        job_id, status.value, message,
    )


async def db_get_job(job_id: str) -> Optional[asyncpg.Record]:
    return await get_pool().fetchrow(
        "SELECT * FROM jobs WHERE job_id = $1", job_id
    )


# ── Attempt CRUD ──────────────────────────────────────────

async def db_add_attempt(job_id: str, record: AttemptRecord) -> None:
    await get_pool().execute(
        """
        INSERT INTO attempts
            (job_id, attempt_number, status, message, delay_used, response_time, http_status)
        VALUES ($1, $2, $3, $4, $5, $6, $7)
        """,
        job_id,
        record.attempt_number,
        record.status.value,
        record.message,
        record.delay_used,
        record.response_time,
        record.http_status,
    )


async def db_get_attempts(job_id: str) -> List[AttemptRecord]:
    rows = await get_pool().fetch(
        "SELECT * FROM attempts WHERE job_id = $1 ORDER BY attempt_number", job_id
    )
    return [
        AttemptRecord(
            attempt_number=r["attempt_number"],
            status=AttemptStatus(r["status"]),
            message=r["message"] or "",
            delay_used=r["delay_used"],
            response_time=r["response_time"],
            http_status=r["http_status"],
        )
        for r in rows
    ]


# ── Log CRUD ──────────────────────────────────────────────

async def db_append_log(
    job_id: str, seq: int, level: str, message: str
) -> None:
    await get_pool().execute(
        """
        INSERT INTO job_logs (job_id, seq, level, message)
        VALUES ($1, $2, $3, $4)
        """,
        job_id, seq, level, message,
    )


async def db_get_logs(job_id: str) -> List[dict]:
    rows = await get_pool().fetch(
        "SELECT seq, level, message, created_at FROM job_logs WHERE job_id = $1 ORDER BY seq",
        job_id,
    )
    return [
        {
            "job_id":    job_id,
            "seq":       r["seq"],
            "level":     r["level"],
            "message":   r["message"],
            "timestamp": r["created_at"].isoformat(),
        }
        for r in rows
    ]
