"""Expression écrite attempts + daily quota tracking."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint

from app.db.base import Base


class ExpressionAttempt(Base):
    __tablename__ = "expression_attempts"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
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
