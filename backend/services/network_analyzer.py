"""
Network Analyzer Service
Intercepts network requests during form submission to discover
the underlying API endpoint and payload structure.
Enables "Direct API Mode" — bypassing the browser entirely.
"""

from __future__ import annotations
import json
import urllib.parse
from typing import List, Optional

from playwright.async_api import async_playwright, Request, Response

from models import NetworkRequest


# ── Intercept network traffic ─────────────────────────────

async def capture_form_requests(url: str, timeout: float = 20.0) -> List[NetworkRequest]:
    """
    Load the page, wait for network activity, and return
    a list of API requests captured (POST + XHR/fetch).
    """
    captured: List[NetworkRequest] = []

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context()
        page    = await context.new_page()

        async def on_request(request: Request):
            if request.method in ("POST", "PUT", "PATCH"):
                try:
                    post_data = request.post_data
                    payload: Optional[dict] = None
                    if post_data:
                        try:
                            payload = json.loads(post_data)
                        except Exception:
                            # Try form-encoded
                            try:
                                payload = dict(urllib.parse.parse_qsl(post_data))
                            except Exception:
                                payload = {"raw": post_data[:200]}

                    captured.append(NetworkRequest(
                        method=request.method,
                        endpoint=_path_from_url(request.url),
                        payload=payload,
                    ))
                except Exception:
                    pass

        async def on_response(response: Response):
            for req in captured:
                if req.endpoint in response.url and req.status is None:
                    req.status = response.status

        page.on("request",  on_request)
        page.on("response", on_response)

        try:
            await page.goto(url, wait_until="networkidle", timeout=int(timeout * 1000))
        except Exception:
            pass

        await browser.close()

    return captured


def _path_from_url(full_url: str) -> str:
    parsed = urllib.parse.urlparse(full_url)
    return parsed.path + (("?" + parsed.query) if parsed.query else "")


# ── Direct API Mode ───────────────────────────────────────

async def direct_api_submit(
    endpoint: str,
    method: str,
    payload: dict,
    headers: Optional[dict] = None,
) -> dict:
    """
    Submit form data directly to the detected API endpoint,
    skipping the Playwright browser.
    Returns {"status": int, "body": str}.
    """
    import aiohttp

    default_headers = {
        "Content-Type": "application/json",
        "User-Agent":   "Mozilla/5.0 FormBot/1.0",
    }
    if headers:
        default_headers.update(headers)

    async with aiohttp.ClientSession() as session:
        method_fn = getattr(session, method.lower(), session.post)
        async with method_fn(endpoint, json=payload, headers=default_headers) as resp:
            body = await resp.text()
            return {"status": resp.status, "body": body[:500]}
