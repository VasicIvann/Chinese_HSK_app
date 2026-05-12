"""FSRS (Free Spaced Repetition Scheduler) integration.

Wraps the `fsrs` library so the rest of the app can think in terms of mastery
records rather than scheduler internals. Two responsibilities:

1. Update a `UserVocabMastery` row from a user rating using FSRS formulas.
2. Pick the next entries to study for a quiz, biased toward due cards.
"""

from __future__ import annotations

from datetime import datetime, timezone
import random
from typing import Dict, List, Optional, Tuple

from fsrs import Card, Rating, Scheduler, State
from sqlalchemy import asc, select

from db import get_session
from models import Entry, Quiz, UserVocabMastery


_SCHEDULER = Scheduler()


# Legacy French statuses → FSRS rating mapping. Order matches the rating buttons
# shown in the Comprehension page.
RATING_BY_STATUS: Dict[str, int] = {
    "faux": Rating.Again.value,
    "difficile": Rating.Hard.value,
    "juste": Rating.Good.value,
    "je connais ce mot": Rating.Easy.value,
}

# Status → coarse confidence score, kept for legacy dashboards.
STATUS_CONFIDENCE: Dict[str, float] = {
    "faux": 0.0,
    "difficile": 0.4,
    "juste": 0.75,
    "je connais ce mot": 1.0,
}


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
    """Rebuild an FSRS Card from a persisted mastery record."""
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
    """Persist an FSRS Card snapshot onto the mastery record."""
    record.fsrs_state = int(card.state.value) if card.state is not None else None
    record.fsrs_step = card.step
    record.fsrs_stability = card.stability
    record.fsrs_difficulty = card.difficulty
    record.fsrs_due_at = _to_naive_utc(card.due) if card.due else None
    record.fsrs_last_review_at = _to_naive_utc(card.last_review) if card.last_review else None
    record.fsrs_last_rating = rating_value


def rate_entry(user_id: int, entry_id: int, status: str) -> Dict[str, object]:
    """Apply a user rating to an entry using FSRS scheduling.

    `status` is one of the keys of `RATING_BY_STATUS` (French labels). Returns a
    dict snapshot of the updated record, useful for UI feedback.
    """
    normalized_status = status.strip().lower()
    if normalized_status not in RATING_BY_STATUS:
        raise ValueError(f"Unsupported rating status: {status}")

    rating_value = RATING_BY_STATUS[normalized_status]
    rating = Rating(rating_value)
    confidence = STATUS_CONFIDENCE[normalized_status]
    now_utc_aware = datetime.now(timezone.utc)
    now_utc_naive = now_utc_aware.replace(tzinfo=None)

    with get_session() as session:
        entry = session.get(Entry, entry_id)
        if not entry:
            raise ValueError(f"Unknown entry_id: {entry_id}")

        stmt = select(UserVocabMastery).where(
            UserVocabMastery.user_id == user_id,
            UserVocabMastery.entry_id == entry_id,
        )
        record = session.execute(stmt).scalars().first()

        if record is None:
            record = UserVocabMastery(
                user_id=user_id,
                entry_id=entry_id,
                status=normalized_status,
                confidence_score=confidence,
                review_count=0,
                last_seen_at=now_utc_naive,
            )
            session.add(record)
            session.flush()

        card = _build_card_from_record(record)
        new_card, _log = _SCHEDULER.review_card(card, rating, review_datetime=now_utc_aware)
        _write_card_into_record(record, new_card, rating_value)

        # Update legacy aggregate metrics.
        previous_count = int(record.review_count or 0)
        previous_avg = float(record.confidence_score or 0.0)
        new_count = previous_count + 1
        record.confidence_score = ((previous_avg * previous_count) + confidence) / new_count
        record.review_count = new_count
        record.status = normalized_status
        record.last_seen_at = now_utc_naive

        return {
            "id": record.id,
            "user_id": record.user_id,
            "entry_id": record.entry_id,
            "status": record.status,
            "confidence_score": record.confidence_score,
            "review_count": record.review_count,
            "last_seen_at": record.last_seen_at,
            "next_review_at": record.fsrs_due_at,
            "stability_days": record.fsrs_stability,
            "rating": rating_value,
        }


def _fetch_mastery_by_entry(user_id: int, quiz_key: str) -> Dict[int, UserVocabMastery]:
    """Return mastery rows for one user/quiz, keyed by entry_id."""
    stmt = (
        select(UserVocabMastery)
        .join(Entry, UserVocabMastery.entry_id == Entry.id)
        .join(Quiz, Entry.quiz_id == Quiz.id)
        .where(UserVocabMastery.user_id == user_id, Quiz.key == quiz_key)
        .order_by(asc(UserVocabMastery.fsrs_due_at))
    )
    with get_session() as session:
        rows = session.execute(stmt).scalars().all()
        # Detach: pull values into plain objects so they remain usable after the
        # session closes. We mirror the columns we actually use downstream.
        result: Dict[int, UserVocabMastery] = {}
        for row in rows:
            session.expunge(row)
            result[row.entry_id] = row
        return result


