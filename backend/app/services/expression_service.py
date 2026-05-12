"""Persistence + daily quota helpers for the Expression écrite endpoints."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Entry, ExpressionAttempt, UserDailyUsage


def find_entry_ids_by_hanzi(db: Session, hanzi_terms: list[str]) -> dict[str, int]:
    """Best-effort resolution of hanzi → entry_id. Unknown terms are dropped."""
    cleaned = [term.strip() for term in hanzi_terms if term and term.strip()]
    if not cleaned:
        return {}
    stmt = select(Entry.id, Entry.hanzi).where(Entry.hanzi.in_(cleaned))
    rows = db.execute(stmt).all()
    mapping: dict[str, int] = {}
    for entry_id, hanzi in rows:
        mapping.setdefault(hanzi, entry_id)
    return mapping


def record_attempt(
    db: Session,
    *,
    user_id: int,
    hsk_level: int,
    subject: str,
    user_text: str,
    correction: dict[str, Any],
    score: int | None,
    tokens_input: int,
    tokens_output: int,
    model_id: str,
) -> ExpressionAttempt:
    payload = json.dumps(correction, ensure_ascii=False)
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
    db.add(attempt)
    db.flush()
    return attempt


def list_attempts(db: Session, user_id: int, limit: int = 50) -> list[dict[str, Any]]:
    limit = max(1, min(limit, 200))
    stmt = (
        select(ExpressionAttempt)
        .where(ExpressionAttempt.user_id == user_id)
        .order_by(ExpressionAttempt.created_at.desc())
        .limit(limit)
    )
    rows = list(db.execute(stmt).scalars().all())
    out: list[dict[str, Any]] = []
    for row in rows:
        try:
            correction = json.loads(row.correction_json)
        except (TypeError, ValueError):
            correction = {}
        out.append(
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
    return out


@dataclass
class DailyUsageSnapshot:
    """Read-only view of today's usage. Returns zeros if no row exists yet."""

    count: int = 0
    tokens_input: int = 0
    tokens_output: int = 0


def get_daily_usage(db: Session, user_id: int, kind: str) -> DailyUsageSnapshot:
    """Read-only fetch of today's usage. Does NOT insert. Safe to call concurrently."""
    today = date.today()
    stmt = select(UserDailyUsage).where(
        UserDailyUsage.user_id == user_id,
        UserDailyUsage.usage_date == today,
        UserDailyUsage.kind == kind,
    )
    row = db.execute(stmt).scalars().first()
    if row is None:
        return DailyUsageSnapshot()
    return DailyUsageSnapshot(
        count=int(row.count or 0),
        tokens_input=int(row.tokens_input or 0),
        tokens_output=int(row.tokens_output or 0),
    )


def increment_daily_usage(
    db: Session,
    *,
    user_id: int,
    kind: str,
    count_delta: int = 1,
    tokens_input_delta: int = 0,
    tokens_output_delta: int = 0,
) -> DailyUsageSnapshot:
    """Atomic-ish upsert: read-then-update inside the caller's transaction."""
    today = date.today()
    stmt = select(UserDailyUsage).where(
        UserDailyUsage.user_id == user_id,
        UserDailyUsage.usage_date == today,
        UserDailyUsage.kind == kind,
    )
    row = db.execute(stmt).scalars().first()
    if row is None:
        row = UserDailyUsage(
            user_id=user_id,
            usage_date=today,
            kind=kind,
            count=count_delta,
            tokens_input=tokens_input_delta,
            tokens_output=tokens_output_delta,
            updated_at=datetime.utcnow(),
        )
        db.add(row)
    else:
        row.count = int(row.count or 0) + count_delta
        row.tokens_input = int(row.tokens_input or 0) + tokens_input_delta
        row.tokens_output = int(row.tokens_output or 0) + tokens_output_delta
        row.updated_at = datetime.utcnow()
    db.flush()
    return DailyUsageSnapshot(
        count=int(row.count or 0),
        tokens_input=int(row.tokens_input or 0),
        tokens_output=int(row.tokens_output or 0),
    )


__all__ = [
    "DailyUsageSnapshot",
    "find_entry_ids_by_hanzi",
    "get_daily_usage",
    "increment_daily_usage",
    "list_attempts",
    "record_attempt",
]
