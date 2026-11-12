"""Pydantic schemas for the Account dashboard endpoint."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel


class MasteryDistribution(BaseModel):
    mastered: int  # confidence_score >= 0.9 (FSRS Review state with high stability)
    learning: int  # at least 1 review, not yet mastered
    new: int       # never reviewed by the user
    total_entries: int


class ActivityCell(BaseModel):
    date: date
    count: int


class QuizDailyPoint(BaseModel):
    date: date
    avg_rating: float  # 1..4 scale (FSRS Again/Hard/Good/Easy)
    count: int


class ExpressionScorePoint(BaseModel):
    date: datetime
    score: int


class ProfileSummary(BaseModel):
    email: str
    locale: str
    joined_at: datetime
    total_reviews: int
    total_expressions: int


class LevelProgress(BaseModel):
    quiz_key: str
    title: str
    level: int | None = None
    total: int
    mastered: int
    learning: int
    new: int


class StreakSummary(BaseModel):
    current: int  # consecutive days ending today (or yesterday if not studied yet today)
    best: int
    studied_today: bool


class SuccessDailyPoint(BaseModel):
    date: date
    rate: float | None  # 0..1
    count: int


class SuccessRate(BaseModel):
    last_7_days: float | None  # 0..1, None without reviews
    last_30_days: float | None
    reviews_7_days: int
    reviews_30_days: int
    daily: list[SuccessDailyPoint]
    tracking_since: date | None  # first day recorded in the review history


class ForecastDay(BaseModel):
    date: date
    count: int


class UpcomingReviews(BaseModel):
    due_now: int
    due_today: int  # includes overdue
    due_tomorrow: int
    due_next_7_days: int  # cumulative, includes overdue
    forecast: list[ForecastDay]  # day 0 includes overdue


class AccountOverview(BaseModel):
    profile: ProfileSummary
    mastery: MasteryDistribution
    activity_heatmap: list[ActivityCell]
    quiz_progression: list[QuizDailyPoint]
    expression_progression: list[ExpressionScorePoint]
    level_progress: list[LevelProgress]
    streak: StreakSummary
    success_rate: SuccessRate
    upcoming: UpcomingReviews
    # The HSK version the word-level numbers above are computed for.
    hsk_version: str = "3.0"


class AccountSettings(BaseModel):
    hsk_version: Literal["2.0", "3.0"]
    # Vocabulary quiz (self-assessment mode): pinyin shown from the start of every card.
    pinyin_locked: bool = False


class AccountSettingsUpdate(BaseModel):
    """Partial update: only the fields sent are changed."""

    hsk_version: Literal["2.0", "3.0"] | None = None
    pinyin_locked: bool | None = None


# --------------------------------------------------------------------------- /account/stats


class TabActivityDay(BaseModel):
    date: date
    vocab: int  # cards answered
    listening: int  # questions answered (Écoute)
    writing: int  # questions answered (Écriture HSK)
    grammar: int  # questions answered (Grammaire)
    classifiers: int  # questions answered (Classificateurs)
    tones: int  # words answered (Tons)
    expression: int  # texts corrected
    drawings: int  # drawings saved


class TabTotals(BaseModel):
    vocab: int
    listening: int
    writing: int
    grammar: int
    classifiers: int
    tones: int
    expression: int
    drawings: int


class WordsDay(BaseModel):
    date: date
    new: int  # words of the version seen for the first time that day
    seen: int  # cumulative words seen at the end of the day


class LevelTotal(BaseModel):
    level: int
    total: int  # words of levels 1..level in the version


class WordsStats(BaseModel):
    per_day: list[WordsDay]
    seen_before: int
    seen_total: int
    new_in_period: int
    reviewed_in_period: int  # distinct words reviewed during the period
    level_totals: list[LevelTotal]


class TimeDay(BaseModel):
    date: date
    minutes: float  # time on vocabulary cards (each card capped at 2 min)
    cards: int  # cards with a recorded time


class HourCount(BaseModel):
    hour: int
    count: int


class WeekdayCount(BaseModel):
    weekday: int  # 0 = Monday
    count: int


class TimeStats(BaseModel):
    per_day: list[TimeDay]
    total_minutes: float
    by_hour: list[HourCount]
    by_weekday: list[WeekdayCount]


class StudyStats(BaseModel):
    days: int
    from_date: date
    to_date: date
    version: str
    active_days: int
    totals: TabTotals
    activity: list[TabActivityDay]
    words: WordsStats
    time: TimeStats
