"""
Pydantic models shared across the application.
"""

from __future__ import annotations
from enum import Enum
from typing import Any, List, Optional
from pydantic import BaseModel, HttpUrl


# ── Enums ─────────────────────────────────────────────────

class RetryStrategy(str, Enum):
    resubmit = "resubmit"
    reload   = "reload"
    hybrid   = "hybrid"


class JobStatus(str, Enum):
    created   = "created"
    analyzing = "analyzing"
    ready     = "ready"
    running   = "running"
    success   = "success"
    failed    = "failed"
    stopped   = "stopped"


class AttemptStatus(str, Enum):
    success  = "success"
    failed   = "failed"
    retry    = "retry"
    busy     = "busy"   # 503
    limited  = "limited" # 429
    captcha  = "captcha"


# ── Form field models ─────────────────────────────────────

class FieldOption(BaseModel):
    value: str
    label: str


class FormField(BaseModel):
    id:          Optional[str] = None
    name:        Optional[str] = None
    type:        str                        # text, email, password, select, radio, checkbox …
    label:       Optional[str] = None
    placeholder: Optional[str] = None
    required:    bool = False
    default:     Optional[str] = None
    options:     Optional[List[Any]] = None  # FieldOption list or str list


# ── Request / Response models ─────────────────────────────

class AnalyzeRequest(BaseModel):
    url: str


class AnalyzeResponse(BaseModel):
    url:    str
    fields: List[FormField]
    captcha_detected: bool = False
    raw_html_snippet: Optional[str] = None


class AutomationSettings(BaseModel):
    max_attempts:      int = 10
    initial_delay:     float = 2.0
    retry_strategy:    RetryStrategy = RetryStrategy.hybrid
    parallel_sessions: int = 3
    direct_api_mode:   bool = False

    success_checks: dict = {
        "url_redirect":      True,
        "success_message":   True,
        "form_disappear":    True,
        "session_cookie":    True,
        "api_response_200":  True,
    }


class StartAutomationRequest(BaseModel):
    url:      str
    fields:   List[FormField]
    values:   dict                  # field name → user-supplied value
    settings: AutomationSettings = AutomationSettings()


class AttemptRecord(BaseModel):
    attempt_number: int
    status:         AttemptStatus
    message:        str
    delay_used:     float
    response_time:  Optional[float] = None
    http_status:    Optional[int]   = None


class AutomationStatusResponse(BaseModel):
    job_id:   str
    status:   JobStatus
    attempts: List[AttemptRecord] = []
    message:  Optional[str] = None


class LogEntry(BaseModel):
    job_id:    str
    seq:       int
    level:     str   # info | success | warn | error | default
    message:   str
    timestamp: str


class NetworkRequest(BaseModel):
    method:   str
    endpoint: str
    payload:  Optional[dict] = None
    status:   Optional[int]  = None
    time_ms:  Optional[float] = None
