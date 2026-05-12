"""Tests for the /v1/mastery dashboard endpoint."""

from __future__ import annotations

from fastapi.testclient import TestClient


def _register(client: TestClient, email: str = "mastery@example.com") -> str:
    res = client.post("/v1/auth/register", json={"email": email, "password": "supersecret"})
    assert res.status_code == 201
    return res.json()["access_token"]


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_mastery_is_empty_initially(client: TestClient, seed_quizzes: None) -> None:
    token = _register(client)
    res = client.get("/v1/mastery", headers=_auth(token))
    assert res.status_code == 200
    assert res.json() == []


def test_mastery_returns_records_after_rating(client: TestClient, seed_quizzes: None) -> None:
    token = _register(client)
    hsk1_entry = client.get("/v1/quizzes/HSK1/entries", headers=_auth(token)).json()[0]
    hsk2_entry = client.get("/v1/quizzes/HSK2/entries", headers=_auth(token)).json()[0]

    client.post(
        "/v1/srs/rate", headers=_auth(token), json={"entry_id": hsk1_entry["id"], "rating": "good"}
    )
    client.post(
        "/v1/srs/rate", headers=_auth(token), json={"entry_id": hsk2_entry["id"], "rating": "again"}
    )

    res = client.get("/v1/mastery", headers=_auth(token))
    assert res.status_code == 200
    items = res.json()
    assert len(items) == 2

    hanzi_by_quiz = {item["quiz_key"]: item["hanzi"] for item in items}
    assert hanzi_by_quiz == {"HSK1": "爱", "HSK2": "北京"}

    for item in items:
        assert item["review_count"] == 1
        assert item["next_review_at"] is not None
        assert item["stability_days"] is not None


def test_mastery_filter_by_quiz(client: TestClient, seed_quizzes: None) -> None:
    token = _register(client)
    hsk1_entry = client.get("/v1/quizzes/HSK1/entries", headers=_auth(token)).json()[0]
    hsk2_entry = client.get("/v1/quizzes/HSK2/entries", headers=_auth(token)).json()[0]
    client.post(
        "/v1/srs/rate", headers=_auth(token), json={"entry_id": hsk1_entry["id"], "rating": "good"}
    )
    client.post(
        "/v1/srs/rate", headers=_auth(token), json={"entry_id": hsk2_entry["id"], "rating": "good"}
    )

    res = client.get("/v1/mastery?quiz=HSK1", headers=_auth(token))
    assert res.status_code == 200
    items = res.json()
    assert [item["quiz_key"] for item in items] == ["HSK1"]


def test_mastery_requires_auth(client: TestClient) -> None:
    assert client.get("/v1/mastery").status_code in (401, 403)
