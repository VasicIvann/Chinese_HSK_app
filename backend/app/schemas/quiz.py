"""Pydantic schemas for quizzes and entries."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class QuizPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    key: str
    title: str
    description: str | None = None
    level: int | None = None


class EntryPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    quiz_id: int
    hanzi: str
    pinyin: str
    translation: str
    alt_translations: str | None = None
    tags: str | None = None
