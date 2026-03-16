"""
Log Broadcaster — pub/sub hub that distributes log entries
to all WebSocket subscribers for a given job_id,
AND persists every log line to PostgreSQL.
"""

import asyncio
from collections import defaultdict
from datetime import datetime, timezone
from typing import Dict, List

from models import LogEntry


class LogBroadcaster:
    def __init__(self):
        # job_id → list of asyncio.Queue (one per WebSocket connection)
        self._subscribers: Dict[str, List[asyncio.Queue]] = defaultdict(list)
        self._seq: Dict[str, int] = defaultdict(int)

    def subscribe(self, job_id: str, queue: asyncio.Queue):
        self._subscribers[job_id].append(queue)

    def unsubscribe(self, job_id: str, queue: asyncio.Queue):
        try:
            self._subscribers[job_id].remove(queue)
        except ValueError:
            pass

    async def emit(self, job_id: str, message: str, level: str = "default"):
        self._seq[job_id] += 1
        seq = self._seq[job_id]
        entry = LogEntry(
            job_id=job_id,
            seq=seq,
            level=level,
            message=message,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        payload = entry.model_dump()

        # Persist to PostgreSQL (fire-and-forget, non-blocking)
        try:
            from services.database import db_append_log
            asyncio.ensure_future(db_append_log(job_id, seq, level, message))
        except Exception:
            pass

        # Broadcast to all WebSocket subscribers
        for queue in list(self._subscribers.get(job_id, [])):
            await queue.put(payload)

    def emit_sync(self, job_id: str, message: str, level: str = "default"):
        """Fire-and-forget from sync context."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.ensure_future(self.emit(job_id, message, level))
        except RuntimeError:
            pass


# Singleton shared across the application
broadcaster = LogBroadcaster()
