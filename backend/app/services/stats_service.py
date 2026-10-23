"""Study statistics for the Account page: activity per tab, vocabulary growth, time and habits.

Everything is bucketed by the user's local day / hour (timestamps are stored in naive UTC).

Units, kept separate on purpose (one small chart per tab):
- vocabulary: cards answered (one row of review_log);
- Écoute, Écriture HSK, Grammaire, Classificateurs: questions answered (sum of the sets' totals);
- Expression: texts corrected; drawings: drawings saved.
"Actions" (hours / weekdays) count one per card, question, text or drawing.
"""

from __future__ import annotations

from collections import Counter
from datetime import date, datetime, time, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.timezone import local_today
from app.models import ExerciseResult, ExpressionAttempt, ReviewLog, UserVocabMastery, WordDrawing
from app.services.version_service import version_entries, version_entry_ids

PERIODS = (7, 30, 90)
TABS = ("vocab", "listening", "writing", "grammar", "classifiers", "expression", "drawings")
EXERCISE_TABS = ("listening", "writing", "grammar", "classifiers")
# A card left open for longer is counted as 2 minutes (the user was away).
MAX_CARD_MS = 120_000


def _local(naive_utc: datetime, tz: ZoneInfo) -> datetime:
    return naive_utc.replace(tzinfo=timezone.utc).astimezone(tz)


def _utc_start(day: date, tz: ZoneInfo) -> datetime:
    return datetime.combine(day, time.min, tzinfo=tz).astimezone(timezone.utc).replace(tzinfo=None)


def study_stats(
    db: Session,
    user_id: int,
    *,
    version: str,
    days: int,
    tz: ZoneInfo,
    now_utc: datetime | None = None,
) -> dict[str, Any]:
    now_naive = (now_utc or datetime.now(timezone.utc)).astimezone(timezone.utc).replace(tzinfo=None)
    today = local_today(tz, now_naive)
    first_day = today - timedelta(days=days - 1)
    since = _utc_start(first_day, tz)
    dates = [first_day + timedelta(days=i) for i in range(days)]

    per_day: dict[str, Counter] = {tab: Counter() for tab in TABS}
    hours: Counter = Counter()
    weekdays: Counter = Counter()
    card_ms: Counter = Counter()
    timed_cards: Counter = Counter()

    def add(tab: str, when: datetime, n: int = 1) -> None:
        local = _local(when, tz)
        per_day[tab][local.date()] += n
        hours[local.hour] += n
        weekdays[local.weekday()] += n

    for reviewed_at, elapsed_ms in db.execute(
        select(ReviewLog.reviewed_at, ReviewLog.elapsed_ms).where(
            ReviewLog.user_id == user_id, ReviewLog.reviewed_at >= since
        )
    ):
        add("vocab", reviewed_at)
        if elapsed_ms is not None and elapsed_ms > 0:
            day = _local(reviewed_at, tz).date()
            card_ms[day] += min(int(elapsed_ms), MAX_CARD_MS)
            timed_cards[day] += 1

    for created_at, section, total in db.execute(
        select(ExerciseResult.created_at, ExerciseResult.section, ExerciseResult.total).where(
            ExerciseResult.user_id == user_id, ExerciseResult.created_at >= since
        )
    ):
        if section in EXERCISE_TABS:
            add(section, created_at, int(total or 0))

    for (created_at,) in db.execute(
        select(ExpressionAttempt.created_at).where(
            ExpressionAttempt.user_id == user_id, ExpressionAttempt.created_at >= since
        )
    ):
        add("expression", created_at)

    for (created_at,) in db.execute(
        select(WordDrawing.created_at).where(WordDrawing.user_id == user_id, WordDrawing.created_at >= since)
    ):
        add("drawings", created_at)

    activity = [{"date": d, **{tab: per_day[tab].get(d, 0) for tab in TABS}} for d in dates]
    totals = {tab: sum(per_day[tab].values()) for tab in TABS}
    active_days = sum(1 for row in activity if any(row[tab] for tab in TABS))

    words = _words(db, user_id, version=version, dates=dates, since=since, tz=tz)
    time_per_day = [
        {"date": d, "minutes": round(card_ms.get(d, 0) / 60_000, 1), "cards": timed_cards.get(d, 0)} for d in dates
    ]

    return {
        "days": days,
        "from_date": first_day,
        "to_date": today,
        "version": version,
        "active_days": active_days,
        "totals": totals,
        "activity": activity,
        "words": words,
        "time": {
            "per_day": time_per_day,
            "total_minutes": round(sum(card_ms.values()) / 60_000, 1),
            "by_hour": [{"hour": h, "count": hours.get(h, 0)} for h in range(24)],
            "by_weekday": [{"weekday": w, "count": weekdays.get(w, 0)} for w in range(7)],
        },
    }


def _words(
    db: Session, user_id: int, *, version: str, dates: list[date], since: datetime, tz: ZoneInfo
) -> dict[str, Any]:
    """Words of `version` seen for the first time per day, cumulated, and the level totals."""
    version_rows = db.execute(version_entries(version)).all()
    in_version = {row.entry_id for row in version_rows}
    by_level: Counter = Counter(row.level for row in version_rows if row.level is not None)

    first_seen = db.execute(
        select(UserVocabMastery.entry_id, UserVocabMastery.created_at).where(UserVocabMastery.user_id == user_id)
    ).all()
    before = 0
    per_day: Counter = Counter()
    for entry_id, created_at in first_seen:
        if entry_id not in in_version:
            continue
        if created_at < since:
            before += 1
        else:
            per_day[_local(created_at, tz).date()] += 1

    running = before
    series = []
    for d in dates:
        running += per_day.get(d, 0)
        series.append({"date": d, "new": per_day.get(d, 0), "seen": running})

    cumulative, levels = 0, []
    for level in sorted(by_level):
        cumulative += by_level[level]
        levels.append({"level": level, "total": cumulative})

    reviewed = db.execute(
        select(func.count(func.distinct(ReviewLog.entry_id))).where(
            ReviewLog.user_id == user_id, ReviewLog.reviewed_at >= since,
            ReviewLog.entry_id.in_(version_entry_ids(version)),
        )
    ).scalar()
    return {
        "per_day": series,
        "seen_before": before,
        "seen_total": running,
        "new_in_period": running - before,
        "reviewed_in_period": int(reviewed or 0),
        "level_totals": levels,
    }
