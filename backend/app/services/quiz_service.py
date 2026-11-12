"""Read-side helpers for quizzes and entries."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Entry, Quiz, QuizEntry


def list_quizzes(db: Session, version: str | None = None) -> list[Quiz]:
    """Quizzes ordered by level; only those of `version` when given."""
    stmt = select(Quiz).order_by(Quiz.version.desc(), func.coalesce(Quiz.level, 9999), Quiz.title)
    if version is not None:
        stmt = stmt.where(Quiz.version == version)
    return list(db.execute(stmt).scalars().all())


def get_quiz_by_key(db: Session, key: str) -> Quiz | None:
    stmt = select(Quiz).where(Quiz.key == key)
    return db.execute(stmt).scalars().first()


def list_entries(db: Session, quiz_key: str, only_active: bool = True) -> list[Entry]:
    stmt = (
        select(Entry)
        .join(QuizEntry, QuizEntry.entry_id == Entry.id)
        .join(Quiz, Quiz.id == QuizEntry.quiz_id)
        .where(Quiz.key == quiz_key)
        .order_by(Entry.id)
    )
    if only_active:
        stmt = stmt.where(Entry.is_active.is_(True))
    return list(db.execute(stmt).scalars().all())
