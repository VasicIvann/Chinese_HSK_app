"""Dashboard stats: level progress, streak, success rate, upcoming reviews,
all bucketed in the user's time zone."""

from __future__ import annotations

from datetime import date, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.timezone import parse_timezone
from app.db.session import SessionLocal
from app.models import Entry, ReviewLog, User, UserVocabMastery
from app.services.account_service import compute_streak, get_overview

SHANGHAI = parse_timezone("Asia/Shanghai")


def _register(client: TestClient, email: str) -> str:
    res = client.post("/v1/auth/register", json={"email": email, "password": "supersecret"})
    assert res.status_code == 201
    return res.json()["access_token"]


def _auth(token: str, tz: str | None = None) -> dict[str, str]:
    headers = {"Authorization": f"Bearer {token}"}
    if tz:
        headers["X-Timezone"] = tz
    return headers


# --- streak -----------------------------------------------------------------

def test_streak_counts_consecutive_days() -> None:
    today = date(2026, 10, 18)
    days = {today - timedelta(days=i) for i in range(4)} | {date(2026, 10, 1), date(2026, 10, 2)}
    assert compute_streak(days, today) == {"current": 4, "best": 4, "studied_today": True}


def test_streak_stays_alive_until_the_end_of_today() -> None:
    today = date(2026, 10, 18)
    days = {date(2026, 10, 17), date(2026, 10, 16)}
    assert compute_streak(days, today) == {"current": 2, "best": 2, "studied_today": False}


def test_streak_is_broken_after_a_missed_day_but_best_is_kept() -> None:
    today = date(2026, 10, 18)
    days = {date(2026, 10, 10), date(2026, 10, 11), date(2026, 10, 12), date(2026, 10, 16)}
    assert compute_streak(days, today) == {"current": 0, "best": 3, "studied_today": False}
    assert compute_streak(set(), today) == {"current": 0, "best": 0, "studied_today": False}


# --- service-level, with a fixed clock ---------------------------------------

def _setup_user_with_history(client: TestClient, email: str) -> tuple[int, list[int]]:
    token = _register(client, email)
    user_id = client.get("/v1/auth/me", headers=_auth(token)).json()["id"]
    hsk1 = [e["id"] for e in client.get("/v1/quizzes/HSK1/entries", headers=_auth(token)).json()]
    hsk2 = [e["id"] for e in client.get("/v1/quizzes/HSK2/entries", headers=_auth(token)).json()]
    return user_id, hsk1 + hsk2


def test_overview_buckets_days_in_the_user_time_zone(client: TestClient, seed_quizzes) -> None:
    user_id, (e1, e2) = _setup_user_with_history(client, "tz@example.com")
    # "Now" = 2026-10-18 02:00 UTC = 10:00 in Shanghai on Oct 18.
    now = datetime(2026, 10, 18, 2, 0)
    with SessionLocal() as s:
        s.add_all(
            [
                # 23:30 UTC Oct 17 = 07:30 Oct 18 in Shanghai -> today in Shanghai.
                ReviewLog(user_id=user_id, entry_id=e1, rating=3, reviewed_at=datetime(2026, 10, 17, 23, 30)),
                # 10:00 UTC Oct 17 = 18:00 Oct 17 Shanghai -> yesterday.
                ReviewLog(user_id=user_id, entry_id=e2, rating=1, reviewed_at=datetime(2026, 10, 17, 10, 0)),
                # 10:00 UTC Oct 16 -> Oct 16 Shanghai.
                ReviewLog(user_id=user_id, entry_id=e1, rating=4, reviewed_at=datetime(2026, 10, 16, 10, 0)),
            ]
        )
        s.commit()
        user = s.get(User, user_id)
        shanghai = get_overview(s, user, tz=SHANGHAI, now_utc=now)
        utc = get_overview(s, user, tz=parse_timezone("UTC"), now_utc=now)

    assert shanghai["streak"] == {"current": 3, "best": 3, "studied_today": True}
    heat = {c["date"]: c["count"] for c in shanghai["activity_heatmap"]}
    assert heat[date(2026, 10, 18)] == 1 and heat[date(2026, 10, 17)] == 1 and heat[date(2026, 10, 16)] == 1

    # In UTC, the 23:30 review lands on Oct 17 and nothing happened "today" (Oct 18).
    assert utc["streak"] == {"current": 2, "best": 2, "studied_today": False}

    rate = shanghai["success_rate"]
    assert rate["reviews_7_days"] == 3
    assert rate["last_7_days"] == round(2 / 3, 4)
    assert rate["tracking_since"] == date(2026, 10, 16)
    assert [(d["date"], d["rate"]) for d in rate["daily"]] == [
        (date(2026, 10, 16), 1.0),
        (date(2026, 10, 17), 0.0),
        (date(2026, 10, 18), 1.0),
    ]


