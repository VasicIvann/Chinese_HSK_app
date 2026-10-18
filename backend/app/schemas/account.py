"""Pydantic schemas for the Account dashboard endpoint."""

from __future__ import annotations

from datetime import date, datetime

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
