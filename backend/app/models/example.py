"""Claude-generated example sentences for a vocabulary entry, stored per user."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, Text

from app.db.base import Base


class WordExample(Base):
    __tablename__ = "word_examples"
    __table_args__ = (
        Index("ix_word_examples_user_entry", "user_id", "entry_id"),
        {"extend_existing": True},
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    entry_id = Column(Integer, ForeignKey("entries.id", ondelete="CASCADE"), nullable=False)
    hsk_level = Column(Integer, nullable=True)
    sentence = Column(Text, nullable=False)
    pinyin = Column(Text, nullable=False, default="")
    translation = Column(Text, nullable=False, default="")
    meaning_in_sentence = Column(Text, nullable=False, default="")
    general_meaning = Column(Text, nullable=False, default="")
    tokens_input = Column(Integer, nullable=False, default=0)
    tokens_output = Column(Integer, nullable=False, default=0)
    model_id = Column(String(64), nullable=False, default="")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
