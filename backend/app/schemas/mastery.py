"""Pydantic schemas for the mastery dashboard endpoint."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class MasteryItem(BaseModel):
    quiz_key: str
    quiz_title: str
    entry_id: int
    hanzi: str
    pinyin: str
    translation: str
    status: str
    confidence_score: float
    review_count: int
    last_seen_at: datetime
    next_review_at: datetime | None = None
    stability_days: float | None = None
    last_rating: int | None = None
