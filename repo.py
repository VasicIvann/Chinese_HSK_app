"""High level data access helpers for quizzes and user accounts."""

from __future__ import annotations

import random
from typing import Dict, List, Optional

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from db import get_session, init_db
from models import Entry, Quiz, User, UserSetting
from utils.auth import hash_password, verify_password


# Ensure tables exist before any query.
init_db()


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


# ---------------------------------------------------------------------------
# User management


def _user_to_dict(user: User) -> Dict[str, Optional[str]]:
    return {
        "id": user.id,
        "email": user.email,
        "locale": user.locale,
        "created_at": user.created_at,
    }


def create_user(email: str, password: str, *, locale: str = "fr") -> Dict[str, Optional[str]]:
    """Create a new user account. Raises ValueError if email already exists."""
    normalized_email = email.strip().lower()
    password_hash = hash_password(password)
    with get_session() as session:
        user = User(email=normalized_email, password_hash=password_hash, locale=locale)
        session.add(user)
        try:
            session.flush()
        except IntegrityError as exc:
            session.rollback()
            raise ValueError("Email déjà enregistré.") from exc
        return _user_to_dict(user)


def authenticate_user(email: str, password: str) -> Optional[Dict[str, Optional[str]]]:
    """Return user dict if credentials are valid."""
    normalized_email = email.strip().lower()
    stmt = select(User).where(User.email == normalized_email)
    with get_session() as session:
        user = session.execute(stmt).scalars().first()
        if user and verify_password(password, user.password_hash):
            return _user_to_dict(user)
        return None


def get_user(user_id: int) -> Optional[Dict[str, Optional[str]]]:
    stmt = select(User).where(User.id == user_id)
    with get_session() as session:
        user = session.execute(stmt).scalars().first()
        return _user_to_dict(user) if user else None


def get_user_settings(user_id: int) -> Dict[str, str]:
    """Return user settings as a dictionary."""
    stmt = select(UserSetting).where(UserSetting.user_id == user_id)
    with get_session() as session:
        settings = session.execute(stmt).scalars().all()
        return {setting.key: setting.value for setting in settings}


def set_user_setting(user_id: int, key: str, value: str) -> None:
    """Upsert a user preference."""
    with get_session() as session:
        stmt = select(UserSetting).where(
            UserSetting.user_id == user_id, UserSetting.key == key
        )
        setting = session.execute(stmt).scalars().first()
        if setting:
            setting.value = value
        else:
            session.add(UserSetting(user_id=user_id, key=key, value=value))


def delete_user_setting(user_id: int, key: str) -> None:
    """Delete a specific user setting."""
    with get_session() as session:
        stmt = select(UserSetting).where(
            UserSetting.user_id == user_id, UserSetting.key == key
        )
        setting = session.execute(stmt).scalars().first()
        if setting:
            session.delete(setting)


def update_user_locale(user_id: int, locale: str) -> None:
    """Update the preferred locale for a user."""
    with get_session() as session:
        user = session.get(User, user_id)
        if user:
            user.locale = locale
