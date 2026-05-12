"""Tests for the SRS endpoints (/v1/srs/*)."""

from __future__ import annotations

from fastapi.testclient import TestClient


def _register(client: TestClient, email: str = "ratings@example.com") -> str:
    res = client.post("/v1/auth/register", json={"email": email, "password": "supersecret"})
    assert res.status_code == 201
    return res.json()["access_token"]


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_rate_updates_mastery_and_returns_snapshot(client: TestClient, seed_quizzes: None) -> None:
    token = _register(client)
    entries = client.get("/v1/quizzes/HSK1/entries", headers=_auth(token)).json()
    entry_id = entries[0]["id"]

    res = client.post(
        "/v1/srs/rate",
        headers=_auth(token),
        json={"entry_id": entry_id, "rating": "good"},
    )
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["entry_id"] == entry_id
    assert data["rating"] == "good"
    assert data["rating_value"] == 3
    assert data["review_count"] == 1
    assert data["next_review_at"] is not None
    assert data["stability_days"] is not None


def test_rate_unknown_entry_returns_404(client: TestClient, seed_quizzes: None) -> None:
    token = _register(client)
    res = client.post(
        "/v1/srs/rate",
        headers=_auth(token),
        json={"entry_id": 99999, "rating": "good"},
    )
    assert res.status_code == 404


def test_rate_validates_rating_enum(client: TestClient, seed_quizzes: None) -> None:
    token = _register(client)
    entry_id = client.get("/v1/quizzes/HSK1/entries", headers=_auth(token)).json()[0]["id"]
    res = client.post(
        "/v1/srs/rate",
        headers=_auth(token),
        json={"entry_id": entry_id, "rating": "great"},
    )
    assert res.status_code == 422


def test_stats_counts_new_and_due_correctly(client: TestClient, seed_quizzes: None) -> None:
    token = _register(client)

    initial = client.get("/v1/srs/stats?quiz=HSK1", headers=_auth(token)).json()
    assert initial == {"due": 0, "new": 1, "upcoming": 0}

    entry_id = client.get("/v1/quizzes/HSK1/entries", headers=_auth(token)).json()[0]["id"]
    client.post(
        "/v1/srs/rate",
        headers=_auth(token),
        json={"entry_id": entry_id, "rating": "good"},
    )

    after = client.get("/v1/srs/stats?quiz=HSK1", headers=_auth(token)).json()
    # After a "good" rating the card is scheduled in the future → upcoming.
    assert after["due"] == 0
    assert after["new"] == 0
    assert after["upcoming"] == 1


def test_stats_aggregates_all_quizzes_when_unscoped(client: TestClient, seed_quizzes: None) -> None:
    token = _register(client)
    res = client.get("/v1/srs/stats", headers=_auth(token))
    assert res.status_code == 200
    data = res.json()
    assert data == {"due": 0, "new": 2, "upcoming": 0}  # one entry each in HSK1 + HSK2


def test_due_returns_entries(client: TestClient, seed_quizzes: None) -> None:
    token = _register(client)
    res = client.get("/v1/srs/due?quiz=HSK1&count=5", headers=_auth(token))
    assert res.status_code == 200
    payload = res.json()
    assert len(payload) == 1
    assert payload[0]["hanzi"] == "爱"


def test_due_unknown_quiz_returns_404(client: TestClient, seed_quizzes: None) -> None:
    token = _register(client)
    res = client.get("/v1/srs/due?quiz=HSK99&count=5", headers=_auth(token))
    assert res.status_code == 404


def test_srs_endpoints_require_auth(client: TestClient) -> None:
    assert client.get("/v1/srs/stats").status_code in (401, 403)
    assert client.get("/v1/srs/due?quiz=HSK1").status_code in (401, 403)
    assert client.post("/v1/srs/rate", json={}).status_code in (401, 403)
