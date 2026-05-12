"""FastAPI application entry point."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import api_router
from app.core.config import get_settings
from app.db.base import register_models


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

    @app.get("/healthz", tags=["meta"], summary="Liveness probe.")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(api_router)
    return app


app = create_app()
