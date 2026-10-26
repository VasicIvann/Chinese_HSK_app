"""Read-only Admin page: access reserved to ADMIN_EMAILS, counters only."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.session import SessionLocal
from app.models import (
    Entry,
    ExerciseResult,
    ExpressionAttempt,
    ReviewLog,
    UserDailyUsage,
    UserVocabMastery,
)


def _register(client: TestClient, email: str) -> tuple[str, dict]:
    res = client.post("/v1/auth/register", json={"email": email, "password": "supersecret"})
    assert res.status_code == 201
    return res.json()["access_token"], res.json()["user"]


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def admin_env(monkeypatch):
    from app.core import config

    monkeypatch.setenv("ADMIN_EMAILS", " I@i.com ")
    config.get_settings.cache_clear()
    yield
    config.get_settings.cache_clear()


def test_only_the_listed_email_is_admin(client: TestClient, admin_env) -> None:
    admin_token, admin_user = _register(client, "i@i.com")
    user_token, user = _register(client, "someone@example.com")
    assert admin_user["is_admin"] is True and user["is_admin"] is False
    assert client.get("/v1/auth/me", headers=_auth(admin_token)).json()["is_admin"] is True
    login = client.post("/v1/auth/login", json={"email": "i@i.com", "password": "supersecret"}).json()
    assert login["user"]["is_admin"] is True

    for path in ("/v1/admin/users", f"/v1/admin/users/{user['id']}/stats"):
        assert client.get(path, headers=_auth(user_token)).status_code == 403
        assert client.get(path).status_code in (401, 403)
        assert client.get(path, headers=_auth(admin_token)).status_code == 200


def test_nobody_is_admin_without_the_variable(client: TestClient, monkeypatch) -> None:
    from app.core import config

    monkeypatch.delenv("ADMIN_EMAILS", raising=False)
    config.get_settings.cache_clear()
    token, user = _register(client, "i@i.com")
    assert user["is_admin"] is False
    assert client.get("/v1/admin/users", headers=_auth(token)).status_code == 403
    config.get_settings.cache_clear()


def test_overview_counts_activity_but_returns_no_content(client: TestClient, admin_env, seed_quizzes) -> None:
    admin_token, _ = _register(client, "i@i.com")
    _, user = _register(client, "learner@example.com")
    now = datetime.utcnow()
    with SessionLocal() as s:
        entry_ids = s.execute(select(Entry.id)).scalars().all()
        s.add_all(
            [
                ReviewLog(user_id=user["id"], entry_id=entry_ids[0], rating=3, reviewed_at=now - timedelta(hours=1)),
                ReviewLog(user_id=user["id"], entry_id=entry_ids[1], rating=1, reviewed_at=now - timedelta(days=10)),
                UserVocabMastery(user_id=user["id"], entry_id=entry_ids[0], status="known", confidence_score=0.95,
                                 review_count=4, last_seen_at=now, created_at=now, updated_at=now),
                UserVocabMastery(user_id=user["id"], entry_id=entry_ids[1], status="learning", confidence_score=0.2,
                                 review_count=1, last_seen_at=now, created_at=now, updated_at=now),
                ExerciseResult(user_id=user["id"], version="3.0", level=3, section="tones", part_key="read",
                               score=7, total=10, details="[]", created_at=now),
                ExpressionAttempt(user_id=user["id"], hsk_level=3, subject="sujet secret", user_text="texte privé",
                                  correction_json="{}", score=80, created_at=now - timedelta(days=3)),
                UserDailyUsage(user_id=user["id"], usage_date=now.date(), kind="expression_correction", count=2,
                               tokens_input=1000, tokens_output=500),
            ]
        )
        s.commit()

    res = client.get("/v1/admin/users", headers=_auth(admin_token))
    body = res.json()
    assert body["summary"]["users"] == 2 and body["summary"]["signups_7d"] == 2
    assert body["summary"]["active_today"] == 1 and body["summary"]["active_7d"] == 1
    assert body["summary"]["claude_tokens"] == 1500
    assert len(body["signups_per_week"]) == 12 and body["signups_per_week"][-1]["count"] == 2
    row = next(r for r in body["users"] if r["email"] == "learner@example.com")
    assert (row["words_seen"], row["words_mastered"], row["reviews"], row["reviews_7d"]) == (2, 1, 2, 1)
    assert row["questions"]["tones"] == 10 and row["expressions"] == 1
    assert (row["claude_calls"], row["claude_tokens"]) == (2, 1500)
    assert row["active_days_30"] == 3 and row["active_today"] is True
    # Counters only: no password hash, no text written by the user.
    assert "password" not in res.text and "texte privé" not in res.text and "sujet secret" not in res.text

    detail = client.get(f"/v1/admin/users/{user['id']}/stats?days=7", headers=_auth(admin_token)).json()
    assert detail["user"]["email"] == "learner@example.com"
    assert detail["stats"]["totals"]["vocab"] == 1 and detail["stats"]["totals"]["tones"] == 10
    assert client.get("/v1/admin/users/9999/stats", headers=_auth(admin_token)).status_code == 404
    assert client.get(f"/v1/admin/users/{user['id']}/stats?days=5", headers=_auth(admin_token)).status_code == 422


def test_admin_endpoints_are_read_only(client: TestClient, admin_env) -> None:
    token, user = _register(client, "i@i.com")
    for method in ("post", "put", "patch", "delete"):
        assert getattr(client, method)("/v1/admin/users", headers=_auth(token)).status_code == 405