def test_level_progress_and_upcoming_reviews(client: TestClient, seed_quizzes) -> None:
    token = _register(client, "levels@example.com")
    user_id = client.get("/v1/auth/me", headers=_auth(token)).json()["id"]
    e1 = client.get("/v1/quizzes/HSK1/entries", headers=_auth(token)).json()[0]["id"]
    e2 = client.get("/v1/quizzes/HSK2/entries", headers=_auth(token)).json()[0]["id"]
    client.post("/v1/srs/rate", headers=_auth(token), json={"entry_id": e1, "rating": "easy"})
    client.post("/v1/srs/rate", headers=_auth(token), json={"entry_id": e2, "rating": "again"})

    now = datetime(2026, 10, 18, 2, 0)  # 10:00 Shanghai
    with SessionLocal() as s:
        rows = {r.entry_id: r for r in s.execute(select(UserVocabMastery)).scalars()}
        rows[e1].fsrs_due_at = now - timedelta(hours=5)  # overdue
        rows[e2].fsrs_due_at = datetime(2026, 10, 18, 20, 0)  # 04:00 Oct 19 Shanghai = tomorrow
        rows[e1].confidence_score = 0.95  # mastered
        s.commit()
        overview = get_overview(s, s.get(User, user_id), tz=SHANGHAI, now_utc=now)

    levels = {l["quiz_key"]: l for l in overview["level_progress"]}
    assert levels["HSK1"] == {
        "quiz_key": "HSK1", "title": "HSK 1", "level": 1,
        "total": 1, "mastered": 1, "learning": 0, "new": 0,
    }
    assert (levels["HSK2"]["learning"], levels["HSK2"]["new"]) == (1, 0)
    assert [l["quiz_key"] for l in overview["level_progress"]] == ["HSK1", "HSK2"]

    up = overview["upcoming"]
    assert (up["due_now"], up["due_today"], up["due_tomorrow"], up["due_next_7_days"]) == (1, 1, 1, 2)
    assert [f["count"] for f in up["forecast"]] == [1, 1, 0, 0, 0, 0, 0]
    assert up["forecast"][0]["date"] == date(2026, 10, 18)


def test_overview_endpoint_returns_the_new_blocks(client: TestClient, seed_quizzes) -> None:
    token = _register(client, "endpoint@example.com")
    entry_id = client.get("/v1/quizzes/HSK1/entries", headers=_auth(token)).json()[0]["id"]
    client.post("/v1/srs/rate", headers=_auth(token), json={"entry_id": entry_id, "rating": "good"})

    res = client.get("/v1/account/overview", headers=_auth(token, "Europe/Paris"))
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["streak"] == {"current": 1, "best": 1, "studied_today": True}
    assert data["success_rate"]["last_7_days"] == 1.0
    assert data["success_rate"]["reviews_30_days"] == 1
    assert len(data["upcoming"]["forecast"]) == 7
    assert {l["quiz_key"] for l in data["level_progress"]} == {"HSK1", "HSK2"}
    # Heatmap and quiz curve come from the log now.
    assert sum(c["count"] for c in data["activity_heatmap"]) == 1
    assert data["quiz_progression"][-1]["avg_rating"] == 3.0


def test_days_before_the_log_still_show_in_the_heatmap(client: TestClient, seed_quizzes) -> None:
    """Old activity (before review_log existed) keeps its approximate heatmap cells."""
    token = _register(client, "legacy@example.com")
    user_id = client.get("/v1/auth/me", headers=_auth(token)).json()["id"]
    now = datetime(2026, 10, 18, 12, 0)
    with SessionLocal() as s:
        entry = s.execute(select(Entry)).scalars().first()
        s.add(
            UserVocabMastery(
                user_id=user_id, entry_id=entry.id, status="known", confidence_score=0.5,
                review_count=3, last_seen_at=datetime(2026, 9, 1, 12, 0), fsrs_last_rating=3,
            )
        )
        s.add(ReviewLog(user_id=user_id, entry_id=entry.id, rating=4, reviewed_at=datetime(2026, 10, 18, 9, 0)))
        s.commit()
        overview = get_overview(s, s.get(User, user_id), tz=parse_timezone("UTC"), now_utc=now)
    heat = {c["date"]: c["count"] for c in overview["activity_heatmap"]}
    assert heat[date(2026, 9, 1)] == 1  # approximation, before the log
    assert heat[date(2026, 10, 18)] == 1  # from the log
    assert overview["streak"]["current"] == 1  # streak only uses the log
