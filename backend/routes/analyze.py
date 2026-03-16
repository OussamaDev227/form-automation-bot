"""
Route: /api/analyze-form
Accepts a URL, validates it (SSRF protection), and returns detected form fields.
"""

from fastapi import APIRouter, Depends, HTTPException
from models import AnalyzeRequest, AnalyzeResponse
from services.form_analyzer import analyze_form
from core.auth import require_api_key
from core.url_validator import validate_url

router = APIRouter()


@router.post(
    "/analyze-form",
    response_model=AnalyzeResponse,
    dependencies=[Depends(require_api_key)],
)
async def analyze_form_endpoint(body: AnalyzeRequest):
    # ── SSRF guard ────────────────────────────────────────
    try:
        safe_url = validate_url(body.url)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    try:
        result = await analyze_form(safe_url)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(exc)}")

    return AnalyzeResponse(
        url=safe_url,
        fields=result["fields"],
        captcha_detected=result["captcha_detected"],
        raw_html_snippet=result["raw_html_snippet"],
    )
