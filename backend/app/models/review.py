"""One row per answer given in a quiz: the full review history.

`UserVocabMastery` only keeps the latest state of each word; this table keeps
every rating so the dashboard can compute streaks, real daily activity,
success rate and retention.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, Integer, String

from app.db.base import Base


class ReviewLog(Base):
    __tablename__ = "review_log"
    __table_args__ = (
        Index("ix_review_log_user_reviewed_at", "user_id", "reviewed_at"),
        {"extend_existing": True},
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    entry_id = Column(Integer, ForeignKey("entries.id", ondelete="CASCADE"), nullable=False)
    rating = Column(Integer, nullable=False)  # 1 again, 2 hard, 3 good, 4 easy
    was_new = Column(Boolean, nullable=False, default=False)  # first time the user rated it
    was_due = Column(Boolean, nullable=False, default=False)  # FSRS due date had passed
    mode = Column(String(32), nullable=True)  # "auto-assess" | "pinyin-input"
    elapsed_ms = Column(Integer, nullable=True)  # time spent on the card
    reviewed_at = Column(DateTime, default=datetime.utcnow, nullable=False)  # naive UTC
