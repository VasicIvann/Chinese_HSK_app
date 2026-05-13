"""Tests for the /v1/account/overview endpoint."""

from __future__ import annotations

from fastapi.testclient import TestClient


def _register(client: TestClient, email: str = "acc@example.com") -> str:
    res = client.post("/v1/auth/register", json={"email": email, "password": "supersecret"})
    assert res.status_code == 201
    return res.json()["access_token"]


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_overview_for_fresh_user_returns_baseline(
    client: TestClient, seed_quizzes: None
) -> None:
    token = _register(client)
    res = client.get("/v1/account/overview", headers=_auth(token))
    assert res.status_code == 200
    data = res.json()

    assert data["profile"]["email"] == "acc@example.com"
    assert data["profile"]["total_reviews"] == 0
    assert data["profile"]["total_expressions"] == 0

    assert data["mastery"]["mastered"] == 0
    assert data["mastery"]["learning"] == 0
    assert data["mastery"]["new"] == data["mastery"]["total_entries"]
    assert data["mastery"]["total_entries"] == 2  # seed has 2 entries

    # Heatmap has heatmap_days entries (default 90).
    assert len(data["activity_heatmap"]) == 90
    assert all(cell["count"] == 0 for cell in data["activity_heatmap"])

    assert data["quiz_progression"] == []
    assert data["expression_progression"] == []


def test_overview_reflects_ratings(client: TestClient, seed_quizzes: None) -> None:
    token = _register(client)
    entries = client.get("/v1/quizzes/HSK1/entries", headers=_auth(token)).json()
    entry_id = entries[0]["id"]

    client.post(
        "/v1/srs/rate", headers=_auth(token), json={"entry_id": entry_id, "rating": "good"}
    )

    data = client.get("/v1/account/overview", headers=_auth(token)).json()
    assert data["profile"]["total_reviews"] == 1
    assert data["mastery"]["learning"] == 1
    assert data["mastery"]["new"] == data["mastery"]["total_entries"] - 1

    # The activity heatmap's last cell (today) is 1.
    assert data["activity_heatmap"][-1]["count"] == 1
    # Quiz progression has 1 point for today.
    assert len(data["quiz_progression"]) == 1
    assert data["quiz_progression"][0]["avg_rating"] == 3.0  # "good" → 3


def test_overview_requires_auth(client: TestClient) -> None:
    assert client.get("/v1/account/overview").status_code in (401, 403)
