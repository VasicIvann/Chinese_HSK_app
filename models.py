"""SQLAlchemy ORM models for quizzes and entries."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import sys

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import clear_mappers

from db import Base


# See db.py note: keep one models module object even if imported with
# different names (models vs chinese_hsk_app.models on Streamlit Cloud).
_PKG_NAME = Path(__file__).resolve().parent.name
if __name__ == "models":
    sys.modules.setdefault(f"{_PKG_NAME}.models", sys.modules[__name__])
elif __name__.endswith(".models"):
    sys.modules.setdefault("models", sys.modules[__name__])

# Streamlit reload/import path quirks can leave stale mapper state in-process.
# Clearing mappers before class declarations prevents reverse_property conflicts.
clear_mappers()


class Quiz(Base):
    """Represents a quiz dataset (e.g., HSK1, HSK2)."""

    __tablename__ = "quizzes"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(50), unique=True, nullable=False)
    title = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    level = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

class Entry(Base):
    """Represents a vocabulary entry belonging to a quiz."""

    __tablename__ = "entries"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True)
    quiz_id = Column(Integer, ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False)
    hanzi = Column(String(32), nullable=False)
    pinyin = Column(String(64), nullable=False)
    translation = Column(String(255), nullable=False)
    alt_translations = Column(Text, nullable=True)
    tags = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

class User(Base):
    """Registered user account."""

    __tablename__ = "users"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    locale = Column(String(10), nullable=False, default="fr")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

class UserSetting(Base):
    """Key-value user preference storage."""

    __tablename__ = "user_settings"
    __table_args__ = (
        UniqueConstraint("user_id", "key", name="uq_user_setting"),
        {"extend_existing": True},
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    key = Column(String(100), nullable=False)
    value = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

class UserVocabMastery(Base):
    """Per-user mastery state for a vocabulary entry, with FSRS scheduling fields."""

    __tablename__ = "user_vocab_mastery"
    __table_args__ = (
        UniqueConstraint("user_id", "entry_id", name="uq_user_entry_mastery"),
        {"extend_existing": True},
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    entry_id = Column(Integer, ForeignKey("entries.id", ondelete="CASCADE"), nullable=False)
    # Legacy fields kept for compatibility and dashboards.
    status = Column(String(32), nullable=False)
    confidence_score = Column(Float, nullable=False, default=0.0)
    review_count = Column(Integer, nullable=False, default=1)
    last_seen_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
    # FSRS state, persisted as serialized scheduler card.
    fsrs_state = Column(Integer, nullable=True)
    fsrs_step = Column(Integer, nullable=True)
    fsrs_stability = Column(Float, nullable=True)
    fsrs_difficulty = Column(Float, nullable=True)
    fsrs_due_at = Column(DateTime, nullable=True, index=True)
    fsrs_last_review_at = Column(DateTime, nullable=True)
    fsrs_last_rating = Column(Integer, nullable=True)


class ExpressionAttempt(Base):
    """A single written-expression submission and its LLM correction."""

    __tablename__ = "expression_attempts"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    hsk_level = Column(Integer, nullable=False)
    subject = Column(Text, nullable=False)
    user_text = Column(Text, nullable=False)
    correction_json = Column(Text, nullable=False)
    score = Column(Integer, nullable=True)
    tokens_input = Column(Integer, nullable=False, default=0)
    tokens_output = Column(Integer, nullable=False, default=0)
    model_id = Column(String(64), nullable=False, default="")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)


class UserDailyUsage(Base):
    """Aggregates per-user LLM usage for daily quota enforcement."""

    __tablename__ = "user_daily_usage"
    __table_args__ = (
        UniqueConstraint("user_id", "usage_date", "kind", name="uq_user_daily_usage"),
        {"extend_existing": True},
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    usage_date = Column(Date, nullable=False)
    kind = Column(String(32), nullable=False)
    count = Column(Integer, nullable=False, default=0)
    tokens_input = Column(Integer, nullable=False, default=0)
    tokens_output = Column(Integer, nullable=False, default=0)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
