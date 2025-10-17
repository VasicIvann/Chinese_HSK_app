"""High level data access helpers for quizzes."""

from __future__ import annotations

import random
from typing import Dict, List, Optional

from sqlalchemy import func, select

from db import get_session
from models import Entry, Quiz


def list_quizzes() -> List[Dict[str, Optional[str]]]:
    """Return all available quizzes ordered by level then title."""
    stmt = select(Quiz).order_by(func.coalesce(Quiz.level, 9999), Quiz.title)
    with get_session() as session:
        result = session.execute(stmt)
        quizzes = []
        for quiz in result.scalars():
            quizzes.append(
                {
                    "id": quiz.id,
                    "key": quiz.key,
                    "title": quiz.title,
                    "description": quiz.description,
                    "level": quiz.level,
                }
            )
        return quizzes


def get_quiz_by_key(key: str) -> Optional[Dict[str, Optional[str]]]:
    """Return a quiz metadata dictionary."""
    stmt = select(Quiz).where(Quiz.key == key)
    with get_session() as session:
        quiz = session.execute(stmt).scalars().first()
        if quiz is None:
            return None
        return {
            "id": quiz.id,
            "key": quiz.key,
            "title": quiz.title,
            "description": quiz.description,
            "level": quiz.level,
        }


def get_entries(quiz_key: str, only_active: bool = True) -> List[Dict[str, str]]:
    """Return all entries for the given quiz as plain dictionaries."""
    stmt = (
        select(Entry)
        .join(Quiz)
        .where(Quiz.key == quiz_key)
        .order_by(Entry.id)
    )
    if only_active:
        stmt = stmt.where(Entry.is_active.is_(True))

    with get_session() as session:
        result = session.execute(stmt)
        entries = []
        for entry in result.scalars():
            entries.append(
                {
                    "hanzi": entry.hanzi,
                    "pinyin": entry.pinyin,
                    "translation": entry.translation,
                    "alt_translations": entry.alt_translations or "",
                    "tags": entry.tags or "",
                }
            )
        return entries


def get_random_entries(
    quiz_key: str, count: int, *, seed: Optional[int] = None
) -> List[Dict[str, str]]:
    """Return a random sample of entries for the given quiz."""
    vocab = get_entries(quiz_key)
    if not vocab:
        return []
    rng = random.Random(seed)
    total = min(count, len(vocab))
    return rng.sample(vocab, k=total)
