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

    @app.get("/healthz", tags=["meta"], summary="Liveness probe; also pings the database.")
    def healthz() -> dict[str, str]:
        # Touching the DB keeps Neon awake when the keep-warm cron pings this URL.
        # Always 200: Render uses this path as its health check, and a slow Neon
        # wake-up must not make a deploy fail. The DB state is reported in "db".
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
