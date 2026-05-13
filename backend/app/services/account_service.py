"""Aggregates for the Account dashboard.

All metrics derive from existing tables (no new persistence). The heatmap and
quiz progression curves use `UserVocabMastery.last_seen_at` as a proxy for
activity — each entry's last review is one event. This is approximate (a user
who rated the same entry 5 times in a day only contributes 1 event) but matches
what we can compute without a `ReviewLog` table.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Entry, ExpressionAttempt, User, UserVocabMastery


MASTERED_CONFIDENCE_THRESHOLD = 0.9


def get_overview(db: Session, user: User, *, heatmap_days: int = 90, trend_days: int = 30) -> dict[str, Any]:
    today = date.today()
    heatmap_start = today - timedelta(days=heatmap_days - 1)
    trend_start = today - timedelta(days=trend_days - 1)

    total_entries = int(db.execute(select(func.count(Entry.id)).where(Entry.is_active.is_(True))).scalar() or 0)

    mastery_stmt = select(UserVocabMastery).where(UserVocabMastery.user_id == user.id)
    mastery_rows = list(db.execute(mastery_stmt).scalars().all())

    mastered_count = sum(
        1 for row in mastery_rows if float(row.confidence_score or 0.0) >= MASTERED_CONFIDENCE_THRESHOLD
    )
    learning_count = len(mastery_rows) - mastered_count
    new_count = max(0, total_entries - len(mastery_rows))
    total_reviews = sum(int(row.review_count or 0) for row in mastery_rows)

    # Activity heatmap: count of last-reviews per day.
    heatmap_counts: dict[date, int] = defaultdict(int)
    for row in mastery_rows:
        if row.last_seen_at is None:
            continue
        d = row.last_seen_at.date()
        if d >= heatmap_start:
            heatmap_counts[d] += 1

    activity_heatmap = [
        {"date": heatmap_start + timedelta(days=i), "count": heatmap_counts.get(heatmap_start + timedelta(days=i), 0)}
        for i in range(heatmap_days)
    ]

    # Quiz progression: per-day average of fsrs_last_rating (1..4).
    quiz_buckets: dict[date, list[int]] = defaultdict(list)
    for row in mastery_rows:
        if row.last_seen_at is None or row.fsrs_last_rating is None:
            continue
        d = row.last_seen_at.date()
        if d >= trend_start:
            quiz_buckets[d].append(int(row.fsrs_last_rating))

    quiz_progression = [
        {
            "date": d,
            "avg_rating": round(sum(ratings) / len(ratings), 2),
            "count": len(ratings),
        }
        for d, ratings in sorted(quiz_buckets.items())
    ]

    # Expression progression: one point per scored attempt over `trend_days`.
    attempts_stmt = (
        select(ExpressionAttempt)
        .where(
            ExpressionAttempt.user_id == user.id,
            ExpressionAttempt.created_at >= datetime.combine(trend_start, datetime.min.time()),
            ExpressionAttempt.score.isnot(None),
        )
        .order_by(ExpressionAttempt.created_at.asc())
    )
    attempts = list(db.execute(attempts_stmt).scalars().all())
    expression_progression = [
        {"date": a.created_at, "score": int(a.score or 0)} for a in attempts
    ]
    total_expressions = int(
        db.execute(
            select(func.count(ExpressionAttempt.id)).where(ExpressionAttempt.user_id == user.id)
        ).scalar()
        or 0
    )

    return {
        "profile": {
            "email": user.email,
            "locale": user.locale,
            "joined_at": user.created_at,
            "total_reviews": total_reviews,
            "total_expressions": total_expressions,
        },
        "mastery": {
            "mastered": mastered_count,
            "learning": learning_count,
            "new": new_count,
            "total_entries": total_entries,
        },
        "activity_heatmap": activity_heatmap,
        "quiz_progression": quiz_progression,
        "expression_progression": expression_progression,
    }
