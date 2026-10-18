"""FSRS scheduling service for the FastAPI backend.

Wraps the `fsrs` library. The API contract uses the standard English SRS enum
(`again` / `hard` / `good` / `easy`) which we translate to FSRS `Rating(1..4)`.
"""

from __future__ import annotations

import random
from collections.abc import Sequence
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from fsrs import Card, Rating, Scheduler, State
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Entry, Quiz, ReviewLog, UserVocabMastery


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
    db: Session,
    *,
    user_id: int,
    entry_id: int,
    rating: RatingEnum,
    record_log: bool = False,
    mode: Optional[str] = None,
    elapsed_ms: Optional[int] = None,
) -> MasterySnapshot:
    """Apply a user rating to an entry using FSRS scheduling.

    With `record_log`, also appends a row to the review history (quiz answers);
    internal re-queues (Expression flow) leave it off so they don't count as reviews.
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
    was_new = _is_new(record)
    was_due = (
        not was_new and record.fsrs_due_at is not None and record.fsrs_due_at <= now_naive
    )

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

    if record_log:
        db.add(
            ReviewLog(
                user_id=user_id,
                entry_id=entry_id,
                rating=rating_value,
                was_new=was_new,
                was_due=was_due,
                mode=mode,
                elapsed_ms=elapsed_ms,
                reviewed_at=now_naive,
            )
        )

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


def _normalize_quiz_keys(quiz_keys: str | Sequence[str] | None) -> list[str]:
    """Accept one key, a list of keys, or None; drop blanks and duplicates, keep order."""
    if quiz_keys is None:
        return []
    raw = [quiz_keys] if isinstance(quiz_keys, str) else list(quiz_keys)
    seen: set[str] = set()
    keys: list[str] = []
    for key in raw:
        key = key.strip()
        if key and key not in seen:
            seen.add(key)
            keys.append(key)
    return keys


def _fetch_mastery_for_quizzes(
    db: Session, user_id: int, quiz_keys: list[str]
) -> dict[int, UserVocabMastery]:
    stmt = (
        select(UserVocabMastery)
        .join(Entry, UserVocabMastery.entry_id == Entry.id)
        .join(Quiz, Entry.quiz_id == Quiz.id)
        .where(UserVocabMastery.user_id == user_id, Quiz.key.in_(quiz_keys))
    )
    rows = db.execute(stmt).scalars().all()
    return {row.entry_id: row for row in rows}


def _is_new(record: UserVocabMastery | None) -> bool:
    """A word is "new" when the user has never rated it."""
    return record is None or record.fsrs_due_at is None


def select_due_entries(
    db: Session,
    *,
    user_id: int,
    quiz_keys: str | Sequence[str],
    count: int,
    new_ratio: float = 0.30,
    only_new: bool = False,
    seed: Optional[int] = None,
) -> list[Entry]:
    """Pick the next entries to study across one or more quizzes.

    Default: biased toward due cards (FSRS due_at <= now), mixed with ~`new_ratio`
    never-seen words. With `only_new`, only words the user has never rated, shuffled.
    """
    keys = _normalize_quiz_keys(quiz_keys)
    if not keys or count <= 0:
        return []

    stmt = (
        select(Entry)
        .join(Quiz)
        .where(Quiz.key.in_(keys), Entry.is_active.is_(True))
        .order_by(Entry.id)
    )
    vocab = list(db.execute(stmt).scalars().all())
    if not vocab:
        return []

    mastery = _fetch_mastery_for_quizzes(db, user_id, keys)
    rng = random.Random(seed)
    now_naive = datetime.utcnow()

    due_bucket: list[Entry] = []
    upcoming_bucket: list[Entry] = []
    new_bucket: list[Entry] = []

    for entry in vocab:
        record = mastery.get(entry.id)
        if _is_new(record):
            new_bucket.append(entry)
        elif record.fsrs_due_at <= now_naive:
            due_bucket.append(entry)
        else:
            upcoming_bucket.append(entry)

    rng.shuffle(new_bucket)
    if only_new:
        return new_bucket[:count]

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
    db: Session, user_id: int, quiz_keys: str | Sequence[str] | None = None
) -> dict[str, int]:
    """Return a {due, new, upcoming} counts summary over the given quizzes (all if None)."""
    summary = {"due": 0, "new": 0, "upcoming": 0}
    now_naive = datetime.utcnow()

    keys = _normalize_quiz_keys(quiz_keys)
    if not keys:
        keys = list(db.execute(select(Quiz.key)).scalars().all())
    if not keys:
        return summary

    stmt = (
        select(Entry.id)
        .join(Quiz)
        .where(Quiz.key.in_(keys), Entry.is_active.is_(True))
    )
    entry_ids = list(db.execute(stmt).scalars().all())
    mastery = _fetch_mastery_for_quizzes(db, user_id, keys)
    for entry_id in entry_ids:
        record = mastery.get(entry_id)
        if _is_new(record):
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
