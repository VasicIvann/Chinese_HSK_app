"""Database seeding utilities for quiz datasets."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict, Iterable, List

from sqlalchemy import func, select

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
]

CSV_FILES = {
    "HSK1": DATA_DIR / "hsk1.csv",
    "HSK2": DATA_DIR / "hsk2.csv",
}


def load_csv_entries(path: Path) -> Iterable[Dict[str, str]]:
    """Yield entries from a CSV file."""
    if not path.exists():
        raise FileNotFoundError(f"CSV file not found: {path}")

    with path.open(encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            # Normalize keys and strip whitespace.
            yield {
                "hanzi": row.get("hanzi", "").strip(),
                "pinyin": row.get("pinyin", "").strip(),
                "translation": row.get("translation", "").strip(),
                "alt_translations": row.get("alt_translations", "").strip(),
                "tags": row.get("tags", "").strip(),
            }


def ensure_seeded() -> None:
    """Create tables and seed initial data only if the database is empty."""
    init_db()

    with get_session() as session:
        quiz_count = session.execute(select(func.count()).select_from(Quiz)).scalar_one()
        if quiz_count:
            return

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

            quiz = Quiz(
                key=definition["key"],
                title=definition["title"],
                description=definition["description"],
                level=definition["level"],
            )
            session.add(quiz)
            session.flush()

            for entry in entries:
                if not entry["hanzi"] or not entry["pinyin"] or not entry["translation"]:
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
