"""
CAPTCHA Detector Service
Scans a loaded Playwright page for known CAPTCHA patterns.
"""

from __future__ import annotations
from playwright.async_api import Page


CAPTCHA_PATTERNS = [
    # reCAPTCHA
    ".g-recaptcha",
    "#recaptcha",
    "iframe[src*='recaptcha']",
    "iframe[title*='reCAPTCHA']",
    "div[data-sitekey]",
    # hCaptcha
    ".h-captcha",
    "iframe[src*='hcaptcha']",
    "iframe[title*='hCaptcha']",
    # Cloudflare Turnstile
    ".cf-turnstile",
    "iframe[src*='challenges.cloudflare']",
    # Generic
    "[class*='captcha']",
    "[id*='captcha']",
    "img[src*='captcha']",
]


async def detect_captcha(page: Page) -> dict:
    """
    Check the page for CAPTCHA widgets.
    Returns:
        {
            "detected": bool,
            "type": str | None,   # "recaptcha" | "hcaptcha" | "turnstile" | "generic"
            "selector": str | None,
        }
    """
    for sel in CAPTCHA_PATTERNS:
        try:
            el = await page.query_selector(sel)
            if el:
                captcha_type = (
                    "recaptcha"  if "recaptcha"  in sel else
                    "hcaptcha"   if "hcaptcha"   in sel else
                    "turnstile"  if "cloudflare" in sel or "turnstile" in sel else
                    "generic"
                )
                return {"detected": True, "type": captcha_type, "selector": sel}
        except Exception:
            continue

    return {"detected": False, "type": None, "selector": None}
