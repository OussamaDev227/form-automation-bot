# Deploying FormBot to Render

This guide deploys 3 services using Render's Blueprint (render.yaml):

| Service             | Type           | Plan          | Cost/mo  |
|---------------------|----------------|---------------|----------|
| formbot-db          | PostgreSQL     | Free (90 days)| $0 → $7  |
| formbot-backend     | Web Service    | Standard      | $25      |
| formbot-frontend    | Static Site    | Free          | $0       |

> **Why Standard for the backend?**
> Playwright downloads a ~300 MB Chromium binary and needs >512 MB RAM.
> The free tier (512 MB, sleeps after 15 min) will crash on the first
> browser launch. The Standard plan gives you 2 GB RAM and always-on.

---

## Step 1 — Push your code to GitHub

```bash
git init
git add .
git commit -m "initial commit"
gh repo create formbot --private --push   # or use GitHub web UI
```

---

## Step 2 — Create a Render account

Go to https://render.com and sign up (free).

---

## Step 3 — Deploy with Blueprint (one click)

1. In Render Dashboard → click **New** → **Blueprint**
2. Connect your GitHub account if not already connected
3. Select your `formbot` repository
4. Render detects `render.yaml` automatically
5. Click **Apply** — Render creates all 3 services simultaneously

---

## Step 4 — Set the secret environment variables

After the Blueprint is created, Render auto-generates `API_KEY` but you
should verify all secrets are set:

### Backend service → Environment tab

| Variable        | Value                                      |
|-----------------|--------------------------------------------|
| `API_KEY`       | Auto-generated ✓ (copy this for Step 5)   |
| `DATABASE_URL`  | Auto-injected from formbot-db ✓            |
| `ALLOWED_ORIGINS` | `https://formbot-frontend.onrender.com` |
| `ENV`           | `production`                               |

### Frontend service → Environment tab

| Variable       | Value                                       |
|----------------|---------------------------------------------|
| `VITE_API_URL` | `https://formbot-backend.onrender.com`      |
| `VITE_API_KEY` | Same value as backend `API_KEY`             |

> After setting `VITE_API_KEY` and `VITE_API_URL`, click **Manual Deploy**
> on the frontend to rebuild with the new env vars baked in.

---

## Step 5 — Verify the deployment

```bash
# Health check
curl https://formbot-backend.onrender.com/health
# → {"status":"ok"}

# Test auth
curl https://formbot-backend.onrender.com/api/automation-status/test
# → {"detail":"Invalid or missing API key."}  ✓ (auth is working)

# Test with key
curl -H "X-API-Key: YOUR_API_KEY" \
     https://formbot-backend.onrender.com/health
# → {"status":"ok"}
```

Visit: **https://formbot-frontend.onrender.com**

---

## Important: Playwright on Render

The backend Dockerfile installs Playwright + Chromium during build.
This adds ~5 minutes to the first build. This is expected.

Render caches Docker layers, so subsequent deploys are fast.

If the build fails with "missing system dependencies":
- The Dockerfile already installs all required libs
- If it still fails, add this to `backend/Dockerfile` before playwright install:

```dockerfile
RUN apt-get update && apt-get install -y \
    libglib2.0-0 libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 \
    libcups2 libdrm2 libdbus-1-3 libxcb1 libxkbcommon0 libx11-6 \
    libxcomposite1 libxdamage1 libxext6 libxfixes3 libxrandr2 \
    libgbm1 libpango-1.0-0 libcairo2 libasound2 \
    --no-install-recommends && rm -rf /var/lib/apt/lists/*
```

---

## WebSocket on Render

Render web services accept inbound WebSocket connections from the public internet. One important rule: always use the `wss://` protocol for WebSocket connections over the public internet — if you use `ws://`, most clients will fail when Render responds with a 301 redirect to TLS.

Our `websocket.ts` already handles this:
```typescript
const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws'
```

Render does not enforce a maximum duration for WebSocket connections, but various factors can interrupt them (instance shutdowns, network issues, platform maintenance). Our reconnect logic in `websocket.ts` handles this with exponential backoff.

---

## Free Tier Limitations

The free tier on Render has some limitations, including PostgreSQL databases that expire after 90 days unless upgraded. For production applications, consider upgrading to a paid plan.

| Service    | Free limitation          | Paid fix         |
|------------|--------------------------|------------------|
| PostgreSQL | Expires after 90 days    | Starter ($7/mo)  |
| Backend    | Sleeps after 15 min idle | Standard ($25/mo)|
| Frontend   | None — always free       | —                |

---

## Custom Domain (optional)

In Render Dashboard → your service → Settings → Custom Domains:

```
formbot.yourdomain.com  →  formbot-frontend (static site)
api.yourdomain.com      →  formbot-backend  (web service)
```

Then update:
- `ALLOWED_ORIGINS=https://formbot.yourdomain.com` on backend
- `VITE_API_URL=https://api.yourdomain.com` on frontend
- Trigger a manual redeploy on both services

---

## Auto-deploy on git push

Once connected, every push to your main branch triggers a new deploy automatically. The frontend rebuilds and the backend redeploys with zero downtime.

---

## Estimated Monthly Cost

| Scenario      | Services                  | Cost/mo |
|---------------|---------------------------|---------|
| Development   | Free DB + Free backend*   | $0      |
| Production    | Starter DB + Standard API + Free frontend | $32 |
| High traffic  | Standard DB + Standard API (2×) + Free frontend | $75 |

*Free backend sleeps — not suitable for production automation jobs.
