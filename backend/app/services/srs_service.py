"""FSRS scheduling service for the FastAPI backend.

Wraps the `fsrs` library. The API contract uses the standard English SRS enum
(`again` / `hard` / `good` / `easy`) which we translate to FSRS `Rating(1..4)`.
"""

from __future__ import annotations

import random
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from fsrs import Card, Rating, Scheduler, State
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Entry, Quiz, UserVocabMastery


class RatingEnum(str, Enum):
    """English SRS rating, mirrors FSRS Rating enum (1..4)."""

    AGAIN = "again"
    HARD = "hard"
    GOOD = "good"
    EASY = "easy"


_RATING_TO_FSRS: dict[RatingEnum, int] = {
    RatingEnum.AGAIN: Rating.Again.value,
    RatingEnum.HARD: Rating.Hard.value,
    RatingEnum.GOOD: Rating.Good.value,
    RatingEnum.EASY: Rating.Easy.value,
}

_RATING_TO_LEGACY_STATUS: dict[RatingEnum, str] = {
    RatingEnum.AGAIN: "faux",
    RatingEnum.HARD: "difficile",
    RatingEnum.GOOD: "juste",
    RatingEnum.EASY: "je connais ce mot",
}

_RATING_TO_CONFIDENCE: dict[RatingEnum, float] = {
    RatingEnum.AGAIN: 0.0,
    RatingEnum.HARD: 0.4,
    RatingEnum.GOOD: 0.75,
    RatingEnum.EASY: 1.0,
}


_SCHEDULER = Scheduler()


