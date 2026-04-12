"""SQLAlchemy ORM models for quizzes and entries."""

from __future__ import annotations

from datetime import datetime

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
    mastery_records = relationship(
        "UserVocabMastery",
        back_populates="entry",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class User(Base):
    """Registered user account."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    locale = Column(String(10), nullable=False, default="fr")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    settings = relationship(
        "UserSetting",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    vocab_mastery = relationship(
        "UserVocabMastery",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class UserSetting(Base):
    """Key-value user preference storage."""

    __tablename__ = "user_settings"
    __table_args__ = (UniqueConstraint("user_id", "key", name="uq_user_setting"),)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    key = Column(String(100), nullable=False)
    value = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    user = relationship("User", back_populates="settings")


class UserVocabMastery(Base):
    """Per-user mastery state for a vocabulary entry."""

    __tablename__ = "user_vocab_mastery"
    __table_args__ = (UniqueConstraint("user_id", "entry_id", name="uq_user_entry_mastery"),)

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

    user = relationship("User", back_populates="vocab_mastery")
    entry = relationship("Entry", back_populates="mastery_records")
