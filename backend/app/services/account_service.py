"""Aggregates for the Account dashboard.

Days follow the user's time zone (X-Timezone header), not the server's.

Activity (heatmap, quiz curve, streak, success rate) comes from `review_log`,
which records every answer since it was introduced. For days *before* the first
logged review, the heatmap and quiz curve fall back to the old approximation
(`UserVocabMastery.last_seen_at`: only each word's latest review counts), so the
history from before the log does not disappear. Streak and success rate use the
log only, since the approximation would make them wrong.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, time, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.timezone import UTC, local_date, local_today
from app.models import Entry, ExpressionAttempt, Quiz, ReviewLog, User, UserVocabMastery


MASTERED_CONFIDENCE_THRESHOLD = 0.9
SUCCESS_MIN_RATING = 3  # "Juste" (good) or "Je connais" (easy)
FORECAST_DAYS = 7


def _is_mastered(row: UserVocabMastery) -> bool:
    return float(row.confidence_score or 0.0) >= MASTERED_CONFIDENCE_THRESHOLD


def _local_day_end_utc(day: date, tz: ZoneInfo) -> datetime:
    """Naive-UTC instant where local `day` ends (start of the next local day)."""
    start_next = datetime.combine(day + timedelta(days=1), time.min, tzinfo=tz)
    return start_next.astimezone(timezone.utc).replace(tzinfo=None)


def compute_streak(days: set[date], today: date) -> dict[str, Any]:
    """Consecutive study days. The current streak is still alive if the user studied
    yesterday but not yet today (they can extend it today)."""
    studied_today = today in days
    current = 0
    cursor = today if studied_today else today - timedelta(days=1)
    while cursor in days:
        current += 1
        cursor -= timedelta(days=1)

    best = 0
    run = 0
    previous: date | None = None
    for d in sorted(days):
        run = run + 1 if previous is not None and d - previous == timedelta(days=1) else 1
        best = max(best, run)
        previous = d
    return {"current": current, "best": best, "studied_today": studied_today}


def _rate(successes: int, total: int) -> float | None:
    return round(successes / total, 4) if total else None


def _level_progress(db: Session, mastery_by_entry: dict[int, UserVocabMastery]) -> list[dict[str, Any]]:
    rows = db.execute(
        select(Entry.id, Quiz.key, Quiz.title, Quiz.level)
        .join(Quiz, Quiz.id == Entry.quiz_id)
        .where(Entry.is_active.is_(True))
    ).all()
    levels: dict[str, dict[str, Any]] = {}
    for entry_id, key, title, level in rows:
        item = levels.setdefault(
            key,
            {"quiz_key": key, "title": title, "level": level,
             "total": 0, "mastered": 0, "learning": 0, "new": 0},
        )
        item["total"] += 1
        record = mastery_by_entry.get(entry_id)
        if record is None:
            item["new"] += 1
        elif _is_mastered(record):
            item["mastered"] += 1
        else:
            item["learning"] += 1
    return sorted(levels.values(), key=lambda x: (x["level"] is None, x["level"] or 0, x["quiz_key"]))


def _upcoming(mastery_rows: list[UserVocabMastery], tz: ZoneInfo, now_naive: datetime, today: date) -> dict[str, Any]:
    end_today = _local_day_end_utc(today, tz)
    end_tomorrow = _local_day_end_utc(today + timedelta(days=1), tz)
    due_dates = [r.fsrs_due_at for r in mastery_rows if r.fsrs_due_at is not None]

    forecast = []
    for i in range(FORECAST_DAYS):
        day = today + timedelta(days=i)
        end = _local_day_end_utc(day, tz)
        start = None if i == 0 else _local_day_end_utc(day - timedelta(days=1), tz)
        # Day 0 also counts everything overdue: it all has to be reviewed today.
        count = sum(1 for d in due_dates if d < end and (start is None or d >= start))
        forecast.append({"date": day, "count": count})

    return {
        "due_now": sum(1 for d in due_dates if d <= now_naive),
        "due_today": sum(1 for d in due_dates if d < end_today),
        "due_tomorrow": sum(1 for d in due_dates if end_today <= d < end_tomorrow),
        "due_next_7_days": sum(1 for d in due_dates if d < _local_day_end_utc(today + timedelta(days=FORECAST_DAYS - 1), tz)),
        "forecast": forecast,
    }


def get_overview(
    db: Session,
    user: User,
    *,
    heatmap_days: int = 90,
    trend_days: int = 30,
    tz: ZoneInfo = UTC,
    now_utc: datetime | None = None,
) -> dict[str, Any]:
    now_naive = (now_utc or datetime.now(timezone.utc)).astimezone(timezone.utc).replace(tzinfo=None)
    today = local_today(tz, now_naive)
    heatmap_start = today - timedelta(days=heatmap_days - 1)
    trend_start = today - timedelta(days=trend_days - 1)

    total_entries = int(db.execute(select(func.count(Entry.id)).where(Entry.is_active.is_(True))).scalar() or 0)

    # Words removed from the syllabus are deactivated, not deleted: ignore their history here.
    mastery_stmt = (
        select(UserVocabMastery)
        .join(Entry, Entry.id == UserVocabMastery.entry_id)
        .where(UserVocabMastery.user_id == user.id, Entry.is_active.is_(True))
    )
    mastery_rows = list(db.execute(mastery_stmt).scalars().all())

    mastered_count = sum(
        1 for row in mastery_rows if float(row.confidence_score or 0.0) >= MASTERED_CONFIDENCE_THRESHOLD
    )
    learning_count = len(mastery_rows) - mastered_count
    new_count = max(0, total_entries - len(mastery_rows))
    total_reviews = sum(int(row.review_count or 0) for row in mastery_rows)

    mastery_by_entry = {row.entry_id: row for row in mastery_rows}

    # Full review history (one row per answer), bucketed by the user's local day.
    logs = list(
        db.execute(
            select(ReviewLog.rating, ReviewLog.reviewed_at).where(ReviewLog.user_id == user.id)
        ).all()
    )
    log_days: dict[date, list[int]] = defaultdict(list)
    for rating, reviewed_at in logs:
        log_days[local_date(reviewed_at, tz)].append(int(rating))
    tracking_since = min(log_days) if log_days else None

    def before_log(d: date) -> bool:
        return tracking_since is None or d < tracking_since

    # Approximation for days before the log: each word's latest review only.
    approx_counts: dict[date, int] = defaultdict(int)
    approx_ratings: dict[date, list[int]] = defaultdict(list)
    for row in mastery_rows:
        if row.last_seen_at is None:
            continue
        d = local_date(row.last_seen_at, tz)
        if not before_log(d):
            continue
        approx_counts[d] += 1
        if row.fsrs_last_rating is not None:
            approx_ratings[d].append(int(row.fsrs_last_rating))

    def day_count(d: date) -> int:
        return approx_counts.get(d, 0) if before_log(d) else len(log_days.get(d, []))

    activity_heatmap = [
        {"date": heatmap_start + timedelta(days=i), "count": day_count(heatmap_start + timedelta(days=i))}
        for i in range(heatmap_days)
    ]

    # Quiz progression: per-day average rating (1..4).
    quiz_progression = []
    for i in range(trend_days):
        d = trend_start + timedelta(days=i)
        ratings = approx_ratings.get(d, []) if before_log(d) else log_days.get(d, [])
        if ratings:
            quiz_progression.append(
                {"date": d, "avg_rating": round(sum(ratings) / len(ratings), 2), "count": len(ratings)}
            )

    # Success rate (log only): share of "Juste" / "Je connais" answers.
    def window(days: int) -> tuple[int, int]:
        first = today - timedelta(days=days - 1)
        ratings = [r for d, rs in log_days.items() if first <= d <= today for r in rs]
        return sum(1 for r in ratings if r >= SUCCESS_MIN_RATING), len(ratings)

    s7, n7 = window(7)
    s30, n30 = window(30)
    success_rate = {
        "last_7_days": _rate(s7, n7),
        "last_30_days": _rate(s30, n30),
        "reviews_7_days": n7,
        "reviews_30_days": n30,
        "daily": [
            {
                "date": d,
                "rate": _rate(sum(1 for r in rs if r >= SUCCESS_MIN_RATING), len(rs)),
                "count": len(rs),
            }
            for d, rs in sorted(log_days.items())
            if trend_start <= d <= today
        ],
        "tracking_since": tracking_since,
    }

    streak = compute_streak(set(log_days), today)
    level_progress = _level_progress(db, mastery_by_entry)
    upcoming = _upcoming(mastery_rows, tz, now_naive, today)

    # Expression progression: one point per scored attempt over `trend_days`.
    attempts_stmt = (
        select(ExpressionAttempt)
        .where(
            ExpressionAttempt.user_id == user.id,
            ExpressionAttempt.created_at
            >= datetime.combine(trend_start, time.min, tzinfo=tz).astimezone(timezone.utc).replace(tzinfo=None),
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
        "level_progress": level_progress,
        "streak": streak,
        "success_rate": success_rate,
        "upcoming": upcoming,
    }
