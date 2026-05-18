# Deployment

Target topology: FastAPI backend on **Render** (free tier), Next.js frontend on **Vercel** (Hobby), database on **Neon Postgres**, kept warm via **cron-job.org**. Recurring cost ≈ **€0** (excluding Anthropic API credits).

## Prerequisites

- GitHub repo pushed (`git push origin main`)
- A Neon Postgres project (free tier)
- An Anthropic Console account with a valid API key and some credits
- Free accounts: [Render](https://render.com), [Vercel](https://vercel.com), [cron-job.org](https://cron-job.org)

---

## 1. Backend — Render

### 1.1 Create the service

1. Render dashboard → **New** → **Blueprint**
2. Connect this GitHub repo, branch `main`
3. Render detects `render.yaml` at the root and proposes the `hsk-api` service
4. Click **Apply** → the service is created but won't start until env vars are set

### 1.2 Configure secrets

In the `hsk-api` service → **Environment** tab → add:

| Key | Value |
|---|---|
| `HSK_DATABASE_URL` | Neon Postgres connection string |
| `JWT_SECRET_KEY` | 64 random chars: `python -c "import secrets; print(secrets.token_urlsafe(64))"` |
| `ANTHROPIC_API_KEY` | Anthropic API key |
| `CORS_ORIGINS` | `<YOUR_VERCEL_URL>` (set the exact Vercel URL once the frontend is deployed) |
| `ALLOWED_REGISTRATION_EMAILS` | `<YOUR_EMAIL>` — invite-only mode, blocks other sign-ups to protect API spend |

Save changes → Render rebuilds.

### 1.3 Database migration

On a **fresh** database, the schema is created by Alembic:

```bash
cd backend
export HSK_DATABASE_URL="postgresql+psycopg://<USER>:<PASSWORD>@<HOST>/<DB>?sslmode=require"
alembic upgrade head
```

If the database **already contains the schema** (e.g. migrated from a previous app sharing the same DB), stamp it instead so Alembic records the baseline without re-running DDL:

```bash
alembic stamp head
```

### 1.4 Verify

Render assigns a URL with a random suffix: `https://hsk-api-<RANDOM>.onrender.com` (not `hsk-api.onrender.com`, which is likely taken). Find the exact URL in the Render dashboard → `hsk-api` service → "Available at your primary URL …".

Once the build is green:

- `<RENDER_URL>/healthz` → `{"status":"ok"}`
- `<RENDER_URL>/docs` → full Swagger UI

### 1.5 Keep-warm (cron-job.org)

Render's free tier sleeps the service after 15 min of inactivity. To keep it awake 24/7:

1. Create an account on [cron-job.org](https://cron-job.org) (free, no card)
2. **Create cronjob**:
   - URL: `<RENDER_URL>/healthz`
   - Schedule: every 10 minutes
   - Method: GET
3. Save.

---

## 2. Frontend — Vercel

### 2.1 Import the project

1. Vercel dashboard → **Add New** → **Project**
2. Select this repo
3. Vercel auto-detects Next.js
4. **Root directory**: `frontend`
5. Leave build settings on the Next.js preset

### 2.2 Environment variables

Before deploying, in **Environment Variables**:

| Key | Value |
|---|---|
| `NEXT_PUBLIC_API_URL` | `<RENDER_URL>` (exact backend URL, no trailing path) |

### 2.3 Deploy

Click **Deploy**. After 1–2 min the frontend is live at `<YOUR_VERCEL_URL>`.

### 2.4 Update CORS

Back on Render → `hsk-api` → Environment → set `CORS_ORIGINS` to the exact Vercel URL. Save → Render redeploys.

---

## 3. Smoke test in production

1. Open the Vercel URL
2. Create an account / sign in
3. Run an HSK1 quiz session
4. Open the Account dashboard → charts render
5. On a phone, open the same URL → "Add to home screen" → the PWA opens full-screen

---

## 4. Subsequent deployments

Push to `main` → **both** platforms auto-deploy:

- Vercel: ~1 min, zero-downtime
- Render: ~3 min, ~30 s swap downtime

GitHub Actions also runs the test suites on every push/PR (`.github/workflows/tests.yml`).

---

## 5. Expected monthly cost

| Service | Cost |
|---|---|
| Render free | €0 (750 h/month, keep-warm OK) |
| Vercel Hobby | €0 (100 GB bandwidth/month) |
| Neon free | €0 (0.5 GB storage, auto-suspend OK) |
| cron-job.org | €0 |
| Anthropic Haiku 4.5 | ≈ $0.003 / correction (prompt caching enabled) |

**Total: under $1/month with daily written-expression usage.**
