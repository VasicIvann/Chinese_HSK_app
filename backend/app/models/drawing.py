"""Handwriting practice: PNG drawings of a word, saved per user and entry."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, LargeBinary

from app.db.base import Base


class WordDrawing(Base):
    __tablename__ = "word_drawings"
    __table_args__ = (
        Index("ix_word_drawings_user_entry", "user_id", "entry_id"),
        Index("ix_word_drawings_user_created", "user_id", "created_at"),
        {"extend_existing": True},
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    entry_id = Column(Integer, ForeignKey("entries.id", ondelete="CASCADE"), nullable=False)
    image_png = Column(LargeBinary, nullable=False)
    width = Column(Integer, nullable=False)
    height = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
