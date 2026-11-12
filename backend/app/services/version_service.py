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
PINYIN_LOCK_KEY = "pinyin_locked"


def get_user_version(db: Session, user_id: int) -> str:
    value = db.execute(
        select(UserSetting.value).where(UserSetting.user_id == user_id, UserSetting.key == SETTING_KEY)
    ).scalar()
    return value if value in HSK_VERSIONS else DEFAULT_VERSION


def set_user_version(db: Session, user_id: int, version: str) -> str:
    if version not in HSK_VERSIONS:
        raise ValueError(f"Version HSK inconnue : {version}")
    _put_setting(db, user_id, SETTING_KEY, version)
    return version


def get_pinyin_locked(db: Session, user_id: int) -> bool:
    """Whether the vocabulary quiz shows the pinyin from the start of every card."""
    value = db.execute(
        select(UserSetting.value).where(UserSetting.user_id == user_id, UserSetting.key == PINYIN_LOCK_KEY)
    ).scalar()
    return value == "1"


def set_pinyin_locked(db: Session, user_id: int, locked: bool) -> bool:
    _put_setting(db, user_id, PINYIN_LOCK_KEY, "1" if locked else "0")
    return locked


def _put_setting(db: Session, user_id: int, key: str, value: str) -> None:
    row = db.execute(
        select(UserSetting).where(UserSetting.user_id == user_id, UserSetting.key == key)
    ).scalar_one_or_none()
    now = datetime.utcnow()
    if row is None:
        db.add(UserSetting(user_id=user_id, key=key, value=value, created_at=now, updated_at=now))
    else:
        row.value = value
        row.updated_at = now
    db.flush()


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
