"""HSK-format exercises (listening, writing, grammar): results and generated items."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, Text

from app.db.base import Base


class ExerciseResult(Base):
    """One finished practice set: a part of a paper, a whole section, or a grammar point."""

    __tablename__ = "exercise_results"
    __table_args__ = (
        Index("ix_exercise_results_user_part", "user_id", "section", "level", "part_key"),
        {"extend_existing": True},
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    version = Column(String(8), nullable=False)
    level = Column(Integer, nullable=False)
    section = Column(String(16), nullable=False)  # listening | writing | grammar
    part_key = Column(String(32), nullable=False)  # "L1", "W2", "all", or a grammar point id
    score = Column(Integer, nullable=False)
    total = Column(Integer, nullable=False)
    # JSON list of {"id": item id, "correct": bool}: lets the next sets prefer unseen items.
    details = Column(Text, nullable=False, default="[]")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class GeneratedExercise(Base):
    """An item written by Claude on demand ("Nouvelle série"), kept for the user."""

    __tablename__ = "generated_exercises"
    __table_args__ = (
        Index("ix_generated_exercises_user_level_type", "user_id", "level", "item_type"),
        {"extend_existing": True},
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    version = Column(String(8), nullable=False)
    level = Column(Integer, nullable=False)
    item_type = Column(String(32), nullable=False)
    payload = Column(Text, nullable=False)  # the item, same JSON shape as the bank's
    model_id = Column(String(64), nullable=False, default="")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
