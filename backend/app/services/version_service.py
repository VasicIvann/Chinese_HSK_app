"""HSK version (2.0 / 3.0) chosen by each user, and the queries scoped to it.

Switching version never touches the user's progress: words are shared entries,
only the quizzes (levels) they are listed under change.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.sql import Select

from app.models import Entry, Quiz, QuizEntry, UserSetting

HSK_VERSIONS = ("2.0", "3.0")
DEFAULT_VERSION = "3.0"
SETTING_KEY = "hsk_version"


def get_user_version(db: Session, user_id: int) -> str:
    value = db.execute(
        select(UserSetting.value).where(UserSetting.user_id == user_id, UserSetting.key == SETTING_KEY)
    ).scalar()
    return value if value in HSK_VERSIONS else DEFAULT_VERSION


def set_user_version(db: Session, user_id: int, version: str) -> str:
    if version not in HSK_VERSIONS:
        raise ValueError(f"Version HSK inconnue : {version}")
    row = db.execute(
        select(UserSetting).where(UserSetting.user_id == user_id, UserSetting.key == SETTING_KEY)
    ).scalar_one_or_none()
    now = datetime.utcnow()
    if row is None:
        db.add(UserSetting(user_id=user_id, key=SETTING_KEY, value=version, created_at=now, updated_at=now))
    else:
        row.value = version
        row.updated_at = now
    db.flush()
    return version


def version_entries(version: str) -> Select:
    """(entry_id, quiz) rows for every active word of a version."""
    return (
        select(QuizEntry.entry_id, Quiz.id.label("quiz_id"), Quiz.key, Quiz.title, Quiz.level)
        .join(Quiz, Quiz.id == QuizEntry.quiz_id)
        .join(Entry, Entry.id == QuizEntry.entry_id)
        .where(Quiz.version == version, Entry.is_active.is_(True))
    )


def version_entry_ids(version: str) -> Select:
    return version_entries(version).with_only_columns(QuizEntry.entry_id)


def entry_level(db: Session, entry_id: int, version: str) -> int | None:
    """The word's HSK level in `version`, else in the other version, else None."""
    rows = db.execute(
        select(Quiz.version, Quiz.level)
        .join(QuizEntry, QuizEntry.quiz_id == Quiz.id)
        .where(QuizEntry.entry_id == entry_id)
    ).all()
    levels = {v: lvl for v, lvl in rows}
    if version in levels:
        return levels[version]
    return next(iter(levels.values()), None)
