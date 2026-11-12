"""Account page statistics: activity per tab, vocabulary growth, time and habits."""

from __future__ import annotations

from datetime import date, datetime

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.timezone import parse_timezone
from app.db.session import SessionLocal
from app.models import (
    Entry,
    ExerciseResult,
    ExpressionAttempt,
    ReviewLog,
    UserVocabMastery,
    WordDrawing,
)
from app.services.stats_service import study_stats

SHANGHAI = parse_timezone("Asia/Shanghai")
NOW = datetime(2026, 10, 18, 2, 0)  # 10:00 on Oct 18 in Shanghai


def _register(client: TestClient, email: str) -> tuple[str, int]:
    res = client.post("/v1/auth/register", json={"email": email, "password": "supersecret"})
    token = res.json()["access_token"]
    me = client.get("/v1/auth/me", headers={"Authorization": f"Bearer {token}"}).json()
    return token, me["id"]


def _mastery(user_id: int, entry_id: int, created_at: datetime) -> UserVocabMastery:
    return UserVocabMastery(
        user_id=user_id, entry_id=entry_id, status="learning", confidence_score=0.3, review_count=1,
        last_seen_at=created_at, created_at=created_at, updated_at=created_at,
    )


def test_stats_per_tab_words_and_time(client: TestClient, seed_quizzes) -> None:
    _, user_id = _register(client, "stats@example.com")
    with SessionLocal() as s:
        e1, e2 = s.execute(select(Entry.id).order_by(Entry.id)).scalars().all()
        s.add_all(
            [
                # 23:30 UTC Oct 17 = 07:30 Oct 18 Shanghai; 45 s on the card.
                ReviewLog(user_id=user_id, entry_id=e1, rating=3, reviewed_at=datetime(2026, 10, 17, 23, 30), elapsed_ms=45_000),
                # 10:00 UTC Oct 17 = 18:00 Oct 17 Shanghai; left open 10 min -> counted 2 min.
                ReviewLog(user_id=user_id, entry_id=e2, rating=1, reviewed_at=datetime(2026, 10, 17, 10, 0), elapsed_ms=600_000),
                # Out of the 7-day window.
                ReviewLog(user_id=user_id, entry_id=e1, rating=4, reviewed_at=datetime(2026, 9, 1, 10, 0)),
                ExerciseResult(user_id=user_id, version="3.0", level=3, section="listening", part_key="L1", score=7, total=10, details="[]", created_at=datetime(2026, 10, 17, 11, 0)),
                ExerciseResult(user_id=user_id, version="3.0", level=3, section="classifiers", part_key="fill", score=8, total=10, details="[]", created_at=datetime(2026, 10, 17, 23, 0)),
                ExerciseResult(user_id=user_id, version="3.0", level=3, section="grammar", part_key="3-01", score=2, total=3, details="[]", created_at=datetime(2026, 10, 16, 1, 0)),
                ExpressionAttempt(user_id=user_id, hsk_level=3, subject="s", user_text="t", correction_json="{}", score=80, created_at=datetime(2026, 10, 17, 12, 0)),
                WordDrawing(user_id=user_id, entry_id=e1, image_png=b"x", width=1, height=1, created_at=datetime(2026, 10, 17, 12, 30)),
                # First seen: e1 before the window, e2 on Oct 17 (Shanghai).
                _mastery(user_id, e1, datetime(2026, 9, 1, 10, 0)),
                _mastery(user_id, e2, datetime(2026, 10, 17, 10, 0)),
            ]
        )
        s.commit()
        stats = study_stats(s, user_id, version="3.0", days=7, tz=SHANGHAI, now_utc=NOW)

    assert stats["from_date"] == date(2026, 10, 12) and stats["to_date"] == date(2026, 10, 18)
    assert len(stats["activity"]) == 7
    day = {row["date"]: row for row in stats["activity"]}
    assert day[date(2026, 10, 18)]["vocab"] == 1 and day[date(2026, 10, 18)]["classifiers"] == 10
    oct17 = day[date(2026, 10, 17)]
    assert (oct17["vocab"], oct17["listening"], oct17["expression"], oct17["drawings"]) == (1, 10, 1, 1)
    assert day[date(2026, 10, 16)]["grammar"] == 3
    assert stats["totals"] == {
        "vocab": 2, "listening": 10, "writing": 0, "grammar": 3, "classifiers": 10, "tones": 0, "expression": 1, "drawings": 1,
    }
    assert stats["active_days"] == 3

    words = stats["words"]
    assert words["seen_before"] == 1 and words["seen_total"] == 2 and words["new_in_period"] == 1
    per_word_day = {row["date"]: row for row in words["per_day"]}
    assert per_word_day[date(2026, 10, 16)]["seen"] == 1
    assert per_word_day[date(2026, 10, 17)] == {"date": date(2026, 10, 17), "new": 1, "seen": 2}
    assert words["reviewed_in_period"] == 2
    assert words["level_totals"] == [{"level": 1, "total": 1}, {"level": 2, "total": 2}]

    t = {row["date"]: row for row in stats["time"]["per_day"]}
    assert t[date(2026, 10, 18)]["minutes"] == 0.8  # 45 s
    assert t[date(2026, 10, 17)]["minutes"] == 2.0  # capped
    assert stats["time"]["total_minutes"] == 2.8
    hours = {h["hour"]: h["count"] for h in stats["time"]["by_hour"]}
    # 07:30 card + 07:00 classifiers (10 questions) in Shanghai.
    assert hours[7] == 11 and hours[18] == 1 and hours[19] == 10
    weekdays = {w["weekday"]: w["count"] for w in stats["time"]["by_weekday"]}
    assert weekdays[6] == 11  # Sunday Oct 18


def test_stats_endpoint(client: TestClient, seed_quizzes) -> None:
    token, _ = _register(client, "stats-api@example.com")
    headers = {"Authorization": f"Bearer {token}", "X-Timezone": "Asia/Shanghai"}
    body = client.get("/v1/account/stats?days=30", headers=headers).json()
    assert body["days"] == 30 and len(body["activity"]) == 30 and body["active_days"] == 0
    assert len(body["time"]["by_hour"]) == 24 and len(body["time"]["by_weekday"]) == 7
    assert client.get("/v1/account/stats?days=12", headers=headers).status_code == 422
    assert client.get("/v1/account/stats").status_code in (401, 403)

    # A finished classifier quiz is now saved and counted.
    res = client.post(
        "/v1/exercises/results",
        headers=headers,
        json={"section": "classifiers", "level": 2, "part": "fill", "answers": [{"id": "本-01", "correct": True}]},
    )
    assert res.status_code == 201
    res = client.post(
        "/v1/exercises/results",
        headers=headers,
        json={"section": "tones", "level": 3, "part": "listen", "answers": [{"id": "12", "correct": False}, {"id": "13", "correct": True}]},
    )
    assert res.status_code == 201
    body = client.get("/v1/account/stats?days=7", headers=headers).json()
    assert body["totals"]["classifiers"] == 1 and body["totals"]["tones"] == 2 and body["active_days"] == 1
