"""
Form Analyzer Service
Launches a Playwright browser, loads the target URL, and extracts
all form fields with their attributes, labels, and options.
"""

from __future__ import annotations
import asyncio
from typing import List, Optional

from playwright.async_api import async_playwright, Page, ElementHandle

from models import FormField, FieldOption


# ── Helpers ───────────────────────────────────────────────

async def _get_label_text(page: Page, field: ElementHandle) -> Optional[str]:
    """Find the <label> associated with a field (for= attribute or wrapping label)."""
    field_id = await field.get_attribute("id")
    if field_id:
        label_el = await page.query_selector(f'label[for="{field_id}"]')
        if label_el:
            return (await label_el.inner_text()).strip()

    # Try closest ancestor label
    try:
        text = await field.evaluate(
            """el => {
                const lbl = el.closest('label');
                return lbl ? lbl.innerText.trim() : null;
            }"""
        )
        return text or None
    except Exception:
        return None


async def _extract_options(field: ElementHandle) -> Optional[List]:
    """Extract <option> or radio siblings."""
    tag = await field.evaluate("el => el.tagName.toLowerCase()")

    if tag == "select":
        raw = await field.evaluate(
            """el => Array.from(el.options).map(o => ({value: o.value, label: o.text.trim()}))"""
        )
        return raw

    if tag == "input":
        input_type = await field.get_attribute("type") or ""
        if input_type == "radio":
            name = await field.get_attribute("name") or ""
            raw = await field.evaluate(
                f"""() => {{
                    const radios = document.querySelectorAll('input[type="radio"][name="{name}"]');
                    return Array.from(radios).map(r => ({{
                        value: r.value,
                        label: r.labels?.[0]?.innerText?.trim() || r.value
                    }}));
                }}"""
            )
            return raw

    return None


async def _field_to_model(page: Page, el: ElementHandle) -> Optional[FormField]:
    """Convert a single DOM element to a FormField model."""
    try:
        tag   = await el.evaluate("e => e.tagName.toLowerCase()")
        ftype = (await el.get_attribute("type") or tag).lower()

        # Skip hidden, submit, button, image, reset
        if ftype in ("submit", "button", "image", "reset", "hidden"):
            return None

        field_id    = await el.get_attribute("id")
        name        = await el.get_attribute("name")
        placeholder = await el.get_attribute("placeholder")
        required    = await el.get_attribute("required") is not None
        default_val = await el.get_attribute("value")
        label_text  = await _get_label_text(page, el)
        options     = await _extract_options(el)

        # Normalise type for <textarea> and <select>
        if tag == "textarea":
            ftype = "textarea"
        elif tag == "select":
            ftype = "select"

        return FormField(
            id=field_id,
            name=name or field_id,
            type=ftype,
            label=label_text or name or field_id or ftype,
            placeholder=placeholder,
            required=required,
            default=default_val,
            options=options,
        )
    except Exception:
        return None


# ── Public API ────────────────────────────────────────────

async def analyze_form(url: str) -> dict:
    """
    Launch Playwright, load the URL, and extract all form fields.

    Returns:
        {
            "fields": List[FormField],
            "captcha_detected": bool,
            "raw_html_snippet": str | None,
        }
    """
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"])
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        )
        page = await context.new_page()

        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=30_000)
            await page.wait_for_load_state("networkidle", timeout=10_000)
        except Exception:
            # Proceed even if networkidle times out
            pass

        # ── Detect CAPTCHA ────────────────────────────────
        captcha_detected = False
        captcha_selectors = [
            ".g-recaptcha", "#recaptcha", "iframe[src*='recaptcha']",
            ".h-captcha",   "iframe[src*='hcaptcha']",
        ]
        for sel in captcha_selectors:
            el = await page.query_selector(sel)
            if el:
                captcha_detected = True
                break

        # ── Extract all interactive form elements ─────────
        selectors = [
            "input[type='text']",    "input[type='email']",
            "input[type='password']","input[type='number']",
            "input[type='tel']",     "input[type='url']",
            "input[type='date']",    "input[type='radio']",
            "input[type='checkbox']","input[type='file']",
            "input[type='hidden']",  "select",  "textarea",
        ]

        fields: List[FormField] = []
        seen_names: set = set()

        for sel in selectors:
            elements = await page.query_selector_all(sel)
            for el in elements:
                field = await _field_to_model(page, el)
                if field is None:
                    continue
                # De-duplicate radio groups by name
                if field.type == "radio":
                    if field.name in seen_names:
                        continue
                    seen_names.add(field.name)
                fields.append(field)

        # Raw snippet for debugging
        snippet = None
        form_el = await page.query_selector("form")
        if form_el:
            try:
                snippet = await form_el.inner_html()
                snippet = snippet[:2000]  # cap to 2 KB
            except Exception:
                pass

        await browser.close()

        return {
            "fields": fields,
            "captcha_detected": captcha_detected,
            "raw_html_snippet": snippet,
        }
