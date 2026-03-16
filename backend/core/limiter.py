"""
Concurrency Limiter — caps simultaneous Playwright automation jobs.

Each browser instance consumes ~200 MB RAM.
MAX_CONCURRENT_JOBS (default 5) prevents OOM on typical VPS hardware.

The semaphore is acquired in the background task before launching
run_automation(), so queued jobs wait here instead of spawning browsers.
"""

import asyncio
import os

MAX_CONCURRENT_JOBS: int = int(os.environ.get("MAX_CONCURRENT_JOBS", "5"))

# Single semaphore shared across all workers in this process.
automation_semaphore = asyncio.Semaphore(MAX_CONCURRENT_JOBS)
