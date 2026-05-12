"""High level data access helpers for quizzes and user accounts."""

from __future__ import annotations

from datetime import date, datetime
from functools import lru_cache
import json
import random
from typing import Dict, List, Optional

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from db import get_session, init_db
from models import (
    Entry,
    ExpressionAttempt,
    Quiz,
    User,
    UserDailyUsage,
    UserSetting,
    UserVocabMastery,
)
from utils.auth import hash_password, verify_password


# Ensure tables exist before any query.
init_db()


@lru_cache(maxsize=1)
def _list_quizzes_cached() -> tuple[Dict[str, Optional[str]], ...]:
    """Cached quiz list for static metadata reads."""
    stmt = select(Quiz).order_by(func.coalesce(Quiz.level, 9999), Quiz.title)
    with get_session() as session:
        result = session.execute(stmt)
        quizzes: List[Dict[str, Optional[str]]] = []
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
        return tuple(quizzes)


def list_quizzes() -> List[Dict[str, Optional[str]]]:
    """Return all available quizzes ordered by level then title."""
    return [dict(item) for item in _list_quizzes_cached()]


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


def get_entries(quiz_key: str, only_active: bool = True) -> List[Dict[str, object]]:
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
                    "id": entry.id,
                    "quiz_id": entry.quiz_id,
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
) -> List[Dict[str, object]]:
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


# ---------------------------------------------------------------------------
# User vocabulary mastery (FSRS-backed)

# Kept for legacy UI labels mapping confidence ranges.
MASTERY_STATUS_SCORES: Dict[str, float] = {
    "je connais ce mot": 1.0,
    "juste": 0.75,
    "difficile": 0.4,
    "faux": 0.0,
}


def upsert_user_vocab_mastery(user_id: int, entry_id: int, status: str) -> Dict[str, object]:
    """Insert/update mastery for one entry. Delegates scheduling to FSRS."""
    from srs import rate_entry  # local import to avoid circular deps

    return rate_entry(user_id=user_id, entry_id=entry_id, status=status)


def get_user_mastery_for_quiz(user_id: int, quiz_key: str) -> Dict[int, Dict[str, object]]:
    """Return mastery rows for one user and one quiz, keyed by entry_id."""
    stmt = (
        select(UserVocabMastery)
        .join(Entry, UserVocabMastery.entry_id == Entry.id)
        .join(Quiz, Entry.quiz_id == Quiz.id)
        .where(UserVocabMastery.user_id == user_id, Quiz.key == quiz_key)
    )

    with get_session() as session:
        rows = session.execute(stmt).scalars().all()
        return {
            row.entry_id: {
                "status": row.status,
                "confidence_score": row.confidence_score,
                "review_count": row.review_count,
                "last_seen_at": row.last_seen_at,
            }
            for row in rows
        }


def get_due_entries(
    quiz_key: str,
    user_id: int,
    count: int,
    *,
    seed: Optional[int] = None,
    new_ratio: float = 0.30,
) -> List[Dict[str, object]]:
    """Return quiz entries prioritized by FSRS due dates.

    Delegates to `srs.select_due_entries`. `new_ratio` is the share of the
    session reserved for cards the user has never seen; the rest is filled with
    cards whose FSRS due date has passed (oldest-overdue first), and finally
    with upcoming cards if more slots remain.
    """
    from srs import select_due_entries  # local import to avoid circular deps

    return select_due_entries(
        quiz_key=quiz_key,
        user_id=user_id,
        count=count,
        new_ratio=new_ratio,
        seed=seed,
    )


def get_user_mastery_entries(user_id: int, quiz_key: Optional[str] = None) -> List[Dict[str, object]]:
    """Return mastery rows enriched with entry and quiz metadata for dashboard views."""
    stmt = (
        select(UserVocabMastery, Entry, Quiz)
        .join(Entry, UserVocabMastery.entry_id == Entry.id)
        .join(Quiz, Entry.quiz_id == Quiz.id)
        .where(UserVocabMastery.user_id == user_id)
        .order_by(Quiz.level.asc(), Quiz.title.asc(), Entry.id.asc())
    )
    if quiz_key:
        stmt = stmt.where(Quiz.key == quiz_key)

    with get_session() as session:
        rows = session.execute(stmt).all()
        return [
            {
                "quiz_key": quiz.key,
                "quiz_title": quiz.title,
                "entry_id": entry.id,
                "hanzi": entry.hanzi,
                "pinyin": entry.pinyin,
                "translation": entry.translation,
                "status": mastery.status,
                "confidence_score": mastery.confidence_score,
                "review_count": mastery.review_count,
                "last_seen_at": mastery.last_seen_at,
                "next_review_at": mastery.fsrs_due_at,
                "stability_days": mastery.fsrs_stability,
                "last_rating": mastery.fsrs_last_rating,
            }
            for mastery, entry, quiz in rows
        ]


