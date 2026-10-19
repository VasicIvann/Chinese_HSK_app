"""HSK 2.0 / 3.0 switch: migration 0007 and the version-scoped API.

The core promise: a word is one entry whatever the version, so its progress
(mastered / learning / never seen) is the same in both; switching version only
changes which level it is listed under.
"""

from __future__ import annotations

from datetime import datetime

import pytest
import sqlalchemy as sa
from alembic import command
from fastapi.testclient import TestClient

from app.db.session import SessionLocal
from app.models import Entry, Quiz, QuizEntry
from tests.test_hsk3_migration import _alembic, legacy_db  # noqa: F401  (fixture)

# --------------------------------------------------------------------------- migration


def _levels_of(conn, entry_id: int) -> set[str]:
    return set(
        conn.execute(
            sa.text(
                "SELECT q.key FROM quiz_entries qe JOIN quizzes q ON q.id = qe.quiz_id WHERE qe.entry_id = :e"
            ),
            {"e": entry_id},
        ).scalars()
    )


def test_upgrade_lists_both_versions_on_shared_entries(legacy_db) -> None:  # noqa: F811
    command.upgrade(_alembic(legacy_db["url"]), "head")
    ids = legacy_db["ids"]
    with legacy_db["engine"].connect() as conn:
        counts = dict(
            conn.execute(
                sa.text(
                    "SELECT q.key, COUNT(*) FROM quiz_entries qe JOIN quizzes q ON q.id = qe.quiz_id "
                    "JOIN entries e ON e.id = qe.entry_id WHERE e.is_active = 1 GROUP BY q.key"
                )
            ).all()
        )
        assert counts == {
            "HSK1": 300, "HSK2": 200, "HSK3": 500, "HSK4": 1000, "HSK5": 1600,
            "HSK1-2.0": 150, "HSK2-2.0": 151, "HSK3-2.0": 297, "HSK4-2.0": 598, "HSK5-2.0": 1300,
        }
        versions = dict(conn.execute(sa.text("SELECT key, version FROM quizzes")).all())
        assert versions["HSK1"] == "3.0" and versions["HSK1-2.0"] == "2.0"

        # Same entry (same id, so same progress / examples / history) in both versions.
        assert _levels_of(conn, ids["爱"]) == {"HSK1", "HSK1-2.0"}
        assert "HSK3-2.0" in _levels_of(conn, ids["认真"])
        assert _levels_of(conn, ids["面条"]) & {"HSK2-2.0"}  # renamed 面条儿 by 0005, still the 2.0 word

        # A word that left the syllabus in 3.0 (北京) is back, for 2.0 only.
        assert _levels_of(conn, ids["北京"]) == {"HSK1-2.0"}
        assert conn.execute(sa.text("SELECT is_active FROM entries WHERE id = :i"), {"i": ids["北京"]}).scalar() == 1
        # Progress on hidden words is never deleted.
        gone = legacy_db["absent"][0]
        assert conn.execute(
            sa.text("SELECT COUNT(*) FROM user_vocab_mastery WHERE entry_id = :i"), {"i": ids[gone]}
        ).scalar() == 1

        # No word listed twice in the same version.
        dupes = conn.execute(
            sa.text(
                "SELECT COUNT(*) FROM (SELECT qe.entry_id, q.version, COUNT(*) c FROM quiz_entries qe "
                "JOIN quizzes q ON q.id = qe.quiz_id GROUP BY qe.entry_id, q.version HAVING c > 1)"
            )
        ).scalar()
        assert dupes == 0


def test_running_the_2_0_sync_again_changes_nothing(legacy_db) -> None:  # noqa: F811
    import importlib.util
    from pathlib import Path

    command.upgrade(_alembic(legacy_db["url"]), "head")
    path = Path(__file__).resolve().parents[1] / "alembic" / "versions" / "0007_hsk_versions.py"
    spec = importlib.util.spec_from_file_location("m0007", path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)

    engine = legacy_db["engine"]
    with engine.connect() as conn:
        before = conn.execute(sa.text("SELECT quiz_id, entry_id FROM quiz_entries ORDER BY 1, 2")).all()
    with engine.begin() as conn:
        assert m.link_v3(conn) == 0
        stats = m.sync_v2(conn, m.load_words())
    assert (stats["inserted"], stats["revived"], stats["links_added"], stats["links_removed"]) == (0, 0, 0, 0)
    with engine.connect() as conn:
        assert conn.execute(sa.text("SELECT quiz_id, entry_id FROM quiz_entries ORDER BY 1, 2")).all() == before


# --------------------------------------------------------------------------- API


