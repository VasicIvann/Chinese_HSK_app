"""Curated Expression écrite subject pool loaded from a JSON file."""

from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Optional, TypedDict


class CuratedSubject(TypedDict):
    subject: str
    keywords: list[str]


_DEFAULT_FILENAME = "expression_subjects.json"


def _candidate_paths() -> list[Path]:
    """Resolution order for the subjects JSON.

    Honour the env var first, then look in `backend/data/` (the deployed layout),
    then fall back to the repo-root `data/` (used during local development when
    Streamlit still owns the source-of-truth file).
    """
    paths: list[Path] = []
    env_path = os.environ.get("HSK_SUBJECTS_FILE", "").strip()
    if env_path:
        paths.append(Path(env_path))

    backend_dir = Path(__file__).resolve().parent.parent.parent
    paths.append(backend_dir / "data" / _DEFAULT_FILENAME)
    paths.append(backend_dir.parent / "data" / _DEFAULT_FILENAME)
    return paths


def _resolve_path() -> Path:
    for candidate in _candidate_paths():
        if candidate.exists():
            return candidate
    raise FileNotFoundError(
        f"Could not find {_DEFAULT_FILENAME}. Tried: {[str(p) for p in _candidate_paths()]}"
    )


@lru_cache(maxsize=1)
def _load_pool() -> dict[int, list[CuratedSubject]]:
    path = _resolve_path()
    raw = json.loads(path.read_text(encoding="utf-8"))
    pool: dict[int, list[CuratedSubject]] = {}
    for level_str, subjects in raw.items():
        try:
            level = int(level_str)
        except (TypeError, ValueError):
            continue
        cleaned: list[CuratedSubject] = []
        for entry in subjects:
            if not isinstance(entry, dict):
                continue
            subject = str(entry.get("subject", "")).strip()
            if not subject:
                continue
            keywords = [str(k).strip() for k in entry.get("keywords", []) if str(k).strip()]
            cleaned.append({"subject": subject, "keywords": keywords})
        if cleaned:
            pool[level] = cleaned
    return pool


def list_subjects(level: Optional[int] = None) -> list[CuratedSubject]:
    pool = _load_pool()
    if level is None:
        return [item for group in pool.values() for item in group]
    return list(pool.get(level, []))


def get_levels() -> list[int]:
    return sorted(_load_pool().keys())


__all__ = ["CuratedSubject", "get_levels", "list_subjects"]
