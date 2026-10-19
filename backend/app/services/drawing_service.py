"""Persistence helpers for handwriting-practice drawings."""

from __future__ import annotations

import base64
import binascii
import struct
from datetime import datetime

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models import Entry, Quiz, WordDrawing

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
DATA_URL_PREFIX = "data:image/png;base64,"
MAX_IMAGE_BYTES = 1_000_000
MAX_WIDTH, MAX_HEIGHT = 4096, 1024
MAX_DRAWINGS_PER_USER = 2000
GALLERY_PREVIEW = 4


class InvalidDrawingError(ValueError):
    """The uploaded payload is not a usable PNG."""


def decode_png(data_url: str) -> tuple[bytes, int, int]:
    """Decode a canvas data URL and return (png bytes, width, height)."""
    if not data_url.startswith(DATA_URL_PREFIX):
        raise InvalidDrawingError("Format attendu : image PNG.")
    try:
        raw = base64.b64decode(data_url[len(DATA_URL_PREFIX):], validate=True)
    except (binascii.Error, ValueError) as exc:
        raise InvalidDrawingError("Image illisible.") from exc
    if len(raw) > MAX_IMAGE_BYTES:
        raise InvalidDrawingError("Image trop lourde.")
    # PNG = signature, then the IHDR chunk (length, "IHDR", width, height, ...).
    if len(raw) < 24 or not raw.startswith(PNG_SIGNATURE) or raw[12:16] != b"IHDR":
        raise InvalidDrawingError("Format attendu : image PNG.")
    width, height = struct.unpack(">II", raw[16:24])
    if not (0 < width <= MAX_WIDTH and 0 < height <= MAX_HEIGHT):
        raise InvalidDrawingError("Dimensions d'image invalides.")
    return raw, width, height


def to_data_url(png: bytes) -> str:
    return DATA_URL_PREFIX + base64.b64encode(png).decode("ascii")


def to_item(row: WordDrawing) -> dict:
    return {
        "id": row.id,
        "entry_id": row.entry_id,
        "image": to_data_url(row.image_png),
        "width": row.width,
        "height": row.height,
        "created_at": row.created_at,
    }


def count_for_user(db: Session, user_id: int) -> int:
    return int(db.execute(select(func.count(WordDrawing.id)).where(WordDrawing.user_id == user_id)).scalar() or 0)


def save_drawing(db: Session, *, user_id: int, entry_id: int, png: bytes, width: int, height: int) -> WordDrawing:
    row = WordDrawing(
        user_id=user_id,
        entry_id=entry_id,
        image_png=png,
        width=width,
        height=height,
        created_at=datetime.utcnow(),
    )
    db.add(row)
    db.flush()
    return row


def list_for_entry(db: Session, *, user_id: int, entry_id: int, limit: int = 100) -> list[WordDrawing]:
    """The user's drawings of one entry, newest first."""
    stmt = (
        select(WordDrawing)
        .where(WordDrawing.user_id == user_id, WordDrawing.entry_id == entry_id)
        .order_by(WordDrawing.created_at.desc(), WordDrawing.id.desc())
        .limit(limit)
    )
    return list(db.execute(stmt).scalars().all())


def delete_drawing(db: Session, *, user_id: int, drawing_id: int) -> bool:
    result = db.execute(
        delete(WordDrawing).where(WordDrawing.id == drawing_id, WordDrawing.user_id == user_id)
    )
    return (result.rowcount or 0) > 0


def gallery(db: Session, *, user_id: int, limit: int, offset: int) -> dict:
    """Drawings grouped by word, most recently drawn word first, with a preview of
    the latest drawings of each word."""
    total_drawings, total_words = db.execute(
        select(func.count(WordDrawing.id), func.count(func.distinct(WordDrawing.entry_id))).where(
            WordDrawing.user_id == user_id
        )
    ).one()

    latest = func.max(WordDrawing.created_at).label("latest_at")
    groups = db.execute(
        select(
            WordDrawing.entry_id,
            func.count(WordDrawing.id).label("count"),
            latest,
            Entry.hanzi,
            Entry.pinyin,
            Entry.translation,
            Quiz.level,
        )
        .join(Entry, Entry.id == WordDrawing.entry_id)
        .join(Quiz, Quiz.id == Entry.quiz_id)
        .where(WordDrawing.user_id == user_id)
        .group_by(WordDrawing.entry_id, Entry.hanzi, Entry.pinyin, Entry.translation, Quiz.level)
        .order_by(latest.desc(), WordDrawing.entry_id.desc())
        .limit(limit + 1)
        .offset(offset)
    ).all()
    has_more = len(groups) > limit
    groups = groups[:limit]

    previews: dict[int, list[WordDrawing]] = {g.entry_id: [] for g in groups}
    if groups:
        rank = (
            func.row_number()
            .over(
                partition_by=WordDrawing.entry_id,
                order_by=(WordDrawing.created_at.desc(), WordDrawing.id.desc()),
            )
            .label("rank")
        )
        ranked = (
            select(WordDrawing.id, rank)
            .where(WordDrawing.user_id == user_id, WordDrawing.entry_id.in_(list(previews)))
            .subquery()
        )
        rows = db.execute(
            select(WordDrawing)
            .join(ranked, ranked.c.id == WordDrawing.id)
            .where(ranked.c.rank <= GALLERY_PREVIEW)
            .order_by(WordDrawing.created_at.desc(), WordDrawing.id.desc())
        ).scalars()
        for row in rows:
            previews[row.entry_id].append(row)

    return {
        "total_drawings": int(total_drawings or 0),
        "total_words": int(total_words or 0),
        "has_more": has_more,
        "words": [
            {
                "entry_id": g.entry_id,
                "hanzi": g.hanzi,
                "pinyin": g.pinyin,
                "translation": g.translation,
                "hsk_level": g.level,
                "count": int(g.count),
                "latest_at": g.latest_at,
                "drawings": [to_item(d) for d in previews[g.entry_id]],
            }
            for g in groups
        ],
    }
