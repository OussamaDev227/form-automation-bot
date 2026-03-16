"""
Automation Engine Service
Fills and submits a form in a Playwright browser session.
Supports all field types and smart submit-button detection.
"""

from __future__ import annotations
import asyncio
import time
from typing import Dict, List, Optional

from playwright.async_api import async_playwright, Page, Browser, BrowserContext

from models import FormField, AttemptStatus
from services.retry_engine import AttemptResult
from services.success_detector import detect_success


# ── Submit button selectors (ordered by priority) ─────────
SUBMIT_SELECTORS = [
    "button[type='submit']",
    "input[type='submit']",
    "button:has-text('submit')",
    "button:has-text('register')",
    "button:has-text('sign up')",
    "button:has-text('signup')",
    "button:has-text('create account')",
    # French
    "button:has-text('envoyer')",
    "button:has-text('inscription')",
    "button:has-text('s'inscrire')",
    # Arabic
    "button:has-text('إرسال')",
    "button:has-text('تسجيل')",
    # Fallback: any button inside a form
    "form button",
    "form input[type='button']",
]


# ── Field filler ──────────────────────────────────────────

async def fill_field(page: Page, field: FormField, value: str) -> None:
    """Fill a single form field according to its type."""
    selector = (
        f"#{field.id}" if field.id
        else f"[name='{field.name}']" if field.name
        else None
    )
    if not selector:
        return

    try:
        ftype = field.type.lower()

        if ftype in ("text", "email", "password", "number", "tel", "url", "date", "search"):
            await page.fill(selector, value)

        elif ftype == "textarea":
            await page.fill(selector, value)

        elif ftype == "checkbox":
            truthy = value.lower() in ("true", "1", "yes", "on", "checked")
            if truthy:
                await page.check(selector)
            else:
                await page.uncheck(selector)

        elif ftype == "radio":
            # selector for a specific radio option value
            radio_sel = f"input[type='radio'][name='{field.name}'][value='{value}']"
            await page.check(radio_sel)

        elif ftype == "select":
            await page.select_option(selector, value=value)

        elif ftype == "file":
            # value should be an absolute path on the server
            await page.set_input_files(selector, value)

        # hidden fields: skip (they are pre-set by the server)

    except Exception:
        pass  # Non-fatal — log upstream if needed


async def find_and_click_submit(page: Page) -> bool:
    """Try each submit selector in priority order. Returns True if clicked."""
    for sel in SUBMIT_SELECTORS:
        try:
            btn = await page.query_selector(sel)
            if btn and await btn.is_visible() and await btn.is_enabled():
                await btn.click()
                return True
        except Exception:
            continue
    return False


# ── Single-session attempt ────────────────────────────────

async def run_single_attempt(
    url: str,
    fields: List[FormField],
    values: Dict[str, str],
    attempt: int,
    should_reload: bool,
    success_checks: dict,
    context: BrowserContext,
) -> AttemptResult:
    """
    Perform one fill-and-submit cycle in an existing browser context.
    Returns an AttemptResult.
    """
    page = await context.new_page()
    t0 = time.perf_counter()

    try:
        if should_reload or attempt == 1:
            response = await page.goto(url, wait_until="domcontentloaded", timeout=30_000)
            http_status = response.status if response else None
        else:
            http_status = None

        # Fill all fields
        for field in fields:
            val = values.get(field.name or field.id or "", field.default or "")
            if val:
                await fill_field(page, field, val)
            await asyncio.sleep(0.05)   # slight delay to appear human

        # Submit
        clicked = await find_and_click_submit(page)
        if not clicked:
            return AttemptResult(
                attempt=attempt,
                status=AttemptStatus.failed,
                message="Submit button not found",
                delay_used=0,
                http_status=http_status,
                response_ms=(time.perf_counter() - t0) * 1000,
            )

        # Wait for navigation / network settle
        try:
            await page.wait_for_load_state("networkidle", timeout=15_000)
        except Exception:
            pass

        elapsed = (time.perf_counter() - t0) * 1000

        # Success detection
        result = await detect_success(
            page=page,
            original_url=url,
            response_status=http_status,
            checks=success_checks,
        )

        if result.succeeded:
            return AttemptResult(
                attempt=attempt,
                status=AttemptStatus.success,
                message=result.reason,
                delay_used=0,
                http_status=http_status,
                response_ms=elapsed,
            )

        # Detect server-side errors via HTTP status
        if http_status == 429:
            status = AttemptStatus.limited
            msg    = "429 Too Many Requests — rate limited"
        elif http_status in (500, 502, 503, 504):
            status = AttemptStatus.busy
            msg    = f"{http_status} Server Error — will retry"
        else:
            status = AttemptStatus.failed
            msg    = f"Submission failed — {result.reason}"

        return AttemptResult(
            attempt=attempt,
            status=status,
            message=msg,
            delay_used=0,
            http_status=http_status,
            response_ms=elapsed,
        )

    except Exception as exc:
        return AttemptResult(
            attempt=attempt,
            status=AttemptStatus.failed,
            message=f"Exception: {str(exc)[:120]}",
            delay_used=0,
            response_ms=(time.perf_counter() - t0) * 1000,
        )
    finally:
        await page.close()


