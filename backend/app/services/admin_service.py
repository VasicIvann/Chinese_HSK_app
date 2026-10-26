"""Read-only figures about the registered accounts, for the Admin page.

Only counters and dates: no password hash, no text written by the users, no drawings.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.timezone import local_date, local_today
from app.models import (
    ExerciseResult,
    ExpressionAttempt,
    ReviewLog,
    User,
    UserDailyUsage,
    UserVocabMastery,
    WordDrawing,
)
from app.services.account_service import MASTERED_CONFIDENCE_THRESHOLD
from app.services.version_service import get_user_version

SECTIONS = ("listening", "writing", "grammar", "classifiers", "tones")


def _activity_times(db: Session, since: datetime | None = None) -> dict[int, list[datetime]]:
    """Every dated action per user (cards, exercise sets, texts, drawings)."""
    out: dict[int, list[datetime]] = defaultdict(list)
    for column, user_column in (
        (ReviewLog.reviewed_at, ReviewLog.user_id),
        (ExerciseResult.created_at, ExerciseResult.user_id),
        (ExpressionAttempt.created_at, ExpressionAttempt.user_id),
        (WordDrawing.created_at, WordDrawing.user_id),
    ):
        query = select(user_column, column)
        if since is not None:
            query = query.where(column >= since)
        for user_id, when in db.execute(query):
            out[user_id].append(when)
    return out


def _last_active(db: Session) -> dict[int, datetime]:
    last: dict[int, datetime] = {}
    for column, user_column in (
        (ReviewLog.reviewed_at, ReviewLog.user_id),
        (ExerciseResult.created_at, ExerciseResult.user_id),
        (ExpressionAttempt.created_at, ExpressionAttempt.user_id),
        (WordDrawing.created_at, WordDrawing.user_id),
        (UserVocabMastery.last_seen_at, UserVocabMastery.user_id),  # history older than review_log
    ):
        for user_id, when in db.execute(select(user_column, func.max(column)).group_by(user_column)):
            if when and (user_id not in last or when > last[user_id]):
                last[user_id] = when
    return last


def _count_by_user(db: Session, user_column, *where) -> dict[int, int]:
    return dict(db.execute(select(user_column, func.count()).where(*where).group_by(user_column)).all())


def users_overview(db: Session, *, tz: ZoneInfo, now_utc: datetime | None = None) -> dict[str, Any]:
    now = (now_utc or datetime.now(timezone.utc)).astimezone(timezone.utc).replace(tzinfo=None)
    today = local_today(tz, now)
    week_ago, month_ago = now - timedelta(days=7), now - timedelta(days=30)

    users = db.execute(select(User).order_by(User.created_at.desc())).scalars().all()
    last = _last_active(db)
    recent = _activity_times(db, since=month_ago)
    words_seen = _count_by_user(db, UserVocabMastery.user_id)
    mastered = _count_by_user(
        db, UserVocabMastery.user_id, UserVocabMastery.confidence_score >= MASTERED_CONFIDENCE_THRESHOLD
    )
    reviews = _count_by_user(db, ReviewLog.user_id)
    reviews_7d = _count_by_user(db, ReviewLog.user_id, ReviewLog.reviewed_at >= week_ago)
    expressions = _count_by_user(db, ExpressionAttempt.user_id)
    drawings = _count_by_user(db, WordDrawing.user_id)

    questions: dict[int, dict[str, int]] = defaultdict(lambda: dict.fromkeys(SECTIONS, 0))
    for user_id, section, total in db.execute(
        select(ExerciseResult.user_id, ExerciseResult.section, func.sum(ExerciseResult.total)).group_by(
            ExerciseResult.user_id, ExerciseResult.section
        )
    ):
        if section in SECTIONS:
            questions[user_id][section] = int(total or 0)

    claude: dict[int, dict[str, int]] = defaultdict(lambda: {"calls": 0, "tokens": 0})
    for user_id, calls, tokens_in, tokens_out in db.execute(
        select(
            UserDailyUsage.user_id,
            func.sum(UserDailyUsage.count),
            func.sum(UserDailyUsage.tokens_input),
            func.sum(UserDailyUsage.tokens_output),
        ).group_by(UserDailyUsage.user_id)
    ):
        claude[user_id] = {"calls": int(calls or 0), "tokens": int(tokens_in or 0) + int(tokens_out or 0)}

    rows = []
    for user in users:
        days_30 = {local_date(t, tz) for t in recent.get(user.id, [])}
        rows.append(
            {
                "id": user.id,
                "email": user.email,
                "created_at": user.created_at,
                "hsk_version": get_user_version(db, user.id),
                "last_active_at": last.get(user.id),
                "active_days_30": len(days_30),
                "active_today": today in days_30,
                "words_seen": words_seen.get(user.id, 0),
                "words_mastered": mastered.get(user.id, 0),
                "reviews": reviews.get(user.id, 0),
                "reviews_7d": reviews_7d.get(user.id, 0),
                "questions": dict(questions[user.id]),
                "expressions": expressions.get(user.id, 0),
                "drawings": drawings.get(user.id, 0),
                "claude_calls": claude[user.id]["calls"],
                "claude_tokens": claude[user.id]["tokens"],
            }
        )

    def active_since(cutoff: datetime) -> int:
        return sum(1 for times in recent.values() if any(t >= cutoff for t in times))

    signups = [u.created_at for u in users]
    return {
        "summary": {
            "users": len(users),
            "signups_7d": sum(1 for d in signups if d >= week_ago),
            "signups_30d": sum(1 for d in signups if d >= month_ago),
            "active_today": sum(1 for r in rows if r["active_today"]),
            "active_7d": active_since(week_ago),
            "active_30d": active_since(month_ago),
            "reviews_7d": sum(reviews_7d.values()),
            "claude_tokens": sum(c["tokens"] for c in claude.values()),
        },
        "signups_per_week": _signups_per_week(signups, tz, today),
        "users": rows,
    }


def _signups_per_week(signups: list[datetime], tz: ZoneInfo, today: date, weeks: int = 12) -> list[dict[str, Any]]:
    """Accounts created per week (weeks starting on Monday), last `weeks` weeks."""
    monday = today - timedelta(days=today.weekday())
    starts = [monday - timedelta(weeks=i) for i in range(weeks - 1, -1, -1)]
    counts = dict.fromkeys(starts, 0)
    for created in signups:
        d = local_date(created, tz)
        week = d - timedelta(days=d.weekday())
        if week in counts:
            counts[week] += 1
    return [{"week": w, "count": c} for w, c in counts.items()]
