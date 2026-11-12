"""Migration 0005: switch to the HSK 3.0 lists (levels 1-5) without losing progress.

(0007, which adds HSK 2.0 next to it, is covered in test_hsk_versions.py.)

Runs the real Alembic migrations on a throwaway SQLite file that starts in the
pre-0005 state (the old HSK 2.0 lists, a user with progress, an example and a
review), then checks what the upgrade did.
"""

from __future__ import annotations

import csv
import importlib.util
import os
from datetime import datetime
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config

BACKEND = Path(__file__).resolve().parents[1]
MIGRATION = BACKEND / "alembic" / "versions" / "0005_hsk3_vocabulary.py"


def _alembic(url: str) -> Config:
    cfg = Config(str(BACKEND / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND / "alembic"))
    return cfg


def _load_migration():
    spec = importlib.util.spec_from_file_location("m0005", MIGRATION)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def legacy_db(tmp_path, monkeypatch):
    """A database at revision 0004 holding the old HSK 2.0 lists and some progress."""
    from app.core import config

    url = f"sqlite:///{tmp_path / 'legacy.db'}"
    monkeypatch.setenv("HSK_DATABASE_URL", url)
    config.get_settings.cache_clear()
    command.upgrade(_alembic(url), "0004_review_log")

    engine = sa.create_engine(url)
    now = datetime.utcnow()
    ids: dict[str, int] = {}
    with engine.begin() as conn:
        for level in (1, 2, 3):
            quiz_id = conn.execute(
                sa.text(
                    "INSERT INTO quizzes (key, title, description, level, created_at, updated_at) "
                    "VALUES (:k, :t, 'HSK 2.0', :l, :n, :n)"
                ),
                {"k": f"HSK{level}", "t": f"HSK {level}", "l": level, "n": now},
            ).lastrowid
            path = BACKEND / "data" / "legacy-hsk2.0" / f"hsk{level}.csv"
            with open(path, encoding="utf-8-sig") as f:
                for row in csv.DictReader(f):
                    entry_id = conn.execute(
                        sa.text(
                            "INSERT INTO entries (quiz_id, hanzi, pinyin, translation, is_active, created_at) "
                            "VALUES (:q, :h, :p, :t, 1, :n)"
                        ),
                        {"q": quiz_id, "h": row["hanzi"], "p": row["pinyin"], "t": row["translation"], "n": now},
                    ).lastrowid
                    ids.setdefault(row["hanzi"], entry_id)
        user_id = conn.execute(
            sa.text(
                "INSERT INTO users (email, password_hash, locale, created_at, updated_at) "
                "VALUES ('legacy@example.com', 'x', 'fr', :n, :n)"
            ),
            {"n": now},
        ).lastrowid
        # Progress on: 爱 (HSK1 in both), 认真 (old HSK3), and one word absent from HSK 3.0 L1-5.
        hsk3_words = set()
        for level in range(1, 6):
            with open(BACKEND / "data" / "hsk3" / f"hsk{level}.csv", encoding="utf-8") as f:
                hsk3_words |= {row["hanzi"] for row in csv.DictReader(f)}
        absent = sorted(h for h in ids if h not in hsk3_words)
        assert absent, "the old lists contain words that left the syllabus"
        for hanzi in ["爱", "认真", *absent[:1]]:
            conn.execute(
                sa.text(
                    "INSERT INTO user_vocab_mastery (user_id, entry_id, status, confidence_score, "
                    "review_count, last_seen_at, created_at, updated_at) "
                    "VALUES (:u, :e, 'known', 0.95, 3, :n, :n, :n)"
                ),
                {"u": user_id, "e": ids[hanzi], "n": now},
            )
        conn.execute(
            sa.text(
                "INSERT INTO word_examples (user_id, entry_id, sentence, created_at) VALUES (:u, :e, '我爱你。', :n)"
            ),
            {"u": user_id, "e": ids["爱"], "n": now},
        )
        conn.execute(
            sa.text(
                "INSERT INTO review_log (user_id, entry_id, rating, was_new, was_due, reviewed_at) "
                "VALUES (:u, :e, 3, 1, 0, :n)"
            ),
            {"u": user_id, "e": ids["认真"], "n": now},
        )
    yield {"url": url, "engine": engine, "ids": ids, "absent": absent[:1]}
    engine.dispose()
    config.get_settings.cache_clear()


def _active_counts(conn) -> dict[str, int]:
    rows = conn.execute(
        sa.text(
            "SELECT q.key, COUNT(*) FROM entries e JOIN quizzes q ON q.id = e.quiz_id "
            "WHERE e.is_active = 1 GROUP BY q.key ORDER BY q.key"
        )
    ).all()
    return dict(rows)


