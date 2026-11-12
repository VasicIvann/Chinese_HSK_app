"""Quiz datasets and their vocabulary entries."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, Integer, String, Text

from app.db.base import Base


class Quiz(Base):
    __tablename__ = "quizzes"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(50), unique=True, nullable=False)
    title = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    level = Column(Integer, nullable=True)
    # HSK syllabus the quiz belongs to: "3.0" (2025 syllabus) or "2.0" (2012 lists).
    version = Column(String(8), nullable=False, default="3.0", server_default="3.0")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )


class QuizEntry(Base):
    """Which quizzes (one level per HSK version) a word belongs to.

    A word is one Entry whatever the version, so the user's progress on it
    (mastery, review log, examples, drawings) is shared by both versions; only
    its level changes. `Entry.quiz_id` is just the word's "home" quiz.
    """

    __tablename__ = "quiz_entries"
    __table_args__ = (
        Index("ix_quiz_entries_entry", "entry_id"),
        {"extend_existing": True},
    )

    quiz_id = Column(Integer, ForeignKey("quizzes.id", ondelete="CASCADE"), primary_key=True)
    entry_id = Column(Integer, ForeignKey("entries.id", ondelete="CASCADE"), primary_key=True)


class Entry(Base):
    __tablename__ = "entries"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True)
    quiz_id = Column(Integer, ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False)
    hanzi = Column(String(32), nullable=False)
    pinyin = Column(String(64), nullable=False)
    translation = Column(String(255), nullable=False)
    alt_translations = Column(Text, nullable=True)
    tags = Column(String(255), nullable=True)
    # False when the word is in no version any more (history kept, hidden everywhere).
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
