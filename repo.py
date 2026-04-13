"""High level data access helpers for quizzes and user accounts."""

from __future__ import annotations

from datetime import datetime
from functools import lru_cache
import random
from typing import Dict, List, Optional

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from db import get_session, init_db
from models import Entry, Quiz, User, UserSetting, UserVocabMastery
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
# User vocabulary mastery (step 2)

MASTERY_STATUS_SCORES: Dict[str, float] = {
    "je connais ce mot": 1.0,
    "juste": 0.75,
    "juste mais dur": 0.4,
    "faux": 0.0,
}


def upsert_user_vocab_mastery(user_id: int, entry_id: int, status: str) -> Dict[str, object]:
    """Insert or update a user's mastery status for one vocabulary entry."""
    normalized_status = status.strip().lower()
    if normalized_status not in MASTERY_STATUS_SCORES:
        raise ValueError(f"Unsupported mastery status: {status}")

    confidence = MASTERY_STATUS_SCORES[normalized_status]
    now = datetime.utcnow()

    with get_session() as session:
        entry = session.get(Entry, entry_id)
        if not entry:
            raise ValueError(f"Unknown entry_id: {entry_id}")

        stmt = select(UserVocabMastery).where(
            UserVocabMastery.user_id == user_id,
            UserVocabMastery.entry_id == entry_id,
        )
        record = session.execute(stmt).scalars().first()

        if record:
            previous_count = int(record.review_count or 0)
            previous_avg = float(record.confidence_score or 0.0)
            new_count = previous_count + 1
            # Running average across all attempts for this word and user.
            record.confidence_score = ((previous_avg * previous_count) + confidence) / new_count
            record.review_count = new_count
            record.status = normalized_status
            record.last_seen_at = now
        else:
            record = UserVocabMastery(
                user_id=user_id,
                entry_id=entry_id,
                status=normalized_status,
                confidence_score=confidence,
                review_count=1,
                last_seen_at=now,
            )
            session.add(record)
            session.flush()

        return {
            "id": record.id,
            "user_id": record.user_id,
            "entry_id": record.entry_id,
            "status": record.status,
            "confidence_score": record.confidence_score,
            "review_count": record.review_count,
            "last_seen_at": record.last_seen_at,
        }


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
) -> List[Dict[str, object]]:
    """Return quiz entries prioritized for revision and new exposure.

    Mastered words (confidence >= 0.9) are excluded entirely.
    Review-needed and unseen words dominate the selection.
    Words in the "just" zone are included sparingly.
    """
    vocab = get_entries(quiz_key)
    if not vocab:
        return []

    mastery = get_user_mastery_for_quiz(user_id, quiz_key)
    rng = random.Random(seed)

    review_bucket: List[Dict[str, object]] = []
    unseen_bucket: List[Dict[str, object]] = []
    just_bucket: List[Dict[str, object]] = []

    for entry in vocab:
        entry_id = int(entry.get("id", 0) or 0)
        m = mastery.get(entry_id)
        if not m:
            unseen_bucket.append(entry)
            continue

        confidence = float(m.get("confidence_score", 0.0) or 0.0)
        if confidence >= 0.9:
            continue
        if confidence <= 0.5:
            review_bucket.append(entry)
        else:
            just_bucket.append(entry)

    def bucket_sort_key(entry: Dict[str, object], bucket_name: str) -> tuple:
        entry_id = int(entry.get("id", 0) or 0)
        m = mastery.get(entry_id)
        confidence = float(m.get("confidence_score", 0.0) or 0.0) if m else 0.0
        reviews = int(m.get("review_count", 0) or 0) if m else 0
        noise = rng.random() * 0.01
        if bucket_name == "review":
            return (confidence, reviews, noise)
        if bucket_name == "unseen":
            return (noise,)
        return (-confidence, reviews, noise)

    review_bucket.sort(key=lambda entry: bucket_sort_key(entry, "review"))
    unseen_bucket.sort(key=lambda entry: bucket_sort_key(entry, "unseen"))
    just_bucket.sort(key=lambda entry: bucket_sort_key(entry, "just"))

    desired_review = int(round(count * 0.45))
    desired_unseen = int(round(count * 0.50))
    desired_just = max(0, count - desired_review - desired_unseen)

    selected: List[Dict[str, object]] = []

    def take_from(bucket: List[Dict[str, object]], amount: int) -> None:
        nonlocal selected
        if amount <= 0 or not bucket:
            return
        take = min(amount, len(bucket))
        selected.extend(bucket[:take])

    take_from(review_bucket, desired_review)
    take_from(unseen_bucket, desired_unseen)
    take_from(just_bucket, desired_just)

    # Redistribute any missing slots to the most important buckets first.
    remaining = count - len(selected)
    if remaining > 0:
        remaining_sources = [review_bucket, unseen_bucket, just_bucket]
        used_ids = {int(entry.get("id", 0) or 0) for entry in selected}
        for bucket in remaining_sources:
            for entry in bucket:
                entry_id = int(entry.get("id", 0) or 0)
                if entry_id in used_ids:
                    continue
                selected.append(entry)
                used_ids.add(entry_id)
                remaining -= 1
                if remaining == 0:
                    break
            if remaining == 0:
                break

    return selected[: min(count, len(selected))]


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
            }
            for mastery, entry, quiz in rows
        ]
