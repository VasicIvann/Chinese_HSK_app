"""Session options on /v1/srs/due and /v1/srs/stats: several HSK levels, large
sessions (MAX), and the "only new words" mode."""

from __future__ import annotations

from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from app.db.session import SessionLocal
from app.models import Entry, Quiz


def _register(client: TestClient, email: str) -> str:
    res = client.post("/v1/auth/register", json={"email": email, "password": "supersecret"})
    assert res.status_code == 201
    return res.json()["access_token"]


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def three_levels() -> dict[str, int]:
    """HSK1 (3 words), HSK2 (4 words), HSK3 (120 words). Returns word counts."""
    now = datetime.utcnow()
    sizes = {"HSK1": 3, "HSK2": 4, "HSK3": 120}
    with SessionLocal() as session:
        for level, (key, size) in enumerate(sizes.items(), start=1):
            quiz = Quiz(key=key, title=f"HSK {level}", level=level, created_at=now, updated_at=now)
            session.add(quiz)
            session.flush()
            session.add_all(
                Entry(
                    quiz_id=quiz.id,
                    hanzi=f"字{level}-{i}",
                    pinyin="zì",
                    translation=f"mot {level}-{i}",
                    is_active=True,
                    created_at=now,
                )
                for i in range(size)
            )
        session.commit()
    return sizes


def _quiz_ids(client: TestClient, token: str) -> dict[str, int]:
    return {q["key"]: q["id"] for q in client.get("/v1/quizzes", headers=_auth(token)).json()}


def test_due_mixes_words_from_several_levels(client: TestClient, three_levels) -> None:
    token = _register(client, "multi@example.com")
    ids = _quiz_ids(client, token)

    res = client.get("/v1/srs/due?quiz=HSK1&quiz=HSK2&count=7", headers=_auth(token))
    assert res.status_code == 200, res.text
    quiz_ids = {e["quiz_id"] for e in res.json()}
    assert len(res.json()) == 7
    assert quiz_ids == {ids["HSK1"], ids["HSK2"]}


def test_due_accepts_comma_separated_keys(client: TestClient, three_levels) -> None:
    token = _register(client, "comma@example.com")
    ids = _quiz_ids(client, token)
    res = client.get("/v1/srs/due?quiz=HSK1,HSK2&count=50", headers=_auth(token))
    assert res.status_code == 200
    assert {e["quiz_id"] for e in res.json()} == {ids["HSK1"], ids["HSK2"]}
    assert len(res.json()) == 7  # capped at the words available


def test_single_quiz_still_works(client: TestClient, three_levels) -> None:
    token = _register(client, "single@example.com")
    ids = _quiz_ids(client, token)
    res = client.get("/v1/srs/due?quiz=HSK2&count=10", headers=_auth(token))
    assert res.status_code == 200
    assert {e["quiz_id"] for e in res.json()} == {ids["HSK2"]}


def test_due_allows_sessions_above_100_words(client: TestClient, three_levels) -> None:
    token = _register(client, "max@example.com")
    total = sum(three_levels.values())
    res = client.get(f"/v1/srs/due?quiz=HSK1,HSK2,HSK3&count={total}", headers=_auth(token))
    assert res.status_code == 200, res.text
    words = res.json()
    assert len(words) == total
    assert len({w["id"] for w in words}) == total  # no duplicates


def test_due_rejects_count_above_limit(client: TestClient, three_levels) -> None:
    token = _register(client, "toomany@example.com")
    res = client.get("/v1/srs/due?quiz=HSK1&count=2001", headers=_auth(token))
    assert res.status_code == 422


def test_due_unknown_quiz_returns_404(client: TestClient, three_levels) -> None:
    token = _register(client, "unknown@example.com")
    res = client.get("/v1/srs/due?quiz=HSK1&quiz=HSK9", headers=_auth(token))
    assert res.status_code == 404
    assert "HSK9" in res.json()["detail"]


def test_only_new_excludes_words_already_rated(client: TestClient, three_levels) -> None:
    token = _register(client, "onlynew@example.com")
    first = client.get("/v1/srs/due?quiz=HSK1,HSK2&count=7", headers=_auth(token)).json()
    rated = {e["id"] for e in first[:5]}
    for entry_id in rated:
        res = client.post(
            "/v1/srs/rate", headers=_auth(token), json={"entry_id": entry_id, "rating": "good"}
        )
        assert res.status_code == 200

    res = client.get("/v1/srs/due?quiz=HSK1,HSK2&count=50&only_new=true", headers=_auth(token))
    assert res.status_code == 200
    fresh = {e["id"] for e in res.json()}
    assert len(fresh) == 2
    assert fresh.isdisjoint(rated)

    # Default mode still serves the rated words when they are due / upcoming.
    default = client.get("/v1/srs/due?quiz=HSK1,HSK2&count=50", headers=_auth(token)).json()
    assert len(default) == 7


def test_only_new_returns_empty_list_when_everything_was_seen(
    client: TestClient, three_levels
) -> None:
    token = _register(client, "allseen@example.com")
    for entry in client.get("/v1/srs/due?quiz=HSK1&count=10", headers=_auth(token)).json():
        client.post("/v1/srs/rate", headers=_auth(token), json={"entry_id": entry["id"], "rating": "easy"})
    res = client.get("/v1/srs/due?quiz=HSK1&only_new=true", headers=_auth(token))
    assert res.status_code == 200
    assert res.json() == []


def test_stats_over_several_levels(client: TestClient, three_levels) -> None:
    token = _register(client, "stats@example.com")
    entry_id = client.get("/v1/srs/due?quiz=HSK2&count=1", headers=_auth(token)).json()[0]["id"]
    client.post("/v1/srs/rate", headers=_auth(token), json={"entry_id": entry_id, "rating": "good"})

    res = client.get("/v1/srs/stats?quiz=HSK1&quiz=HSK2", headers=_auth(token))
    assert res.status_code == 200
    stats = res.json()
    assert stats["due"] + stats["new"] + stats["upcoming"] == 7
    assert stats["new"] == 6

    everything = client.get("/v1/srs/stats", headers=_auth(token)).json()
    assert sum(everything.values()) == sum(three_levels.values())
