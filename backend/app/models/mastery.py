"""Per-user mastery state for vocabulary entries, with FSRS scheduling fields."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)

from app.db.base import Base


class UserVocabMastery(Base):
    __tablename__ = "user_vocab_mastery"
    __table_args__ = (
        UniqueConstraint("user_id", "entry_id", name="uq_user_entry_mastery"),
        {"extend_existing": True},
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    entry_id = Column(Integer, ForeignKey("entries.id", ondelete="CASCADE"), nullable=False)

    # Legacy aggregates kept for dashboards.
    status = Column(String(32), nullable=False)
    confidence_score = Column(Float, nullable=False, default=0.0)
    review_count = Column(Integer, nullable=False, default=1)
    last_seen_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # FSRS state, persisted as a serialized scheduler card.
    fsrs_state = Column(Integer, nullable=True)
    fsrs_step = Column(Integer, nullable=True)
    fsrs_stability = Column(Float, nullable=True)
    fsrs_difficulty = Column(Float, nullable=True)
    fsrs_due_at = Column(DateTime, nullable=True, index=True)
    fsrs_last_review_at = Column(DateTime, nullable=True)
    fsrs_last_rating = Column(Integer, nullable=True)
