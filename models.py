"""SQLAlchemy ORM models for quizzes and entries."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from db import Base


class Quiz(Base):
    """Represents a quiz dataset (e.g., HSK1, HSK2)."""

    __tablename__ = "quizzes"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(50), unique=True, nullable=False)
    title = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    level = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    entries = relationship(
        "Entry", back_populates="quiz", cascade="all, delete-orphan", lazy="selectin"
    )


class Entry(Base):
    """Represents a vocabulary entry belonging to a quiz."""

    __tablename__ = "entries"

    id = Column(Integer, primary_key=True, index=True)
    quiz_id = Column(Integer, ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False)
    hanzi = Column(String(32), nullable=False)
    pinyin = Column(String(64), nullable=False)
    translation = Column(String(255), nullable=False)
    alt_translations = Column(Text, nullable=True)
    tags = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    quiz = relationship("Quiz", back_populates="entries")
