"""
Retry Engine Service
Implements exponential backoff and three retry strategies:
  - resubmit : always re-fill and submit without reloading
  - reload   : always reload the page before submitting
  - hybrid   : reload every N attempts, otherwise resubmit
"""

from __future__ import annotations
import asyncio
import math
from dataclasses import dataclass, field
from typing import Callable, Awaitable, Optional

from models import RetryStrategy, AttemptStatus


# ── Configuration ─────────────────────────────────────────

@dataclass
class RetryConfig:
    max_attempts:      int   = 10
    initial_delay:     float = 2.0    # seconds
    backoff_factor:    float = 2.0
    max_delay:         float = 60.0   # seconds cap
    strategy:          RetryStrategy = RetryStrategy.hybrid
    reload_every:      int   = 3      # for hybrid: reload on attempt % reload_every == 0


@dataclass
class AttemptResult:
    attempt:     int
    status:      AttemptStatus
    message:     str
    delay_used:  float
    http_status: Optional[int]  = None
    response_ms: Optional[float] = None
    should_reload: bool = False


# ── Core logic ────────────────────────────────────────────

class RetryEngine:
    """
    Drives the retry loop.
    The caller supplies an `attempt_fn` coroutine that performs one submission
    and returns an AttemptResult.
    """

    def __init__(self, config: RetryConfig):
        self.config = config

    def compute_delay(self, attempt: int) -> float:
        """Exponential backoff: delay = initial * factor^(attempt-1), capped at max."""
        delay = self.config.initial_delay * math.pow(self.config.backoff_factor, attempt - 1)
        return min(delay, self.config.max_delay)

    def should_reload(self, attempt: int) -> bool:
        """Decide whether this attempt should reload the page first."""
        if self.config.strategy == RetryStrategy.reload:
            return True
        if self.config.strategy == RetryStrategy.resubmit:
            return False
        # hybrid
        return attempt % self.config.reload_every == 0

    async def run(
        self,
        attempt_fn: Callable[[int, bool], Awaitable[AttemptResult]],
        on_attempt: Optional[Callable[[AttemptResult], Awaitable[None]]] = None,
        stop_event: Optional[asyncio.Event] = None,
    ) -> AttemptResult:
        """
        Execute the retry loop.

        attempt_fn(attempt_number, should_reload) → AttemptResult
        on_attempt(result) — called after each attempt (for logging/UI updates)
        stop_event — set externally to abort the loop
        """
        last_result = None

        for attempt in range(1, self.config.max_attempts + 1):
            if stop_event and stop_event.is_set():
                return AttemptResult(
                    attempt=attempt,
                    status=AttemptStatus.failed,
                    message="Stopped by user",
                    delay_used=0,
                )

            delay = self.compute_delay(attempt)
            reload = self.should_reload(attempt)

            result = await attempt_fn(attempt, reload)
            result.delay_used = delay
            result.should_reload = reload
            last_result = result

            if on_attempt:
                await on_attempt(result)

            if result.status == AttemptStatus.success:
                return result

            # Respect 429 / 503 by doubling the delay once more
            actual_delay = delay
            if result.http_status in (429, 503):
                actual_delay = min(delay * 2, self.config.max_delay)

            if attempt < self.config.max_attempts:
                if stop_event:
                    try:
                        await asyncio.wait_for(stop_event.wait(), timeout=actual_delay)
                        if stop_event.is_set():
                            break
                    except asyncio.TimeoutError:
                        pass
                else:
                    await asyncio.sleep(actual_delay)

        return last_result or AttemptResult(
            attempt=self.config.max_attempts,
            status=AttemptStatus.failed,
            message="Max attempts reached",
            delay_used=self.compute_delay(self.config.max_attempts),
        )
