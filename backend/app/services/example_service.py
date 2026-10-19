"""Persistence helpers for Claude-generated vocabulary examples."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Entry, WordExample
from app.services.version_service import DEFAULT_VERSION, entry_level


def get_entry_with_level(
    db: Session, entry_id: int, version: str = DEFAULT_VERSION
) -> tuple[Entry, int | None] | None:
    """Return the entry and its HSK level in `version`, or None if it doesn't exist."""
    entry = db.get(Entry, entry_id)
    if entry is None:
        return None
    return entry, entry_level(db, entry_id, version)


def list_examples(db: Session, *, user_id: int, entry_id: int, limit: int = 50) -> list[WordExample]:
    """The user's examples for one entry, newest first."""
    stmt = (
        select(WordExample)
        .where(WordExample.user_id == user_id, WordExample.entry_id == entry_id)
        .order_by(WordExample.created_at.desc(), WordExample.id.desc())
        .limit(limit)
    )
    return list(db.execute(stmt).scalars().all())


def save_example(
    db: Session,
    *,
    user_id: int,
    entry_id: int,
    hsk_level: int | None,
    example: dict[str, str],
    tokens_input: int,
    tokens_output: int,
    model_id: str,
) -> WordExample:
    row = WordExample(
        user_id=user_id,
        entry_id=entry_id,
        hsk_level=hsk_level,
        sentence=example["sentence"],
        pinyin=example.get("pinyin", ""),
        translation=example.get("translation", ""),
        meaning_in_sentence=example.get("meaning_in_sentence", ""),
        general_meaning=example.get("general_meaning", ""),
        decomposition=example.get("decomposition", ""),
        tokens_input=tokens_input,
        tokens_output=tokens_output,
        model_id=model_id[:64],
        created_at=datetime.utcnow(),
    )
    db.add(row)
    db.flush()
    return row


__all__ = ["get_entry_with_level", "list_examples", "save_example"]