# ── Parallel automation ───────────────────────────────────

async def run_parallel_attempt(
    url: str,
    fields: List[FormField],
    values: Dict[str, str],
    attempt: int,
    should_reload: bool,
    success_checks: dict,
    num_sessions: int,
    browser: Browser,
) -> AttemptResult:
    """
    Run `num_sessions` browser contexts in parallel.
    Return the first successful result; if all fail return the last.
    """
    contexts = [await browser.new_context() for _ in range(num_sessions)]
    tasks = [
        asyncio.create_task(
            run_single_attempt(url, fields, values, attempt, should_reload,
                               success_checks, ctx)
        )
        for ctx in contexts
    ]

    first_success: Optional[AttemptResult] = None
    results = []

    for coro in asyncio.as_completed(tasks):
        result = await coro
        results.append(result)
        if result.status == AttemptStatus.success and first_success is None:
            first_success = result
            # Cancel remaining workers
            for t in tasks:
                t.cancel()
            break

    for ctx in contexts:
        try:
            await ctx.close()
        except Exception:
            pass

    return first_success or results[-1]


# ── Main orchestrator ─────────────────────────────────────

async def run_automation(
    url: str,
    fields: List[FormField],
    values: Dict[str, str],
    settings,               # AutomationSettings
    job_id: str,
    log_fn,                 # async callable(job_id, msg, level)
    stop_event: asyncio.Event,
    on_attempt_done,        # async callable(AttemptResult)
) -> AttemptResult:
    """
    Top-level automation runner.
    Integrates the retry engine with Playwright browser management.
    """
    from services.retry_engine import RetryEngine, RetryConfig
    from models import RetryStrategy

    config = RetryConfig(
        max_attempts=settings.max_attempts,
        initial_delay=settings.initial_delay,
        strategy=settings.retry_strategy,
    )
    engine = RetryEngine(config)

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"])
        await log_fn(job_id, "Browser launched (Chromium headless)", "info")

        async def attempt_fn(attempt: int, reload: bool) -> AttemptResult:
            action = "Reloading + submitting" if reload else "Submitting"
            await log_fn(job_id, f"Attempt #{attempt} — {action}", "info")
            await log_fn(job_id, f"  ↳ Navigating to {url}", "default")
            await log_fn(job_id, f"  ↳ Filling {len(fields)} fields", "default")
            await log_fn(job_id, "  ↳ Locating submit button...", "default")

            result = await run_parallel_attempt(
                url=url,
                fields=fields,
                values=values,
                attempt=attempt,
                should_reload=reload,
                success_checks=settings.success_checks,
                num_sessions=settings.parallel_sessions,
                browser=browser,
            )

            level = "success" if result.status == AttemptStatus.success else \
                    "warn"    if result.status in (AttemptStatus.busy, AttemptStatus.limited) else \
                    "error"
            await log_fn(job_id, f"  → {result.message}", level)

            delay = engine.compute_delay(attempt)
            if result.status != AttemptStatus.success:
                await log_fn(job_id, f"  ⏱ Next retry in {delay:.0f}s", "warn")

            return result

        final = await engine.run(
            attempt_fn=attempt_fn,
            on_attempt=on_attempt_done,
            stop_event=stop_event,
        )

        await browser.close()

    if final.status == AttemptStatus.success:
        await log_fn(job_id, "━━━━ AUTOMATION COMPLETE — SUCCESS ━━━━", "success")
    else:
        await log_fn(job_id, "━━━━ AUTOMATION ENDED — MAX ATTEMPTS REACHED ━━━━", "error")

    return final
