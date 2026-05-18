# HSK Trainer

A full-stack web app to prepare for the official **HSK** Chinese proficiency exams. It combines an **FSRS spaced-repetition scheduler** for vocabulary review and an **LLM-powered written-expression grader** (Anthropic Claude) that returns structured, actionable corrections.

Built as a real study tool *and* an engineering portfolio piece — decoupled FastAPI backend, typed Next.js frontend, streaming LLM integration, CI, and infra-as-code, all running on free tiers.

> Tech: **FastAPI · SQLAlchemy 2 · Alembic · Pydantic v2 · Postgres · JWT · Anthropic Claude (SSE streaming) · Next.js 16 · React 19 · TypeScript · TanStack Query · Tailwind v4 · Vitest · pytest · GitHub Actions**

---

## Why this project is interesting

| Area | What it demonstrates |
|---|---|
| **Spaced repetition** | Integration of [FSRS](https://github.com/open-spaced-repetition/py-fsrs) (modern ML-based scheduling) behind a clean service boundary, replacing a naive bucket heuristic. |
| **LLM engineering** | Claude Haiku 4.5 with **prompt caching**, **structured JSON output**, and **token-by-token SSE streaming** through FastAPI → consumed in the browser via a custom `fetch` + `ReadableStream` reader. |
| **API design** | Versioned REST API, auto-generated OpenAPI/Swagger, stateless JWT auth, per-user daily quota enforcement as a reusable dependency. |
| **Data layer** | SQLAlchemy 2.x models, Alembic migrations (baseline-stamped against an existing production DB), Postgres in prod / SQLite in tests. |
| **Frontend UX** | Optimistic UI on the quiz (next card renders in <50 ms, persistence happens in the background with retry), mobile-first responsive design, PWA-installable. |
| **Delivery** | GitHub Actions CI (pytest + vitest + build), `render.yaml` infra-as-code, zero-cost deployment topology. |

---

## Architecture

```
┌────────────────────────┐        HTTPS / JSON        ┌──────────────────────────┐
│  Next.js 16 (Vercel)   │  ───────────────────────▶  │  FastAPI (Render)        │
│  - App Router, RSC     │   Bearer JWT               │  - Pydantic v2 schemas   │
│  - TanStack Query      │  ◀───────────────────────  │  - SQLAlchemy 2 + Alembic│
│  - Optimistic quiz UI  │   SSE (text/event-stream)  │  - FSRS scheduler        │
│  - Tailwind v4         │                            │  - Claude (prompt cache) │
└────────────────────────┘                            └────────────┬─────────────┘
                                                                    │
                                                       ┌────────────▼─────────────┐
                                                       │  Postgres (Neon)         │
                                                       └──────────────────────────┘
```

The repo is a **monorepo**:

```
backend/    FastAPI service (Python 3.12)
  app/
    api/v1/        auth, quizzes, srs, mastery, expression, account
    services/      srs_service, llm_service, expression_service, ...
    models/        SQLAlchemy ORM
    schemas/       Pydantic v2 request/response models
  alembic/         migrations (0001 baseline)
  data/            HSK1-3 vocabulary CSVs + curated writing subjects
  tests/           pytest (Anthropic fully mocked)

frontend/   Next.js 16 app (TypeScript)
  app/             routes (landing, auth, comprehension, expression, account)
  components/      quiz, expression, charts, mastery, ui primitives
  lib/             typed API client, auth context, SSE consumer, FSRS hooks
  tests/           Vitest unit tests
```

---

## Features

- **FSRS-driven comprehension quiz** — the scheduler picks cards that are due, mixing in new vocabulary. Two modes: self-assessment and pinyin input. Keyboard shortcuts (1–4), progressive hints (pinyin → full solution), instant card transitions.
- **AI written-expression grading** — pick a curated subject, generate one with Claude, or write your own. Submit a short text in Chinese; Claude streams back a structured correction (score, corrected version, pinyin, translation, typed error list, strengths, next-step advice).
- **Closed feedback loop** — vocabulary Claude flags as misused is automatically re-queued into the FSRS review pile.
- **Dashboard** — mastery distribution donut, 90-day activity heatmap, quiz & expression progression curves, and browsable lists of mastered / known / to-review words.
- **Cross-device** — JWT auth, shared Postgres, PWA "add to home screen" on mobile.

---

## Local development

Prerequisites: **Python 3.12**, **Node 20+**, a Postgres URL (or use the SQLite fallback), an [Anthropic API key](https://console.anthropic.com/).

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\Activate.ps1
pip install -e ".[dev]"
cp .env.example .env                                 # fill HSK_DATABASE_URL, JWT_SECRET_KEY, ANTHROPIC_API_KEY
alembic upgrade head                                 # creates the schema on a fresh DB
uvicorn app.main:app --reload --port 8000
```

API docs: <http://localhost:8000/docs>

### Frontend

```bash
cd frontend
npm install
cp .env.local.example .env.local                     # NEXT_PUBLIC_API_URL=http://localhost:8000
npm run dev
```

App: <http://localhost:3000>

---

## Tests

```bash
# Backend — pytest, no network (Anthropic mocked)
cd backend && pytest

# Frontend — Vitest unit tests
cd frontend && npm test
```

CI runs both suites plus a production build on every push and PR (`.github/workflows/tests.yml`).

---

## Deployment

Backend on Render (free tier, kept warm via a 10-min cron ping), frontend on Vercel, database on Neon — total recurring cost ≈ €0. Full step-by-step in [DEPLOYMENT.md](DEPLOYMENT.md), with `render.yaml` as infra-as-code.

---

## License

[MIT](LICENSE)
