# Free Deployment Guide — Railway + Neon + Vercel

Total cost: $0/month

| Service  | Provider | Free Limits                          |
|----------|----------|--------------------------------------|
| Backend  | Railway  | $5 credit/month (~500 hrs container) |
| Database | Neon     | 0.5 GB PostgreSQL, never expires     |
| Frontend | Vercel   | Unlimited static hosting             |

---

## Overview

```
GitHub repo
    │
    ├── /backend  ──▶  Railway  (FastAPI + Playwright, Docker)
    │                      │
    │                      └──▶  Neon  (PostgreSQL, serverless)
    │
    └── /frontend ──▶  Vercel  (React/Vite static site)
```

---

## Step 1 — Push your code to GitHub

```bash
cd form-automation-bot
git init
git add .
git commit -m "initial commit"

# Create a new GitHub repo (use GitHub web UI or CLI):
gh repo create formbot --private --push --source=.
```

---

## Step 2 — Set up Neon (free PostgreSQL)

1. Go to **https://neon.tech** → Sign up (no credit card needed)
2. Click **New Project** → name it `formbot` → click **Create Project**
3. Copy the **Connection string** — it looks like:
   ```
   postgresql://username:password@ep-xxx.us-east-2.aws.neon.tech/neondb?sslmode=require
   ```
4. Save it — you'll use this as `DATABASE_URL` in Railway

> Neon's free tier: 0.5 GB storage, never expires, scales to zero when idle.

---

## Step 3 — Deploy backend on Railway

1. Go to **https://railway.app** → Sign up with GitHub (no credit card)
2. Click **New Project** → **Deploy from GitHub repo**
3. Select your `formbot` repo
4. Railway detects `backend/railway.json` → set the **Root Directory** to `/backend`
5. Go to **Variables** tab and add:

   | Variable              | Value                                      |
   |-----------------------|--------------------------------------------|
   | `API_KEY`             | Run: `openssl rand -hex 32` → paste result |
   | `DATABASE_URL`        | Your Neon connection string from Step 2    |
   | `ALLOWED_ORIGINS`     | `https://formbot.vercel.app` (update after Step 4) |
   | `ENV`                 | `production`                               |
   | `MAX_CONCURRENT_JOBS` | `2`  (conservative for 512 MB RAM)         |
   | `PORT`                | `8000`                                     |

6. Click **Deploy** — Railway builds your Docker image (takes ~5 min first time)
7. After deploy, go to **Settings** → **Networking** → **Generate Domain**
   - You get a URL like: `https://formbot-backend.up.railway.app`
8. Copy this URL — you'll need it for Step 4

---

## Step 4 — Deploy frontend on Vercel

1. Go to **https://vercel.com** → Sign up with GitHub (free)
2. Click **Add New Project** → Import your `formbot` repo
3. Set **Root Directory** to `frontend`
4. Under **Environment Variables**, add:

   | Variable       | Value                                          |
   |----------------|------------------------------------------------|
   | `VITE_API_URL` | `https://formbot-backend.up.railway.app`       |
   | `VITE_API_KEY` | Same value as `API_KEY` in Railway             |

5. Click **Deploy** — Vercel builds your Vite app (~1 min)
6. You get a URL like: `https://formbot.vercel.app`

---

## Step 5 — Update CORS on Railway

Now that you have your Vercel URL, go back to Railway:

1. Variables tab → update `ALLOWED_ORIGINS` to your Vercel URL:
   ```
   ALLOWED_ORIGINS=https://formbot.vercel.app
   ```
2. Railway auto-redeploys

---

## Step 6 — Verify everything works

```bash
# Replace with your actual Railway URL and API key
BACKEND=https://formbot-backend.up.railway.app
KEY=your-api-key-here

# Health check (no auth needed)
curl $BACKEND/health
# → {"status":"ok"}

# Auth check
curl -H "X-API-Key: $KEY" $BACKEND/health
# → {"status":"ok"}

# Test SSRF protection
curl -X POST $BACKEND/api/analyze-form \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $KEY" \
  -d '{"url":"http://localhost"}'
# → {"detail":"Hostname 'localhost' is not allowed."}  ✓
```

Then visit your Vercel URL and try analyzing a real form!

---

## Important: Playwright on 512 MB RAM

Railway's free tier gives you 512 MB RAM. Playwright + Chromium needs ~280–350 MB.
This means you have very little headroom.

**To make it work reliably, set `MAX_CONCURRENT_JOBS=2` (already set in Step 3).**

If you see OOM (Out of Memory) errors in Railway logs:
1. Set `MAX_CONCURRENT_JOBS=1`
2. In `backend/services/form_analyzer.py`, add `args=["--no-sandbox", "--disable-dev-shm-usage"]` to `playwright.chromium.launch()`

The launch args are already in the Dockerfile environment — this is a known
workaround for low-memory containers.

---

## Auto-deploy on git push

Both Railway and Vercel redeploy automatically on every push to your main branch.

```bash
git add .
git commit -m "update"
git push
# Both services redeploy automatically
```

---

## Free tier limits summary

### Railway ($5 credit/month)
- ~500 hours of a 512 MB / 0.5 vCPU container per month
- If you use it lightly (not 24/7), the $5 credit covers everything
- If you exceed $5, Railway pauses your service until next month
- Check usage: Railway Dashboard → Usage tab

### Neon (always free)
- 0.5 GB storage per project
- 100 compute-hours/month (scales to zero when idle — resets monthly)
- No credit card, never expires
- If you hit the storage limit: delete old job logs in the `job_logs` table

### Vercel (always free)
- Unlimited static site deployments
- 100 GB bandwidth/month
- No limits for this use case

---

## Tips to stay within free limits

1. **Add a log cleanup job** — old rows in `job_logs` and `attempts` accumulate fast.
   Run this monthly:
   ```sql
   DELETE FROM job_logs  WHERE created_at < NOW() - INTERVAL '30 days';
   DELETE FROM attempts  WHERE created_at < NOW() - INTERVAL '30 days';
   DELETE FROM jobs      WHERE created_at < NOW() - INTERVAL '30 days'
                           AND status IN ('success','failed','stopped');
   ```

2. **Don't run automations in parallel** — keep `MAX_CONCURRENT_JOBS=1` or `2`
   to avoid OOM on Railway's 512 MB tier.

3. **Use Neon's scale-to-zero** — it's on by default. Your database pauses after
   5 minutes of inactivity, saving compute hours.

---

## Upgrading later

If you need more resources:
- Railway Hobby plan: $5/month flat fee + usage → no credit limits, more RAM available
- Neon Launch: $19/month → 10 GB storage, 300 compute-hours
- Vercel Pro: $20/month → if you need team features (not needed for this project)
