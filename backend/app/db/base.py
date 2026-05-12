"""Declarative base + import-once registration of all models for Alembic."""

from __future__ import annotations

from sqlalchemy.orm import declarative_base

Base = declarative_base()


def register_models() -> None:
    """Force-import all model modules so Alembic sees every table."""
    from app.models import expression, mastery, quiz, user  # noqa: F401
