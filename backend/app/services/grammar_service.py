"""Official grammar points (语法等级大纲, HSK levels 1-3) with French explanations.

`data/grammar/points.json` is built by `scripts/build_grammar.py` from the official
list (`data/grammar/official.csv`) and the explanations in `data/grammar/src`.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ExerciseResult

PATH = Path(__file__).resolve().parents[2] / "data" / "grammar" / "points.json"


@lru_cache(maxsize=1)
def all_points() -> list[dict[str, Any]]:
    if not PATH.exists():
        return []
    with open(PATH, encoding="utf-8") as f:
        return json.load(f)["points"]


def points_with_progress(db: Session, user_id: int, level: int) -> list[dict[str, Any]]:
    rows = db.execute(
        select(ExerciseResult.part_key, ExerciseResult.score, ExerciseResult.total)
        .where(
            ExerciseResult.user_id == user_id,
            ExerciseResult.section == "grammar",
            ExerciseResult.level == level,
        )
        .order_by(ExerciseResult.created_at)
    ).all()
    last: dict[str, dict[str, int]] = {}
    for part_key, score, total in rows:
        last[part_key] = {"score": score, "total": total}
    return [{**p, "last": last.get(p["id"])} for p in all_points() if p["level"] == level]
