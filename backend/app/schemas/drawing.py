"""Pydantic schemas for the handwriting-practice drawings."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class DrawingCreateRequest(BaseModel):
    entry_id: int = Field(ge=1)
    # A "data:image/png;base64,..." URL straight from canvas.toDataURL().
    image: str = Field(min_length=32, max_length=1_500_000)


class DrawingItem(BaseModel):
    id: int
    entry_id: int
    # Ready to use as <img src>: the API is called with a Bearer token, so the
    # image travels inline instead of through a separate (unauthenticated) URL.
    image: str
    width: int
    height: int
    created_at: datetime


class DrawingWordGroup(BaseModel):
    entry_id: int
    hanzi: str
    pinyin: str
    translation: str
    hsk_level: int | None = None
    count: int
    latest_at: datetime
    drawings: list[DrawingItem]


class DrawingGalleryResponse(BaseModel):
    total_drawings: int
    total_words: int
    words: list[DrawingWordGroup]
    has_more: bool
