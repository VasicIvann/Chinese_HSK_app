"""Pydantic schemas for the Expression écrite endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


HSKLevel = Literal[1, 2, 3]


class SubjectItem(BaseModel):
    subject: str
    keywords: list[str] = Field(default_factory=list)


class SubjectGenerateRequest(BaseModel):
    level: HSKLevel
    theme: str | None = Field(default=None, max_length=120)


class SubjectGenerateResponse(BaseModel):
    subject: str
    keywords: list[str] = Field(default_factory=list)
    quota_remaining: int


class CorrectRequest(BaseModel):
    level: HSKLevel
    subject: str = Field(min_length=3, max_length=500)
    user_text: str = Field(min_length=1, max_length=2000)


class ExpressionErrorItem(BaseModel):
    type: str
    segment: str
    correction: str
    explanation: str


class CorrectionPayload(BaseModel):
    score: int | None = None
    corrected_version: str = ""
    pinyin: str = ""
    french_translation: str = ""
    errors: list[ExpressionErrorItem] = Field(default_factory=list)
    vocabulary_mistakes: list[str] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    next_step_advice: str = ""


class ExpressionAttemptItem(BaseModel):
    id: int
    hsk_level: int
    subject: str
    user_text: str
    correction: dict[str, Any]
    score: int | None = None
    tokens_input: int = 0
    tokens_output: int = 0
    model_id: str = ""
    created_at: datetime


class QuotaStatus(BaseModel):
    kind: str
    count: int
    limit: int
    remaining: int


class QuotaResponse(BaseModel):
    correction: QuotaStatus
    subject_generation: QuotaStatus