def test_upgrade_switches_to_hsk3_and_keeps_progress(legacy_db) -> None:
    command.upgrade(_alembic(legacy_db["url"]), "0005_hsk3_vocabulary")
    engine, ids = legacy_db["engine"], legacy_db["ids"]

    with engine.connect() as conn:
        assert _active_counts(conn) == {"HSK1": 300, "HSK2": 200, "HSK3": 500, "HSK4": 1000, "HSK5": 1600}

        # Same entry ids: progress, examples and review history stay attached.
        def where(hanzi):
            return conn.execute(
                sa.text(
                    "SELECT q.key, e.is_active FROM entries e JOIN quizzes q ON q.id = e.quiz_id WHERE e.id = :i"
                ),
                {"i": ids[hanzi]},
            ).one()

        assert where("爱") == ("HSK1", 1)
        level_renzhen = where("认真")
        assert level_renzhen[1] == 1 and level_renzhen[0] in {"HSK1", "HSK2", "HSK3", "HSK4", "HSK5"}
        for hanzi in legacy_db["absent"]:
            assert where(hanzi)[1] == 0  # kept but hidden

        assert conn.execute(sa.text("SELECT COUNT(*) FROM user_vocab_mastery")).scalar() == 1 + 1 + len(legacy_db["absent"])
        assert conn.execute(sa.text("SELECT entry_id FROM word_examples")).scalar() == ids["爱"]
        assert conn.execute(sa.text("SELECT entry_id FROM review_log")).scalar() == ids["认真"]

        # No duplicate active (hanzi, pinyin, level).
        dupes = conn.execute(
            sa.text(
                "SELECT COUNT(*) FROM (SELECT hanzi, pinyin, quiz_id, COUNT(*) c FROM entries "
                "WHERE is_active = 1 GROUP BY hanzi, pinyin, quiz_id HAVING c > 1 "
                "AND hanzi NOT IN ('花', '生', '称', '批'))"
            )
        ).scalar()
        assert dupes == 0

        new_words = conn.execute(
            sa.text("SELECT translation FROM entries e JOIN quizzes q ON q.id = e.quiz_id WHERE q.key='HSK5' AND hanzi='经营'")
        ).scalar()
        assert new_words  # a French translation is present


def test_variant_forms_keep_their_progress(legacy_db) -> None:
    """面条 (old) is 面条儿 in the new syllabus: same entry, moved and renamed."""
    command.upgrade(_alembic(legacy_db["url"]), "0005_hsk3_vocabulary")
    with legacy_db["engine"].connect() as conn:
        row = conn.execute(
            sa.text("SELECT hanzi, is_active FROM entries WHERE id = :i"), {"i": legacy_db["ids"]["面条"]}
        ).one()
    assert row == ("面条儿", 1)


def test_running_the_sync_again_changes_nothing(legacy_db) -> None:
    command.upgrade(_alembic(legacy_db["url"]), "0005_hsk3_vocabulary")
    engine = legacy_db["engine"]
    with engine.connect() as conn:
        before = conn.execute(sa.text("SELECT id, quiz_id, is_active FROM entries ORDER BY id")).all()

    m = _load_migration()
    with engine.begin() as conn:
        stats = m.sync_vocabulary(conn, m.load_words())
    assert stats["inserted"] == 0
    with engine.connect() as conn:
        after = conn.execute(sa.text("SELECT id, quiz_id, is_active FROM entries ORDER BY id")).all()
    assert after == before


def test_fresh_database_gets_the_full_lists(tmp_path, monkeypatch) -> None:
    from app.core import config

    url = f"sqlite:///{tmp_path / 'fresh.db'}"
    monkeypatch.setenv("HSK_DATABASE_URL", url)
    config.get_settings.cache_clear()
    try:
        command.upgrade(_alembic(url), "head")
        engine = sa.create_engine(url)
        with engine.connect() as conn:
            listed = dict(
                conn.execute(
                    sa.text(
                        "SELECT q.key, COUNT(*) FROM quiz_entries qe JOIN quizzes q ON q.id = qe.quiz_id "
                        "GROUP BY q.key"
                    )
                ).all()
            )
            assert listed == {
                "HSK1": 300, "HSK2": 200, "HSK3": 500, "HSK4": 1000, "HSK5": 1600,
                "HSK1-2.0": 150, "HSK2-2.0": 151, "HSK3-2.0": 297, "HSK4-2.0": 598, "HSK5-2.0": 1300,
            }
            assert conn.execute(sa.text("SELECT COUNT(*) FROM entries WHERE translation = ''")).scalar() == 0
        engine.dispose()
    finally:
        config.get_settings.cache_clear()
        os.environ.pop("HSK_DATABASE_URL", None)
