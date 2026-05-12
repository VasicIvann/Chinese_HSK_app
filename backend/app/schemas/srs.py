"""Pydantic schemas for the SRS endpoints."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.services.srs_service import RatingEnum


class RateRequest(BaseModel):
    entry_id: int = Field(ge=1)
    rating: RatingEnum


class MasterySnapshotResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    entry_id: int
    rating: RatingEnum
    rating_value: int
    confidence_score: float
    review_count: int
    last_seen_at: datetime
    next_review_at: datetime | None = None
    stability_days: float | None = None
    difficulty: float | None = None
    state: int | None = None


class DueEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    quiz_id: int
    hanzi: str
    pinyin: str
    translation: str
    alt_translations: str | None = None
    tags: str | None = None


class StatsResponse(BaseModel):
    due: int
    new: int
    upcoming: int
