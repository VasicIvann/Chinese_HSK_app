# HSK API

FastAPI backend for the HSK Trainer. Authenticated REST endpoints for vocabulary
quizzes, FSRS-driven spaced repetition, and Claude-powered written-expression
grading.

## Stack

- FastAPI + Pydantic v2
- SQLAlchemy 2.x + Alembic migrations
- Postgres in production, SQLite in tests
- Stateless JWT auth (`Authorization: Bearer`)
- Anthropic Claude Haiku 4.5 (prompt caching + SSE streaming)

## Local setup

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\Activate.ps1
pip install -e ".[dev]"
cp .env.example .env                                 # HSK_DATABASE_URL, JWT_SECRET_KEY, ANTHROPIC_API_KEY
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

OpenAPI docs: <http://localhost:8000/docs>

## Tests

```bash
pytest
```

Tests run against a temporary SQLite database and mock the Anthropic client —
no network calls, no production data touched.

## Deploy on Render

1. New Web Service → connect this repo → root directory `backend/`
2. Build command: `pip install -e .`
3. Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
4. Env vars: copy the keys from `.env.example`
5. Add a cron-job.org GET ping on `/healthz` every 10 min to prevent free-tier sleep

See [../DEPLOYMENT.md](../DEPLOYMENT.md) for the full guide.

## Alembic baseline

`0001_baseline` describes the full schema. On a fresh database, `alembic upgrade
head` creates every table. If you connect Alembic to a database that **already**
has the schema, stamp it instead so the baseline is recorded without re-running
the DDL:

```bash
alembic stamp head
```

Future schema changes use `alembic revision --autogenerate` + `alembic upgrade head`.

## `data/`

`hsk1.csv` / `hsk2.csv` / `hsk3.csv` are the source HSK 1–3 vocabulary datasets.
`expression_subjects.json` is the curated pool of writing prompts per level.
