"""SQLAlchemy ORM models for quizzes and entries."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import sys

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)

from db import Base


# See db.py note: keep one models module object even if imported with
# different names (models vs chinese_hsk_app.models on Streamlit Cloud).
_PKG_NAME = Path(__file__).resolve().parent.name
if __name__ == "models":
    sys.modules.setdefault(f"{_PKG_NAME}.models", sys.modules[__name__])
elif __name__.endswith(".models"):
    sys.modules.setdefault("models", sys.modules[__name__])


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
    """Per-user mastery state for a vocabulary entry."""

    __tablename__ = "user_vocab_mastery"
    __table_args__ = (
        UniqueConstraint("user_id", "entry_id", name="uq_user_entry_mastery"),
        {"extend_existing": True},
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    entry_id = Column(Integer, ForeignKey("entries.id", ondelete="CASCADE"), nullable=False)
    status = Column(String(32), nullable=False)
    confidence_score = Column(Float, nullable=False, default=0.0)
    review_count = Column(Integer, nullable=False, default=1)
    last_seen_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

