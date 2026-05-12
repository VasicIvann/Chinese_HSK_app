# HSK API

FastAPI backend for the Chinese HSK Trainer app. Provides authenticated REST endpoints for vocabulary quizzes, FSRS-driven spaced repetition, and Claude-powered expression écrite correction.

## Stack

- FastAPI + Pydantic v2
- SQLAlchemy 2.x + Alembic migrations
- Postgres (Neon) in production, SQLite for tests
- JWT auth (Authorization: Bearer)
- Anthropic Claude Haiku 4.5 for expression écrite correction

## Local setup

```powershell
# From repo root
.\.venv\Scripts\Activate.ps1
cd backend
cp .env.example .env  # fill HSK_DATABASE_URL, JWT_SECRET_KEY, ANTHROPIC_API_KEY

# Apply migrations
alembic upgrade head

# Run the dev server
uvicorn app.main:app --reload --port 8000
```

OpenAPI docs: http://localhost:8000/docs

## Tests

```powershell
pytest
```

Tests use a temporary SQLite DB and never touch the production Neon instance.

## Deploy on Render free tier

1. New Web Service → connect this repo → root directory `backend/`
2. Build command: `pip install -e .`
3. Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
4. Env vars: copy from `.env.example`
5. Set up a cron-job.org ping on `GET /healthz` every 10 min to prevent sleep

## Alembic baseline

The initial migration `0001_baseline` describes the schema that already exists in the Neon database (created by the Streamlit app via lightweight `ALTER TABLE`). The first time you connect Alembic to a non-empty production DB, run:

```powershell
alembic stamp head
```

This marks the DB as already at the current revision without re-running CREATE TABLE statements. Future schema changes will use proper `alembic revision --autogenerate` + `alembic upgrade head`.