# ---------------------------------------------------------------------------
# Expression écrite — attempts + daily quota


def find_entry_ids_by_hanzi(hanzi_terms: List[str]) -> Dict[str, int]:
    """Resolve hanzi strings to entry_ids (first match wins per hanzi)."""
    cleaned = [term.strip() for term in hanzi_terms if term and term.strip()]
    if not cleaned:
        return {}

    stmt = select(Entry.id, Entry.hanzi).where(Entry.hanzi.in_(cleaned))
    with get_session() as session:
        rows = session.execute(stmt).all()
        mapping: Dict[str, int] = {}
        for entry_id, hanzi in rows:
            mapping.setdefault(hanzi, entry_id)
        return mapping


def record_expression_attempt(
    *,
    user_id: int,
    hsk_level: int,
    subject: str,
    user_text: str,
    correction: Dict[str, object],
    score: Optional[int],
    tokens_input: int,
    tokens_output: int,
    model_id: str,
) -> int:
    """Persist a single expression attempt + its correction."""
    payload = json.dumps(correction, ensure_ascii=False)
    with get_session() as session:
        attempt = ExpressionAttempt(
            user_id=user_id,
            hsk_level=hsk_level,
            subject=subject,
            user_text=user_text,
            correction_json=payload,
            score=score,
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            model_id=model_id,
        )
        session.add(attempt)
        session.flush()
        return int(attempt.id)


def list_expression_attempts(user_id: int, limit: int = 20) -> List[Dict[str, object]]:
    """Return the most recent expression attempts for a user."""
    stmt = (
        select(ExpressionAttempt)
        .where(ExpressionAttempt.user_id == user_id)
        .order_by(ExpressionAttempt.created_at.desc())
        .limit(limit)
    )
    with get_session() as session:
        rows = session.execute(stmt).scalars().all()
        results: List[Dict[str, object]] = []
        for row in rows:
            try:
                correction = json.loads(row.correction_json)
            except (TypeError, ValueError):
                correction = {}
            results.append(
                {
                    "id": row.id,
                    "hsk_level": row.hsk_level,
                    "subject": row.subject,
                    "user_text": row.user_text,
                    "correction": correction,
                    "score": row.score,
                    "tokens_input": row.tokens_input,
                    "tokens_output": row.tokens_output,
                    "model_id": row.model_id,
                    "created_at": row.created_at,
                }
            )
        return results


def get_or_create_daily_usage(user_id: int, kind: str) -> Dict[str, int]:
    """Return today's usage row for a (user, kind), creating it if missing."""
    today = date.today()
    with get_session() as session:
        stmt = select(UserDailyUsage).where(
            UserDailyUsage.user_id == user_id,
            UserDailyUsage.usage_date == today,
            UserDailyUsage.kind == kind,
        )
        row = session.execute(stmt).scalars().first()
        if row is None:
            row = UserDailyUsage(
                user_id=user_id,
                usage_date=today,
                kind=kind,
                count=0,
                tokens_input=0,
                tokens_output=0,
            )
            session.add(row)
            session.flush()
        return {
            "count": int(row.count or 0),
            "tokens_input": int(row.tokens_input or 0),
            "tokens_output": int(row.tokens_output or 0),
        }


def increment_daily_usage(
    user_id: int,
    kind: str,
    *,
    count_delta: int = 1,
    tokens_input_delta: int = 0,
    tokens_output_delta: int = 0,
) -> Dict[str, int]:
    """Atomically increment a daily usage row."""
    today = date.today()
    with get_session() as session:
        stmt = select(UserDailyUsage).where(
            UserDailyUsage.user_id == user_id,
            UserDailyUsage.usage_date == today,
            UserDailyUsage.kind == kind,
        )
        row = session.execute(stmt).scalars().first()
        if row is None:
            row = UserDailyUsage(
                user_id=user_id,
                usage_date=today,
                kind=kind,
                count=count_delta,
                tokens_input=tokens_input_delta,
                tokens_output=tokens_output_delta,
            )
            session.add(row)
        else:
            row.count = int(row.count or 0) + count_delta
            row.tokens_input = int(row.tokens_input or 0) + tokens_input_delta
            row.tokens_output = int(row.tokens_output or 0) + tokens_output_delta
        session.flush()
        return {
            "count": int(row.count or 0),
            "tokens_input": int(row.tokens_input or 0),
            "tokens_output": int(row.tokens_output or 0),
        }
