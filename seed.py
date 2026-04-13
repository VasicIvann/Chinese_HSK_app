"""Database seeding utilities for quiz datasets."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict, Iterable, List

from sqlalchemy import select

from db import DATA_DIR, init_db, get_session
from models import Entry, Quiz


QUIZ_DEFINITIONS: List[Dict[str, str | int | None]] = [
    {
        "key": "HSK1",
        "title": "HSK 1",
        "description": "Vocabulaire officiel HSK niveau 1.",
        "level": 1,
    },
    {
        "key": "HSK2",
        "title": "HSK 2",
        "description": "Vocabulaire officiel HSK niveau 2.",
        "level": 2,
    },
    {
        "key": "HSK3",
        "title": "HSK 3",
        "description": "Vocabulaire officiel HSK niveau 3.",
        "level": 3,
    },
]

CSV_FILES = {
    "HSK1": DATA_DIR / "hsk1.csv",
    "HSK2": DATA_DIR / "hsk2.csv",
    "HSK3": DATA_DIR / "hsk3.csv",
}


def load_csv_entries(path: Path) -> Iterable[Dict[str, str]]:
    """Yield entries from a CSV file."""
    if not path.exists():
        raise FileNotFoundError(f"CSV file not found: {path}")

    with path.open(encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            normalized_row = {
                key.lstrip("\ufeff").strip(): (value or "")
                for key, value in row.items()
                if key is not None
            }
            # Normalize keys and strip whitespace.
            yield {
                "hanzi": normalized_row.get("hanzi", "").strip(),
                "pinyin": normalized_row.get("pinyin", "").strip(),
                "translation": normalized_row.get("translation", "").strip(),
                "alt_translations": normalized_row.get("alt_translations", "").strip(),
                "tags": normalized_row.get("tags", "").strip(),
            }


def ensure_seeded() -> None:
    """Create tables and seed missing quizzes/entries idempotently."""
    init_db()

    with get_session() as session:
        existing_by_key = {
            quiz.key: quiz for quiz in session.execute(select(Quiz)).scalars().all()
        }

        for definition in QUIZ_DEFINITIONS:
            csv_path = CSV_FILES[definition["key"]]
            try:
                entries = list(load_csv_entries(csv_path))
            except FileNotFoundError as exc:
                print(exc)
                continue
            if not entries:
                print(f"No entries found in {csv_path}, skipping.")
                continue

            expected_count = sum(
                1
                for entry in entries
                if entry["hanzi"] and entry["pinyin"] and entry["translation"]
            )

            quiz = existing_by_key.get(definition["key"])
            if not quiz:
                quiz = Quiz(
                    key=definition["key"],
                    title=definition["title"],
                    description=definition["description"],
                    level=definition["level"],
                )
                session.add(quiz)
                session.flush()
                existing_by_key[definition["key"]] = quiz
            else:
                # Keep metadata aligned if definitions evolve.
                quiz.title = str(definition["title"])
                quiz.description = (
                    str(definition["description"])
                    if definition["description"] is not None
                    else None
                )
                quiz.level = int(definition["level"]) if definition["level"] is not None else None

            existing_count = session.execute(
                select(Entry).where(Entry.quiz_id == quiz.id)
            ).scalars().all()
            if len(existing_count) >= expected_count:
                continue

            for entry in entries:
                if not entry["hanzi"] or not entry["pinyin"] or not entry["translation"]:
                    continue
                duplicate = session.execute(
                    select(Entry.id).where(
                        Entry.quiz_id == quiz.id,
                        Entry.hanzi == entry["hanzi"],
                        Entry.pinyin == entry["pinyin"],
                        Entry.translation == entry["translation"],
                    ).limit(1)
                ).first()
                if duplicate:
                    continue
                session.add(
                    Entry(
                        quiz_id=quiz.id,
                        hanzi=entry["hanzi"],
                        pinyin=entry["pinyin"],
                        translation=entry["translation"],
                        alt_translations=entry["alt_translations"] or None,
                        tags=entry["tags"] or None,
                        is_active=True,
                    )
                )
