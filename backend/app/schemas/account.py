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


class AccountOverview(BaseModel):
    profile: ProfileSummary
    mastery: MasteryDistribution
    activity_heatmap: list[ActivityCell]
    quiz_progression: list[QuizDailyPoint]
    expression_progression: list[ExpressionScorePoint]