def _to_utc_aware(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _to_naive_utc(dt: datetime) -> datetime:
    aware = _to_utc_aware(dt)
    assert aware is not None
    return aware.replace(tzinfo=None)


def _build_card_from_record(record: UserVocabMastery) -> Card:
    if record.fsrs_state is None:
        return Card()
    return Card(
        state=State(record.fsrs_state),
        step=record.fsrs_step,
        stability=record.fsrs_stability,
        difficulty=record.fsrs_difficulty,
        due=_to_utc_aware(record.fsrs_due_at) or datetime.now(timezone.utc),
        last_review=_to_utc_aware(record.fsrs_last_review_at),
    )


def _write_card_into_record(record: UserVocabMastery, card: Card, rating_value: int) -> None:
    record.fsrs_state = int(card.state.value) if card.state is not None else None
    record.fsrs_step = card.step
    record.fsrs_stability = card.stability
    record.fsrs_difficulty = card.difficulty
    record.fsrs_due_at = _to_naive_utc(card.due) if card.due else None
    record.fsrs_last_review_at = _to_naive_utc(card.last_review) if card.last_review else None
    record.fsrs_last_rating = rating_value


class MasterySnapshot(dict):
    """Plain dict subclass used as a transparent return type for rate_entry()."""


def rate_entry(
    db: Session, *, user_id: int, entry_id: int, rating: RatingEnum
) -> MasterySnapshot:
    """Apply a user rating to an entry using FSRS scheduling.

    Returns a dict snapshot suitable for direct JSON serialization.
    """
    rating_value = _RATING_TO_FSRS[rating]
    fsrs_rating = Rating(rating_value)
    confidence = _RATING_TO_CONFIDENCE[rating]
    legacy_status = _RATING_TO_LEGACY_STATUS[rating]
    now_utc_aware = datetime.now(timezone.utc)
    now_naive = now_utc_aware.replace(tzinfo=None)

    entry = db.get(Entry, entry_id)
    if entry is None:
        raise ValueError(f"Unknown entry_id: {entry_id}")

    stmt = select(UserVocabMastery).where(
        UserVocabMastery.user_id == user_id,
        UserVocabMastery.entry_id == entry_id,
    )
    record = db.execute(stmt).scalars().first()

    if record is None:
        record = UserVocabMastery(
            user_id=user_id,
            entry_id=entry_id,
            status=legacy_status,
            confidence_score=confidence,
            review_count=0,
            last_seen_at=now_naive,
        )
        db.add(record)
        db.flush()

    card = _build_card_from_record(record)
    new_card, _log = _SCHEDULER.review_card(card, fsrs_rating, review_datetime=now_utc_aware)
    _write_card_into_record(record, new_card, rating_value)

    previous_count = int(record.review_count or 0)
    previous_avg = float(record.confidence_score or 0.0)
    new_count = previous_count + 1
    record.confidence_score = ((previous_avg * previous_count) + confidence) / new_count
    record.review_count = new_count
    record.status = legacy_status
    record.last_seen_at = now_naive

    db.flush()

    return MasterySnapshot(
        entry_id=record.entry_id,
        rating=rating.value,
        rating_value=rating_value,
        confidence_score=record.confidence_score,
        review_count=record.review_count,
        last_seen_at=record.last_seen_at,
        next_review_at=record.fsrs_due_at,
        stability_days=record.fsrs_stability,
        difficulty=record.fsrs_difficulty,
        state=record.fsrs_state,
    )


def _fetch_mastery_for_quiz(
    db: Session, user_id: int, quiz_key: str
) -> dict[int, UserVocabMastery]:
    stmt = (
        select(UserVocabMastery)
        .join(Entry, UserVocabMastery.entry_id == Entry.id)
        .join(Quiz, Entry.quiz_id == Quiz.id)
        .where(UserVocabMastery.user_id == user_id, Quiz.key == quiz_key)
    )
    rows = db.execute(stmt).scalars().all()
    return {row.entry_id: row for row in rows}


def select_due_entries(
    db: Session,
    *,
    user_id: int,
    quiz_key: str,
    count: int,
    new_ratio: float = 0.30,
    seed: Optional[int] = None,
) -> list[Entry]:
    """Pick the next entries to study, biased toward due cards (FSRS due_at <= now)."""
    stmt = (
        select(Entry)
        .join(Quiz)
        .where(Quiz.key == quiz_key, Entry.is_active.is_(True))
        .order_by(Entry.id)
    )
    vocab = list(db.execute(stmt).scalars().all())
    if not vocab:
        return []

    mastery = _fetch_mastery_for_quiz(db, user_id, quiz_key)
    rng = random.Random(seed)
    now_naive = datetime.utcnow()

    due_bucket: list[Entry] = []
    upcoming_bucket: list[Entry] = []
    new_bucket: list[Entry] = []

    for entry in vocab:
        record = mastery.get(entry.id)
        if record is None or record.fsrs_due_at is None:
            new_bucket.append(entry)
        elif record.fsrs_due_at <= now_naive:
            due_bucket.append(entry)
        else:
            upcoming_bucket.append(entry)

    rng.shuffle(new_bucket)
    due_bucket.sort(
        key=lambda e: (
            mastery[e.id].fsrs_due_at or now_naive,
            mastery[e.id].fsrs_stability or 0.0,
            rng.random(),
        )
    )
    upcoming_bucket.sort(key=lambda e: mastery[e.id].fsrs_due_at or now_naive)

    desired_new = max(1, int(round(count * new_ratio))) if new_bucket else 0
    desired_due = max(0, count - desired_new)

    selected: list[Entry] = []
    used: set[int] = set()

    def take(source: list[Entry], amount: int) -> None:
        for entry in source:
            if amount <= 0:
                return
            if entry.id in used:
                continue
            selected.append(entry)
            used.add(entry.id)
            amount -= 1

    take(due_bucket, desired_due)
    take(new_bucket, desired_new)

    remaining = count - len(selected)
    if remaining > 0:
        take(due_bucket, remaining)
        remaining = count - len(selected)
    if remaining > 0:
        take(new_bucket, remaining)
        remaining = count - len(selected)
    if remaining > 0:
        take(upcoming_bucket, remaining)

    return selected[: min(count, len(selected))]


def get_due_count(
    db: Session, user_id: int, quiz_key: Optional[str] = None
) -> dict[str, int]:
    """Return a {due, new, upcoming} counts summary, optionally scoped to one quiz."""
    summary = {"due": 0, "new": 0, "upcoming": 0}
    now_naive = datetime.utcnow()

    quiz_keys: list[str]
    if quiz_key:
        quiz_keys = [quiz_key]
    else:
        quiz_keys = list(db.execute(select(Quiz.key)).scalars().all())

    for key in quiz_keys:
        stmt = (
            select(Entry.id)
            .join(Quiz)
            .where(Quiz.key == key, Entry.is_active.is_(True))
        )
        entry_ids = list(db.execute(stmt).scalars().all())
        if not entry_ids:
            continue
        mastery = _fetch_mastery_for_quiz(db, user_id, key)
        for entry_id in entry_ids:
            record = mastery.get(entry_id)
            if record is None or record.fsrs_due_at is None:
                summary["new"] += 1
            elif record.fsrs_due_at <= now_naive:
                summary["due"] += 1
            else:
                summary["upcoming"] += 1
    return summary


def queue_entries_for_relearn(db: Session, user_id: int, entry_ids: list[int]) -> int:
    """Force a hard reset (`again`) on the given entries. Used by Expression flow."""
    affected = 0
    for entry_id in entry_ids:
        try:
            rate_entry(db, user_id=user_id, entry_id=entry_id, rating=RatingEnum.AGAIN)
            affected += 1
        except ValueError:
            continue
    return affected


__all__ = [
    "MasterySnapshot",
    "RatingEnum",
    "get_due_count",
    "queue_entries_for_relearn",
    "rate_entry",
    "select_due_entries",
]
