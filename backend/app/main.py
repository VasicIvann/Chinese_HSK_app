"""FastAPI application entry point."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api.v1 import api_router
from app.core.config import get_settings
from app.db.base import register_models
from app.db.session import engine


def create_app() -> FastAPI:
    settings = get_settings()
    register_models()

    app = FastAPI(
        title="HSK API",
        description=(
            "REST API for the Chinese HSK Trainer. Handles authentication, vocabulary "
            "quizzes, FSRS-driven spaced repetition, and Claude-powered expression "
            "écrite correction."
        ),
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

    @app.get("/healthz", tags=["meta"], summary="Liveness probe (does not touch the database).")
    def healthz() -> dict[str, str]:
        # Pinged by Render's health check and by the keep-warm cron (every 10 min).
        # It must NOT query the database: Neon suspends its compute after 5 min idle,
        # and a DB ping every 10 min kept it awake most of the day (≈100 CU-hours a
        # month, the whole free allowance). Neon wakes up in < 1 s on the next real request.
        return {"status": "ok"}

    @app.get("/healthz/db", tags=["meta"], summary="Checks the database connection (wakes Neon up).")
    def healthz_db() -> dict[str, str]:
        # Manual checks only: never point a cron at this URL.
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            db_status = "ok"
        except Exception:  # noqa: BLE001
            db_status = "error"
        return {"status": "ok", "db": db_status}

    app.include_router(api_router)
    return app


app = create_app()
