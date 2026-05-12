"""Tests for the Expression écrite endpoints.

Anthropic calls are fully mocked via `FakeAnthropic`. No network traffic.
"""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from tests.fake_anthropic import FakeAnthropic


def _register(client: TestClient, email: str = "expr@example.com") -> str:
    res = client.post("/v1/auth/register", json={"email": email, "password": "supersecret"})
    assert res.status_code == 201
    return res.json()["access_token"]


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def fake_anthropic(monkeypatch):
    """Patch the LLM service to use FakeAnthropic + a non-empty key."""
    from app.core import config
    from app.services import llm_service

    config.get_settings.cache_clear()
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-fake-test-key")
    config.get_settings.cache_clear()

    fake = FakeAnthropic()
    monkeypatch.setattr(llm_service, "_get_client", lambda: fake)
    yield fake
    config.get_settings.cache_clear()


def _parse_sse(body: str) -> list[tuple[str, dict]]:
    """Split a raw SSE body into a list of (event, data) tuples."""
    events: list[tuple[str, dict]] = []
    current_event = "message"
    for block in body.strip().split("\n\n"):
        if not block.strip():
            continue
        data_lines: list[str] = []
        for line in block.splitlines():
            if line.startswith("event: "):
                current_event = line[len("event: ") :].strip()
            elif line.startswith("data: "):
                data_lines.append(line[len("data: ") :])
        if data_lines:
            payload = json.loads("\n".join(data_lines))
            events.append((current_event, payload))
            current_event = "message"
    return events


def test_subjects_pool_returns_curated_items(client: TestClient) -> None:
    token = _register(client)
    res = client.get("/v1/expression/subjects?level=1", headers=_auth(token))
    assert res.status_code == 200
    items = res.json()
    assert len(items) >= 5
    assert all("subject" in item and "keywords" in item for item in items)


def test_subjects_requires_auth(client: TestClient) -> None:
    assert client.get("/v1/expression/subjects").status_code in (401, 403)


def test_generate_subject_calls_claude_and_decrements_quota(
    client: TestClient, fake_anthropic: FakeAnthropic
) -> None:
    token = _register(client)

    res = client.post(
        "/v1/expression/subjects/generate",
        headers=_auth(token),
        json={"level": 2},
    )
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["subject"]
    assert data["quota_remaining"] == 49  # 50 - 1
    assert len(fake_anthropic.messages.create_calls) == 1


def test_correct_streams_sse_events_and_persists(
    client: TestClient, fake_anthropic: FakeAnthropic, seed_quizzes: None
) -> None:
    token = _register(client)

    res = client.post(
        "/v1/expression/correct",
        headers=_auth(token),
        json={"level": 2, "subject": "Présentez votre famille.", "user_text": "我有一个哥哥。"},
    )
    assert res.status_code == 200, res.text
    assert res.headers["content-type"].startswith("text/event-stream")

    events = _parse_sse(res.text)
    event_types = [name for name, _ in events]
    assert event_types[0] == "start"
    assert "partial" in event_types
    assert "complete" in event_types
    assert event_types[-1] == "persisted"

    complete = next(payload for name, payload in events if name == "complete")
    assert complete["correction"]["score"] == 80

    persisted = next(payload for name, payload in events if name == "persisted")
    assert persisted["attempt_id"] >= 1
    assert persisted["relearned_count"] == 0

    # /attempts now has one entry.
    history = client.get("/v1/expression/attempts", headers=_auth(token)).json()
    assert len(history) == 1
    assert history[0]["score"] == 80


def test_correct_requires_chinese_in_user_text(
    client: TestClient, fake_anthropic: FakeAnthropic, seed_quizzes: None
) -> None:
    token = _register(client)
    res = client.post(
        "/v1/expression/correct",
        headers=_auth(token),
        json={"level": 1, "subject": "Décrivez", "user_text": "no chinese here"},
    )
    assert res.status_code == 422


def test_correct_queues_vocab_mistakes_into_srs(
    client: TestClient, monkeypatch, seed_quizzes: None
) -> None:
    """Claude returns vocabulary_mistakes=['爱'] → that entry should land in SRS as 'again'."""
    from app.core import config
    from app.services import llm_service

    config.get_settings.cache_clear()
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-fake-test-key")
    config.get_settings.cache_clear()

    fake = FakeAnthropic(
        correction_response={
            "score": 40,
            "corrected_version": "我喜欢一个朋友。",
            "pinyin": "wǒ xǐ huān yī gè péng yǒu.",
            "french_translation": "J'aime un ami.",
            "errors": [
                {"type": "vocabulaire", "segment": "爱", "correction": "喜欢", "explanation": "Trop fort."}
            ],
            "vocabulary_mistakes": ["爱"],
            "strengths": [],
            "next_step_advice": "Distinguez 爱 (aimer fort) et 喜欢 (apprécier).",
        }
    )
    monkeypatch.setattr(llm_service, "_get_client", lambda: fake)

    token = _register(client, email="vocab@example.com")
    res = client.post(
        "/v1/expression/correct",
        headers=_auth(token),
        json={"level": 1, "subject": "Décrivez votre meilleur ami.", "user_text": "我爱我的朋友。"},
    )
    assert res.status_code == 200, res.text
    events = _parse_sse(res.text)
    persisted = next(p for name, p in events if name == "persisted")
    assert persisted["relearned_count"] == 1

    # The mastery list now contains a 'faux' record on the matching entry.
    mastery = client.get("/v1/mastery", headers=_auth(token)).json()
    assert any(item["status"] == "faux" and item["hanzi"] == "爱" for item in mastery)

    config.get_settings.cache_clear()


def test_correct_503_when_anthropic_not_configured(
    client: TestClient, monkeypatch, seed_quizzes: None
) -> None:
    from app.core import config

    monkeypatch.setenv("ANTHROPIC_API_KEY", "")
    config.get_settings.cache_clear()

    token = _register(client, email="noconf@example.com")
    res = client.post(
        "/v1/expression/correct",
        headers=_auth(token),
        json={"level": 1, "subject": "Décrivez votre matinée.", "user_text": "我今天很好。"},
    )
    assert res.status_code == 503
    config.get_settings.cache_clear()


def test_quota_endpoint_reflects_usage(client: TestClient, fake_anthropic: FakeAnthropic) -> None:
    token = _register(client)
    initial = client.get("/v1/expression/quota", headers=_auth(token)).json()
    assert initial["correction"]["remaining"] == 20
    assert initial["subject_generation"]["remaining"] == 50

    client.post(
        "/v1/expression/subjects/generate", headers=_auth(token), json={"level": 1}
    )
    after = client.get("/v1/expression/quota", headers=_auth(token)).json()
    assert after["subject_generation"]["count"] == 1
    assert after["subject_generation"]["remaining"] == 49


def test_attempts_requires_auth(client: TestClient) -> None:
    assert client.get("/v1/expression/attempts").status_code in (401, 403)
