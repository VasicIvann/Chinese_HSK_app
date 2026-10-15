"""Tests for the vocabulary example endpoints (Anthropic fully mocked)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from tests.fake_anthropic import FakeAnthropic


def _register(client: TestClient, email: str) -> str:
    res = client.post("/v1/auth/register", json={"email": email, "password": "supersecret"})
    assert res.status_code == 201
    return res.json()["access_token"]


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _entry_id(client: TestClient, token: str, quiz: str = "HSK1") -> int:
    res = client.get(f"/v1/quizzes/{quiz}/entries", headers=_auth(token))
    assert res.status_code == 200
    return res.json()[0]["id"]


@pytest.fixture()
def fake_anthropic(monkeypatch):
    from app.core import config
    from app.services import llm_service

    config.get_settings.cache_clear()
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-fake-test-key")
    config.get_settings.cache_clear()

    fake = FakeAnthropic()
    monkeypatch.setattr(llm_service, "_get_client", lambda: fake)
    yield fake
    config.get_settings.cache_clear()


def test_examples_require_auth(client: TestClient) -> None:
    assert client.get("/v1/examples?entry_id=1").status_code in (401, 403)
    assert client.post("/v1/examples", json={"entry_id": 1}).status_code in (401, 403)


def test_list_is_empty_before_generation(client: TestClient, seed_quizzes) -> None:
    token = _register(client, "ex-empty@example.com")
    entry_id = _entry_id(client, token)
    res = client.get(f"/v1/examples?entry_id={entry_id}", headers=_auth(token))
    assert res.status_code == 200
    assert res.json() == []


def test_generate_saves_and_lists_example(
    client: TestClient, seed_quizzes, fake_anthropic
) -> None:
    token = _register(client, "ex-gen@example.com")
    entry_id = _entry_id(client, token)

    res = client.post("/v1/examples", json={"entry_id": entry_id}, headers=_auth(token))
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["example"]["sentence"] == "我爱我的家。"
    assert body["example"]["entry_id"] == entry_id
    assert body["example"]["hsk_level"] == 1
    assert body["example"]["general_meaning"]
    assert body["example"]["decomposition"].startswith("爱 contient 心")
    assert body["quota_remaining"] == 99

    # The prompt carries the word and its HSK level.
    user_msg = fake_anthropic.messages.create_calls[0]["messages"][0]["content"]
    assert "爱" in user_msg and "HSK 1" in user_msg

    listed = client.get(f"/v1/examples?entry_id={entry_id}", headers=_auth(token)).json()
    assert len(listed) == 1
    assert listed[0]["id"] == body["example"]["id"]


def test_second_generation_avoids_previous_sentence_and_lists_newest_first(
    client: TestClient, seed_quizzes, fake_anthropic
) -> None:
    token = _register(client, "ex-two@example.com")
    entry_id = _entry_id(client, token)

    first = client.post("/v1/examples", json={"entry_id": entry_id}, headers=_auth(token)).json()
    fake_anthropic.messages.example_response = {
        **fake_anthropic.messages.example_response,
        "sentence": "妈妈爱我。",
    }
    second = client.post("/v1/examples", json={"entry_id": entry_id}, headers=_auth(token)).json()

    second_prompt = fake_anthropic.messages.create_calls[1]["messages"][0]["content"]
    assert "我爱我的家。" in second_prompt

    listed = client.get(f"/v1/examples?entry_id={entry_id}", headers=_auth(token)).json()
    assert [e["id"] for e in listed] == [second["example"]["id"], first["example"]["id"]]


def test_examples_are_private_per_user(
    client: TestClient, seed_quizzes, fake_anthropic
) -> None:
    alice = _register(client, "ex-alice@example.com")
    bob = _register(client, "ex-bob@example.com")
    entry_id = _entry_id(client, alice)

    client.post("/v1/examples", json={"entry_id": entry_id}, headers=_auth(alice))
    assert client.get(f"/v1/examples?entry_id={entry_id}", headers=_auth(bob)).json() == []


def test_generate_unknown_entry_returns_404(
    client: TestClient, seed_quizzes, fake_anthropic
) -> None:
    token = _register(client, "ex-404@example.com")
    res = client.post("/v1/examples", json={"entry_id": 999999}, headers=_auth(token))
    assert res.status_code == 404
    assert fake_anthropic.messages.create_calls == []


def test_unusable_model_output_returns_502_and_saves_nothing(
    client: TestClient, seed_quizzes, fake_anthropic
) -> None:
    token = _register(client, "ex-502@example.com")
    entry_id = _entry_id(client, token)
    fake_anthropic.messages.example_response = {"sentence": ""}

    res = client.post("/v1/examples", json={"entry_id": entry_id}, headers=_auth(token))
    assert res.status_code == 502
    assert client.get(f"/v1/examples?entry_id={entry_id}", headers=_auth(token)).json() == []


def test_subject_generation_still_uses_subject_response(
    client: TestClient, fake_anthropic
) -> None:
    """Guard: routing in the fake must not break the existing subject endpoint."""
    token = _register(client, "ex-subject@example.com")
    res = client.post(
        "/v1/expression/subjects/generate", json={"level": 1}, headers=_auth(token)
    )
    assert res.status_code == 200
    assert res.json()["subject"] == "Décrivez votre week-end idéal."


def test_missing_decomposition_is_saved_as_empty_string(
    client: TestClient, seed_quizzes, fake_anthropic
) -> None:
    """An answer without the new field still produces a valid example."""
    token = _register(client, "ex-nodecomp@example.com")
    entry_id = _entry_id(client, token)
    response = dict(fake_anthropic.messages.example_response)
    response.pop("decomposition")
    fake_anthropic.messages.example_response = response

    res = client.post("/v1/examples", json={"entry_id": entry_id}, headers=_auth(token))
    assert res.status_code == 201
    assert res.json()["example"]["decomposition"] == ""


def test_prompt_asks_for_decomposition() -> None:
    from app.services import llm_service

    assert "decomposition" in llm_service.EXAMPLE_FIELDS
    assert "decomposition" in llm_service.EXAMPLE_SYSTEM_PROMPT