def select_due_entries(
    quiz_key: str,
    user_id: int,
    count: int,
    *,
    new_ratio: float = 0.30,
    seed: Optional[int] = None,
) -> List[Dict[str, object]]:
    """Pick study entries for a session, biased toward FSRS due cards.

    The session is composed of three sources:
    * `due_bucket`: cards whose FSRS due date has passed or is today.
    * `new_bucket`: cards never seen by this user yet.
    * `upcoming_bucket`: cards already studied but not yet due (filler).

    The default split favors due cards heavily, introduces a moderate slice of
    new cards (`new_ratio`), and uses upcoming cards only to fill remaining
    slots when the first two buckets cannot satisfy the requested count.
    """
    from repo import get_entries  # local import to avoid circular deps

    vocab = get_entries(quiz_key)
    if not vocab:
        return []

    mastery = _fetch_mastery_by_entry(user_id, quiz_key)
    rng = random.Random(seed)
    now_naive = datetime.utcnow()

    due_bucket: List[Dict[str, object]] = []
    upcoming_bucket: List[Tuple[Dict[str, object], datetime]] = []
    new_bucket: List[Dict[str, object]] = []

    for entry in vocab:
        entry_id = int(entry.get("id", 0) or 0)
        record = mastery.get(entry_id)
        if record is None:
            new_bucket.append(entry)
            continue
        due_at = record.fsrs_due_at
        if due_at is None:
            new_bucket.append(entry)
            continue
        if due_at <= now_naive:
            due_bucket.append(entry)
        else:
            upcoming_bucket.append((entry, due_at))

    rng.shuffle(new_bucket)
    # Sort due cards by most-overdue first, then by lowest stability.
    due_bucket.sort(
        key=lambda entry: (
            (mastery[int(entry["id"])].fsrs_due_at or now_naive),
            (mastery[int(entry["id"])].fsrs_stability or 0.0),
            rng.random(),
        )
    )
    upcoming_bucket.sort(key=lambda pair: pair[1])

    desired_new = max(1, int(round(count * new_ratio))) if new_bucket else 0
    desired_due = max(0, count - desired_new)

    selected: List[Dict[str, object]] = []
    used_ids: set[int] = set()

    def take(source: List[Dict[str, object]], amount: int) -> None:
        for entry in source:
            if amount <= 0:
                return
            entry_id = int(entry.get("id", 0) or 0)
            if entry_id in used_ids:
                continue
            selected.append(entry)
            used_ids.add(entry_id)
            amount -= 1

    take(due_bucket, desired_due)
    take(new_bucket, desired_new)

    # Fill remaining slots with leftover due → new → upcoming.
    remaining = count - len(selected)
    if remaining > 0:
        take(due_bucket, remaining)
        remaining = count - len(selected)
    if remaining > 0:
        take(new_bucket, remaining)
        remaining = count - len(selected)
    if remaining > 0:
        upcoming_entries = [pair[0] for pair in upcoming_bucket]
        take(upcoming_entries, remaining)

    return selected[: min(count, len(selected))]


def queue_entries_for_relearn(user_id: int, entry_ids: List[int]) -> int:
    """Force a hard reset on the given entries by submitting a `Again` rating.

    Used by the Expression flow when Claude flags vocabulary mistakes: those
    words are pushed back into the user's near-term review queue.
    """
    affected = 0
    for entry_id in entry_ids:
        try:
            rate_entry(user_id=user_id, entry_id=entry_id, status="faux")
            affected += 1
        except ValueError:
            continue
    return affected


def get_due_count(user_id: int, quiz_key: Optional[str] = None) -> Dict[str, int]:
    """Return a summary of due/new/upcoming counts for dashboards."""
    from repo import get_entries, list_quizzes  # local import

    quiz_keys = [quiz_key] if quiz_key else [q["key"] for q in list_quizzes()]
    summary = {"due": 0, "new": 0, "upcoming": 0}
    now_naive = datetime.utcnow()

    for key in quiz_keys:
        vocab = get_entries(key)
        if not vocab:
            continue
        mastery = _fetch_mastery_by_entry(user_id, key)
        for entry in vocab:
            entry_id = int(entry.get("id", 0) or 0)
            record = mastery.get(entry_id)
            if record is None or record.fsrs_due_at is None:
                summary["new"] += 1
                continue
            if record.fsrs_due_at <= now_naive:
                summary["due"] += 1
            else:
                summary["upcoming"] += 1
    return summary


def format_next_review(record: Dict[str, object]) -> str:
    """Human-readable hint for the next review delay."""
    next_review_at = record.get("next_review_at")
    if not isinstance(next_review_at, datetime):
        return ""
    delta = next_review_at - datetime.utcnow()
    seconds = int(delta.total_seconds())
    if seconds <= 60:
        return "à revoir tout de suite"
    minutes = seconds // 60
    if minutes < 60:
        return f"à revoir dans {minutes} min"
    hours = minutes // 60
    if hours < 24:
        return f"à revoir dans {hours} h"
    days = hours // 24
    if days < 30:
        return f"à revoir dans {days} j"
    months = days // 30
    if months < 12:
        return f"à revoir dans {months} mois"
    years = days // 365
    return f"à revoir dans {years} an(s)"


__all__ = [
    "RATING_BY_STATUS",
    "STATUS_CONFIDENCE",
    "rate_entry",
    "select_due_entries",
    "queue_entries_for_relearn",
    "get_due_count",
    "format_next_review",
]
