"""
Authentication — API key guard.

Every protected endpoint adds `Depends(require_api_key)`.

Configuration
─────────────
Set the API_KEY environment variable before starting the server:

    export API_KEY="your-secret-key-here"

If API_KEY is not set the server refuses to start (see main.py startup check).

Clients must send the key in the header:

    X-API-Key: your-secret-key-here

Using `secrets.compare_digest` prevents timing-based enumeration attacks.
"""

import os
import secrets

from fastapi import HTTPException, Security, status
from fastapi.security.api_key import APIKeyHeader

_API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)

# Loaded once at import time; runtime changes require a restart.
_EXPECTED_KEY: str = os.environ.get("API_KEY", "")


async def require_api_key(api_key: str = Security(_API_KEY_HEADER)) -> str:
    """
    FastAPI dependency — raises 401 if the key is missing or wrong.
    Safe against timing attacks via constant-time comparison.
    """
    if not _EXPECTED_KEY:
        # Server misconfiguration — fail closed.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Server is not configured for authentication. Set API_KEY.",
        )

    if not api_key or not secrets.compare_digest(api_key, _EXPECTED_KEY):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key.",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    return api_key
