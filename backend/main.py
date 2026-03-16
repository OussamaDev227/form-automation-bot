"""
Form Automation Bot — FastAPI Backend
Entry point: DB init, CORS, routers, WebSocket log streaming.
"""

import asyncio
import os
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from routes.analyze import router as analyze_router
from routes.automation import router as automation_router
from routes.logs import router as logs_router
from services.log_broadcaster import broadcaster
from services.database import init_db, close_db


# ── Startup safety checks ─────────────────────────────────

def _check_env() -> None:
    """Refuse to start if critical env vars are missing."""
    missing = []
    if not os.environ.get("API_KEY"):
        missing.append("API_KEY")
    if missing:
        print(
            f"[FATAL] Missing required environment variables: {', '.join(missing)}\n"
            f"        Set them before starting the server.\n"
            f"        Example:  export API_KEY=$(openssl rand -hex 32)",
            file=sys.stderr,
        )
        sys.exit(1)


_check_env()


# ── Application lifespan ──────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield
    await close_db()


# ── App ───────────────────────────────────────────────────

app = FastAPI(
    title="Form Automation Bot API",
    version="1.0.0",
    lifespan=lifespan,
    # Hide docs in production by checking env
    docs_url="/docs" if os.environ.get("ENV") != "production" else None,
    redoc_url=None,
)

# ── CORS (Blocker 4 fix) ──────────────────────────────────
# Read allowed origins from env; defaults to localhost for local dev.
# In production set:  ALLOWED_ORIGINS=https://yourdomain.com
_raw_origins = os.environ.get("ALLOWED_ORIGINS", "http://localhost:5173")
ALLOWED_ORIGINS = [o.strip() for o in _raw_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["X-API-Key", "Content-Type"],
)

# ── Routers ───────────────────────────────────────────────
app.include_router(analyze_router,    prefix="/api", tags=["Form Analysis"])
app.include_router(automation_router, prefix="/api", tags=["Automation"])
app.include_router(logs_router,       prefix="/api", tags=["Logs"])


# ── WebSocket: real-time log streaming ────────────────────
@app.websocket("/ws/logs/{job_id}")
async def websocket_logs(websocket: WebSocket, job_id: str):
    # Validate API key via query param for WS (headers unavailable in browser WS)
    import secrets
    expected = os.environ.get("API_KEY", "")
    token = websocket.query_params.get("api_key", "")
    if not expected or not secrets.compare_digest(token, expected):
        await websocket.close(code=4401)
        return

    await websocket.accept()
    queue: asyncio.Queue = asyncio.Queue()
    broadcaster.subscribe(job_id, queue)
    try:
        while True:
            msg = await queue.get()
            await websocket.send_json(msg)
    except WebSocketDisconnect:
        broadcaster.unsubscribe(job_id, queue)


@app.get("/health")
async def health():
    return {"status": "ok"}



if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
