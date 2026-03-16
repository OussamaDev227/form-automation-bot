# FormBot — Universal Form Automation Platform

A full-stack RPA tool: analyze any web form, fill it, and submit it with smart
retry strategies, parallel sessions, and real-time log streaming.

---

## Quick Start

### 1. Clone and configure

```bash
git clone <repo>
cd form-automation-bot
cp .env.example .env
```

Edit `.env` — at minimum set these two:

```env
API_KEY=<run: openssl rand -hex 32>
DB_PASSWORD=<run: openssl rand -hex 16>
```

### 2. Launch

```bash
docker-compose up --build
```

| Service  | URL                        |
|----------|----------------------------|
| Frontend | http://localhost:5173      |
| Backend  | http://localhost:8000      |
| API docs | http://localhost:8000/docs |

---

## What Was Fixed (4 Blockers)

| Blocker | Fix |
|---------|-----|
| No persistent storage | PostgreSQL via asyncpg — jobs, attempts, logs all survive restarts |
| SSRF on URL input | `core/url_validator.py` — blocks private IPs, loopback, bad schemes |
| No authentication | `core/auth.py` — X-API-Key header required on every endpoint |
| Hardcoded CORS * | `ALLOWED_ORIGINS` env var — defaults to localhost only |

Plus: WS reconnect logic, concurrency semaphore, React ErrorBoundary, log persistence.

---

## Security Model

| Threat | Fix |
|--------|-----|
| Unauthenticated access | X-API-Key header required on every endpoint |
| SSRF via URL input | Blocks private IPs + non-http(s) schemes |
| CORS abuse | ALLOWED_ORIGINS env var; defaults to localhost only |
| Browser OOM | asyncio.Semaphore(MAX_CONCURRENT_JOBS) caps sessions |
| WS auth | api_key query param validated server-side |
| Log loss on restart | All logs persisted to PostgreSQL job_logs table |

---

## API Reference

All endpoints require the header: X-API-Key: <your key>

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/analyze-form | Analyze a URL's form fields |
| POST | /api/start-automation | Start an automation job |
| POST | /api/stop-automation/{job_id} | Stop a running job |
| GET | /api/automation-status/{job_id} | Poll job status + attempts |
| GET | /api/automation-logs/{job_id} | Fetch persisted logs (REST) |
| WS | /ws/logs/{job_id}?api_key=<key> | Real-time log stream |
| GET | /health | Health check (no auth) |

---

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| API_KEY | Yes | — | Auth key for all API endpoints |
| DB_PASSWORD | Yes | formbot_dev | PostgreSQL password |
| DATABASE_URL | No | auto-built | Full DSN (overrides DB_PASSWORD) |
| ALLOWED_ORIGINS | Prod | http://localhost:5173 | Comma-separated CORS origins |
| ENV | No | development | Set to production to hide /docs |
| MAX_CONCURRENT_JOBS | No | 5 | Max simultaneous Playwright browsers |
| VITE_API_KEY | Yes | same as API_KEY | Injected into frontend at build |
| VITE_API_URL | No | (same-origin) | Backend URL for standalone frontend |

---

## Production Deployment Checklist

- Set API_KEY to a random 32-byte hex string
- Set DB_PASSWORD to a strong password
- Set ALLOWED_ORIGINS to your exact frontend domain
- Set ENV=production (disables /docs)
- Remove ports: 5432:5432 from db service in compose
- Put services behind TLS reverse proxy (nginx / Caddy)
- Set up automated PostgreSQL backups
- Consider a managed PG service (RDS, Supabase, Neon) for durability

---

## License

MIT
