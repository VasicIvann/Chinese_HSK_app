"""Every quiz answer is recorded in review_log; internal re-queues are not."""

from __future__ import annotations

from datetime import datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.timezone import local_date, local_today, parse_timezone
from app.db.session import SessionLocal
from app.models import ReviewLog, UserVocabMastery


def _register(client: TestClient, email: str) -> str:
    res = client.post("/v1/auth/register", json={"email": email, "password": "supersecret"})
    assert res.status_code == 201
    return res.json()["access_token"]


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _logs() -> list[ReviewLog]:
    with SessionLocal() as s:
        return list(s.execute(select(ReviewLog).order_by(ReviewLog.id)).scalars().all())


def test_each_rating_adds_a_row(client: TestClient, seed_quizzes) -> None:
    token = _register(client, "log@example.com")
    entry_id = client.get("/v1/quizzes/HSK1/entries", headers=_auth(token)).json()[0]["id"]

    first = client.post(
        "/v1/srs/rate",
        headers=_auth(token),
        json={"entry_id": entry_id, "rating": "hard", "mode": "pinyin-input", "elapsed_ms": 4200},
    )
    second = client.post(
        "/v1/srs/rate", headers=_auth(token), json={"entry_id": entry_id, "rating": "good"}
    )
    assert first.status_code == second.status_code == 200

    logs = _logs()
    assert [(l.rating, l.was_new, l.mode, l.elapsed_ms) for l in logs] == [
        (2, True, "pinyin-input", 4200),
        (3, False, None, None),
    ]
    assert all(abs(l.reviewed_at - datetime.utcnow()) < timedelta(minutes=1) for l in logs)


def test_was_due_is_set_when_the_review_was_overdue(client: TestClient, seed_quizzes) -> None:
    token = _register(client, "due@example.com")
    entry_id = client.get("/v1/quizzes/HSK1/entries", headers=_auth(token)).json()[0]["id"]
    client.post("/v1/srs/rate", headers=_auth(token), json={"entry_id": entry_id, "rating": "good"})
    with SessionLocal() as s:
        row = s.execute(select(UserVocabMastery)).scalars().one()
        row.fsrs_due_at = datetime.utcnow() - timedelta(days=1)
        s.commit()
    client.post("/v1/srs/rate", headers=_auth(token), json={"entry_id": entry_id, "rating": "good"})
    assert [l.was_due for l in _logs()] == [False, True]


def test_elapsed_time_is_capped_and_bad_values_rejected(client: TestClient, seed_quizzes) -> None:
    token = _register(client, "elapsed@example.com")
    entry_id = client.get("/v1/quizzes/HSK1/entries", headers=_auth(token)).json()[0]["id"]
    res = client.post(
        "/v1/srs/rate",
        headers=_auth(token),
        json={"entry_id": entry_id, "rating": "easy", "elapsed_ms": 9_999_999},
    )
    assert res.status_code == 200
    assert _logs()[0].elapsed_ms == 600_000
    bad = client.post(
        "/v1/srs/rate",
        headers=_auth(token),
        json={"entry_id": entry_id, "rating": "easy", "mode": "cheat", "elapsed_ms": -1},
    )
    assert bad.status_code == 422


def test_expression_requeue_is_not_logged_as_a_review(client: TestClient, seed_quizzes) -> None:
    from app.services.srs_service import queue_entries_for_relearn

    token = _register(client, "requeue@example.com")
    entry_id = client.get("/v1/quizzes/HSK1/entries", headers=_auth(token)).json()[0]["id"]
    user_id = client.get("/v1/auth/me", headers=_auth(token)).json()["id"]
    with SessionLocal() as s:
        assert queue_entries_for_relearn(s, user_id, [entry_id]) == 1
        s.commit()
    assert _logs() == []


def test_timezone_helpers() -> None:
    assert str(parse_timezone("Asia/Shanghai")) == "Asia/Shanghai"
    assert str(parse_timezone("Not/AZone")) == "UTC"
    assert str(parse_timezone(None)) == "UTC"
    assert str(parse_timezone("x" * 100)) == "UTC"
    # 23:30 UTC on Oct 17 is already Oct 18 in Shanghai, still Oct 17 in Paris (UTC+2).
    ts = datetime(2026, 10, 17, 23, 30)
    assert local_date(ts, parse_timezone("Asia/Shanghai")).isoformat() == "2026-10-18"
    assert local_date(ts, parse_timezone("Europe/Paris")).isoformat() == "2026-10-18"
    assert local_date(ts, parse_timezone("America/New_York")).isoformat() == "2026-10-17"
    assert local_today(parse_timezone("UTC"), ts).isoformat() == "2026-10-17"
