"""Pydantic schemas for the vocabulary example endpoints."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ExampleGenerateRequest(BaseModel):
    entry_id: int = Field(ge=1)


class WordExampleItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    entry_id: int
    hsk_level: int | None = None
    sentence: str
    pinyin: str = ""
    translation: str = ""
    meaning_in_sentence: str = ""
    general_meaning: str = ""
    decomposition: str = ""
    created_at: datetime


class ExampleGenerateResponse(BaseModel):
    example: WordExampleItem
    quota_remaining: int
