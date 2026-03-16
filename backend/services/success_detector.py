"""
Success Detector Service
Applies multiple heuristics to determine whether a form submission succeeded.
"""

from __future__ import annotations
import re
from typing import Optional
from playwright.async_api import Page


SUCCESS_KEYWORDS = [
    # English
    "success", "thank you", "thanks", "confirmed", "registered",
    "welcome", "account created", "verification", "check your email",
    # French
    "succès", "merci", "confirmé", "inscrit", "bienvenue",
    # Arabic
    "تم", "شكرًا", "نجاح", "مرحبًا", "تسجيل",
]

FAILURE_KEYWORDS = [
    "error", "invalid", "failed", "wrong", "incorrect",
    "erreur", "invalide", "خطأ", "غير صحيح",
]

DASHBOARD_SELECTORS = [
    "#dashboard", ".dashboard", "#home", ".home-page",
    "[data-page='home']", ".user-profile", "#user-panel",
]


class SuccessResult:
    __slots__ = ("succeeded", "reason", "http_status")

    def __init__(self, succeeded: bool, reason: str, http_status: Optional[int] = None):
        self.succeeded   = succeeded
        self.reason      = reason
        self.http_status = http_status


async def detect_success(
    page: Page,
    original_url: str,
    response_status: Optional[int] = None,
    checks: Optional[dict] = None,
) -> SuccessResult:
    """
    Run all configured success heuristics.
    Returns a SuccessResult with succeeded=True on first positive signal.
    """
    if checks is None:
        checks = {k: True for k in [
            "url_redirect", "success_message", "form_disappear",
            "session_cookie", "api_response_200",
        ]}

    # 1. HTTP response code
    if checks.get("api_response_200") and response_status in (200, 201, 204):
        current_url = page.url
        if current_url != original_url:
            return SuccessResult(True, f"HTTP {response_status} + URL changed", response_status)

    # 2. URL redirect
    if checks.get("url_redirect"):
        current_url = page.url
        if current_url != original_url:
            # Heuristic: new URL suggests a dashboard/confirmation page
            positive_paths = ["dashboard", "home", "welcome", "confirm", "success",
                              "merci", "تم", "شكر"]
            if any(p in current_url.lower() for p in positive_paths):
                return SuccessResult(True, f"Redirected to: {current_url}")

    # 3. Success message in page text
    if checks.get("success_message"):
        try:
            body_text = (await page.inner_text("body")).lower()
            for kw in SUCCESS_KEYWORDS:
                if kw in body_text:
                    # Make sure it's not also showing an error
                    if not any(fk in body_text for fk in FAILURE_KEYWORDS):
                        return SuccessResult(True, f'Success keyword found: "{kw}"')
        except Exception:
            pass

    # 4. Form disappeared
    if checks.get("form_disappear"):
        try:
            form_count = len(await page.query_selector_all("form"))
            if form_count == 0:
                return SuccessResult(True, "All forms disappeared from DOM")
        except Exception:
            pass

    # 5. Dashboard / post-login elements appeared
    for sel in DASHBOARD_SELECTORS:
        try:
            el = await page.query_selector(sel)
            if el:
                return SuccessResult(True, f"Dashboard element found: {sel}")
        except Exception:
            pass

    # 6. Session cookie created
    if checks.get("session_cookie"):
        try:
            cookies = await page.context.cookies()
            session_names = {"session", "sessionid", "auth_token", "jwt",
                             "access_token", "token", "sid"}
            for c in cookies:
                if c["name"].lower() in session_names:
                    return SuccessResult(True, f"Session cookie set: {c['name']}")
        except Exception:
            pass

    return SuccessResult(False, "No success signals detected")
