"""End-to-end tests for the auth flow."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_register_login_and_me_flow(client: TestClient) -> None:
    payload = {"email": "alice@example.com", "password": "supersecret"}

    register = client.post("/v1/auth/register", json=payload)
    assert register.status_code == 201, register.text
    data = register.json()
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "alice@example.com"
    token = data["access_token"]
    assert token

    # /me with the fresh token returns the same user
    me = client.get("/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == "alice@example.com"

    # Login on the same email returns a new token + same user
    login = client.post("/v1/auth/login", json=payload)
    assert login.status_code == 200
    assert login.json()["user"]["id"] == data["user"]["id"]


def test_register_duplicate_email_conflicts(client: TestClient) -> None:
    payload = {"email": "bob@example.com", "password": "supersecret"}

    first = client.post("/v1/auth/register", json=payload)
    assert first.status_code == 201

    second = client.post("/v1/auth/register", json=payload)
    assert second.status_code == 409


def test_login_with_wrong_password_returns_401(client: TestClient) -> None:
    client.post(
        "/v1/auth/register",
        json={"email": "carol@example.com", "password": "rightpassword"},
    )
    res = client.post(
        "/v1/auth/login",
        json={"email": "carol@example.com", "password": "wrongpassword"},
    )
    assert res.status_code == 401


def test_me_without_token_is_unauthorized(client: TestClient) -> None:
    res = client.get("/v1/auth/me")
    # FastAPI's HTTPBearer with auto_error=True returns 401 (newer) or 403 (older).
    assert res.status_code in (401, 403)


def test_me_with_invalid_token_returns_401(client: TestClient) -> None:
    res = client.get("/v1/auth/me", headers={"Authorization": "Bearer not-a-real-token"})
    assert res.status_code == 401


def test_register_respects_invite_only(monkeypatch, client: TestClient) -> None:
    from app.core.config import get_settings

    monkeypatch.setenv("ALLOWED_REGISTRATION_EMAILS", "vip@example.com")
    get_settings.cache_clear()

    blocked = client.post(
        "/v1/auth/register",
        json={"email": "stranger@example.com", "password": "supersecret"},
    )
    assert blocked.status_code == 403

    allowed = client.post(
        "/v1/auth/register",
        json={"email": "vip@example.com", "password": "supersecret"},
    )
    assert allowed.status_code == 201

    # Restore default state for other tests.
    monkeypatch.delenv("ALLOWED_REGISTRATION_EMAILS", raising=False)
    get_settings.cache_clear()
