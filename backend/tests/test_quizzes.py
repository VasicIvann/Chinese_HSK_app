"""Tests for the quiz catalog endpoints."""

from __future__ import annotations

from fastapi.testclient import TestClient


def _auth_token(client: TestClient, email: str = "dave@example.com") -> str:
    res = client.post("/v1/auth/register", json={"email": email, "password": "supersecret"})
    assert res.status_code == 201
    return res.json()["access_token"]


def test_list_quizzes_requires_auth(client: TestClient) -> None:
    res = client.get("/v1/quizzes")
    assert res.status_code in (401, 403)


def test_list_quizzes_returns_seeded_data(client: TestClient, seed_quizzes: None) -> None:
    token = _auth_token(client)
    res = client.get("/v1/quizzes", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    payload = res.json()
    assert len(payload) == 2
    keys = {item["key"] for item in payload}
    assert keys == {"HSK1", "HSK2"}


def test_get_entries_for_known_quiz(client: TestClient, seed_quizzes: None) -> None:
    token = _auth_token(client)
    res = client.get("/v1/quizzes/HSK1/entries", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    entries = res.json()
    assert len(entries) == 1
    assert entries[0]["hanzi"] == "爱"


def test_get_entries_unknown_quiz_returns_404(client: TestClient, seed_quizzes: None) -> None:
    token = _auth_token(client)
    res = client.get("/v1/quizzes/HSK99/entries", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 404


def test_healthz_does_not_require_auth_nor_the_database(client: TestClient, monkeypatch) -> None:
    """Pinged every 10 min by the keep-warm cron: must never wake Neon up."""
    import app.main as main

    class NoDatabase:
        def connect(self):
            raise AssertionError("/healthz must not touch the database")

    monkeypatch.setattr(main, "engine", NoDatabase())
    res = client.get("/healthz")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}


def test_healthz_db_checks_the_database(client: TestClient, monkeypatch) -> None:
    assert client.get("/healthz/db").json() == {"status": "ok", "db": "ok"}
    import app.main as main

    class BrokenEngine:
        def connect(self):
            raise RuntimeError("db down")

    monkeypatch.setattr(main, "engine", BrokenEngine())
    res = client.get("/healthz/db")
    assert res.status_code == 200
    assert res.json() == {"status": "ok", "db": "error"}
