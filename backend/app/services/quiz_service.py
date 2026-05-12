"""Read-side helpers for quizzes and entries."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Entry, Quiz


def list_quizzes(db: Session) -> list[Quiz]:
    stmt = select(Quiz).order_by(func.coalesce(Quiz.level, 9999), Quiz.title)
    return list(db.execute(stmt).scalars().all())


def get_quiz_by_key(db: Session, key: str) -> Quiz | None:
    stmt = select(Quiz).where(Quiz.key == key)
    return db.execute(stmt).scalars().first()


def list_entries(db: Session, quiz_key: str, only_active: bool = True) -> list[Entry]:
    stmt = select(Entry).join(Quiz).where(Quiz.key == quiz_key).order_by(Entry.id)
    if only_active:
        stmt = stmt.where(Entry.is_active.is_(True))
    return list(db.execute(stmt).scalars().all())