def _register(client: TestClient, email: str) -> str:
    res = client.post("/v1/auth/register", json={"email": email, "password": "supersecret"})
    assert res.status_code == 201
    return res.json()["access_token"]


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def two_versions() -> dict[str, int]:
    """HSK1 (3.0) lists 爱 + 新; HSK1-2.0 lists 爱 + 旧. 爱 is one shared entry."""
    now = datetime.utcnow()
    with SessionLocal() as s:
        v3 = Quiz(key="HSK1", title="HSK 1", level=1, version="3.0", created_at=now, updated_at=now)
        v2 = Quiz(key="HSK1-2.0", title="HSK 1", level=1, version="2.0", created_at=now, updated_at=now)
        s.add_all([v3, v2])
        s.flush()
        shared = Entry(quiz_id=v3.id, hanzi="爱", pinyin="ài", translation="aimer", is_active=True, created_at=now)
        only3 = Entry(quiz_id=v3.id, hanzi="新", pinyin="xīn", translation="nouveau", is_active=True, created_at=now)
        only2 = Entry(quiz_id=v2.id, hanzi="旧", pinyin="jiù", translation="vieux", is_active=True, created_at=now)
        s.add_all([shared, only3, only2])
        s.flush()
        s.add_all(
            [
                QuizEntry(quiz_id=v3.id, entry_id=shared.id),
                QuizEntry(quiz_id=v3.id, entry_id=only3.id),
                QuizEntry(quiz_id=v2.id, entry_id=shared.id),
                QuizEntry(quiz_id=v2.id, entry_id=only2.id),
            ]
        )
        s.commit()
        return {"v3": v3.id, "v2": v2.id, "shared": shared.id, "only3": only3.id, "only2": only2.id}


def test_version_setting_defaults_to_3_and_persists(client: TestClient, two_versions) -> None:
    token = _register(client, "version-setting@example.com")
    assert client.get("/v1/account/settings", headers=_auth(token)).json() == {"hsk_version": "3.0"}
    assert [q["key"] for q in client.get("/v1/quizzes", headers=_auth(token)).json()] == ["HSK1"]

    res = client.put("/v1/account/settings", headers=_auth(token), json={"hsk_version": "2.0"})
    assert res.status_code == 200 and res.json() == {"hsk_version": "2.0"}
    assert client.get("/v1/account/settings", headers=_auth(token)).json() == {"hsk_version": "2.0"}
    quizzes = client.get("/v1/quizzes", headers=_auth(token)).json()
    assert [(q["key"], q["version"]) for q in quizzes] == [("HSK1-2.0", "2.0")]
    assert len(client.get("/v1/quizzes?version=all", headers=_auth(token)).json()) == 2

    assert client.put("/v1/account/settings", headers=_auth(token), json={"hsk_version": "4.0"}).status_code == 422


def test_progress_is_shared_across_versions(client: TestClient, two_versions) -> None:
    ids = two_versions
    token = _register(client, "version-progress@example.com")
    for _ in range(3):
        client.post("/v1/srs/rate", headers=_auth(token), json={"entry_id": ids["shared"], "rating": "easy"})

    def overview():
        return client.get("/v1/account/overview", headers=_auth(token)).json()

    v3 = overview()
    assert v3["hsk_version"] == "3.0"
    assert v3["mastery"]["total_entries"] == 2
    assert v3["mastery"]["new"] == 1  # 新 never seen; 爱 rated
    assert [(lv["quiz_key"], lv["total"], lv["new"]) for lv in v3["level_progress"]] == [("HSK1", 2, 1)]

    client.put("/v1/account/settings", headers=_auth(token), json={"hsk_version": "2.0"})
    v2 = overview()
    assert v2["hsk_version"] == "2.0"
    assert [(lv["quiz_key"], lv["total"], lv["new"]) for lv in v2["level_progress"]] == [("HSK1-2.0", 2, 1)]
    # Same status for the shared word in both versions.
    assert v2["mastery"]["mastered"] + v2["mastery"]["learning"] == 1
    assert (v2["mastery"]["mastered"], v2["mastery"]["learning"]) == (v3["mastery"]["mastered"], v3["mastery"]["learning"])
    assert v2["profile"]["total_reviews"] == v3["profile"]["total_reviews"] == 3

    # Only-new in 2.0 skips the word already learned in 3.0.
    fresh = client.get("/v1/srs/due?quiz=HSK1-2.0&only_new=true&count=10", headers=_auth(token)).json()
    assert [e["id"] for e in fresh] == [ids["only2"]]
    due = client.get("/v1/srs/due?quiz=HSK1-2.0&count=10", headers=_auth(token)).json()
    assert {e["id"] for e in due} == {ids["shared"], ids["only2"]}
    assert {e["quiz_id"] for e in due} == {ids["v2"]}

    stats = client.get("/v1/srs/stats", headers=_auth(token)).json()
    assert stats["new"] == 1 and stats["due"] + stats["upcoming"] == 1

    mastery = client.get("/v1/mastery", headers=_auth(token)).json()
    assert [(m["entry_id"], m["quiz_key"]) for m in mastery] == [(ids["shared"], "HSK1-2.0")]

    client.put("/v1/account/settings", headers=_auth(token), json={"hsk_version": "3.0"})
    assert overview()["mastery"] == v3["mastery"]


def test_settings_require_auth(client: TestClient) -> None:
    assert client.get("/v1/account/settings").status_code in (401, 403)
    assert client.put("/v1/account/settings", json={"hsk_version": "2.0"}).status_code in (401, 403)
