"""Classifiers (量词) tab: data, fill-in and usage quizzes, generation by Claude."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.services import classifier_service as cs
from tests.fake_anthropic import FakeAnthropic

BACKEND = Path(__file__).resolve().parents[1]


def _register(client: TestClient, email: str) -> str:
    res = client.post("/v1/auth/register", json={"email": email, "password": "supersecret"})
    assert res.status_code == 201
    return res.json()["access_token"]


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_sources_build_without_problems() -> None:
    spec = importlib.util.spec_from_file_location("build_classifiers", BACKEND / "scripts" / "build_classifiers.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.build(check_only=True) == 0


def test_levels_are_cumulative_and_follow_the_version() -> None:
    l1 = {c["hanzi"] for c in cs.available("3.0", 1)}
    l3 = {c["hanzi"] for c in cs.available("3.0", 3)}
    assert {"个", "本", "杯", "页", "间"} <= l1 and "张" not in l1
    assert l1 < l3 and {"张", "辆", "台", "顿"} <= l3
    # 只 is level 1 in 3.0, level 3 in 2.0; 台 is beyond level 3 in 2.0.
    assert "只" not in {c["hanzi"] for c in cs.available("2.0", 2)}
    assert "只" in {c["hanzi"] for c in cs.available("2.0", 3)}
    assert "台" not in {c["hanzi"] for c in cs.available("2.0", 3)}
    # Units of measure are not classifiers here.
    assert not {"元", "公斤", "分钟", "岁"} & l3


@pytest.mark.parametrize("version", ["3.0", "2.0"])
@pytest.mark.parametrize("level", [1, 2, 3])
def test_fill_questions_are_well_formed(version: str, level: int) -> None:
    known = cs.by_hanzi(version, level)
    for seed in range(15):
        for q in _fill(version, level, seed):
            assert len(q["options"]) == 4 and len(set(q["options"])) == 4
            assert q["options"][q["answer"]] == q["classifier"]
            assert all(o in known for o in q["options"])
            assert q["before"] + q["classifier"] + q["after"] == q["sentence"]


def _fill(version: str, level: int, seed: int):
    import random

    rng = random.Random(seed)
    pool = [s for c in cs.all_classifiers() for s in c["sentences"] if (s["levels"].get(version) or 99) <= level]
    return [cs.fill_question(s, version, level, rng) for s in pool]


@pytest.mark.parametrize("version", ["3.0", "2.0"])
@pytest.mark.parametrize("level", [1, 2, 3])
def test_usage_questions_never_offer_a_correct_distractor(version: str, level: int) -> None:
    fits: dict[str, set[str]] = {}
    for c in cs.all_classifiers():
        for n in c["nouns"]:
            fits.setdefault(n["zh"], set()).update({c["hanzi"], *n["also"]})
    usage_of = {c["hanzi"]: c["usage"] for c in cs.all_classifiers()}
    known = cs.by_hanzi(version, level)
    kinds = set()
    for seed in range(20):
        questions = cs.usage_quiz(version, level, count=10, seed=seed)
        assert len(questions) == 10
        for q in questions:
            kinds.add(q["kind"])
            assert len(set(q["options"])) == 4
            if q["kind"] == "cl_to_usage":
                assert q["options"][q["answer"]] == usage_of[q["classifier"]].replace(q["classifier"], "～")
                assert not any(h in o for h, o in zip(q["option_hanzi"], q["options"]))
                assert not ({"次", "回"} <= set(q["option_hanzi"]))
            else:
                assert q["options"][q["answer"]] == q["classifier"]
                assert all(o in known for o in q["options"])
            if q["kind"] == "usage_to_cl":
                assert q["classifier"] not in q["prompt"]
            if q["kind"] == "noun_to_cl":
                wrong = set(q["options"]) - {q["classifier"]}
                assert not wrong & fits[q["prompt"]], q
                assert not wrong & cs.OPEN_ENDED
    assert kinds == {"usage_to_cl", "noun_to_cl", "cl_to_usage"}


def test_list_and_quiz_endpoints(client: TestClient) -> None:
    token = _register(client, "classifiers@example.com")
    body = client.get("/v1/classifiers?level=1", headers=_auth(token)).json()
    assert body["version"] == "3.0" and len(body["classifiers"]) == 13
    ben = next(c for c in body["classifiers"] if c["hanzi"] == "本")
    assert ben["pinyin"] == "běn" and ben["sentence_count"] >= 3 and ben["nouns"][0]["zh"] == "书"
    assert len(client.get("/v1/classifiers?level=1&version=2.0", headers=_auth(token)).json()["classifiers"]) == 7

    fill = client.get("/v1/classifiers/quiz?mode=fill&level=3", headers=_auth(token)).json()
    assert len(fill["questions"]) == 10
    assert len({q["classifier"] for q in fill["questions"]}) >= 8  # spread over many classifiers
    focus = client.get("/v1/classifiers/quiz?mode=fill&level=1&hanzi=本", headers=_auth(token)).json()
    assert focus["questions"] and {q["classifier"] for q in focus["questions"]} == {"本"}
    usage = client.get("/v1/classifiers/quiz?mode=usage&level=2", headers=_auth(token)).json()
    assert len(usage["questions"]) == 10

    assert client.get("/v1/classifiers/quiz?mode=fill&level=1&hanzi=张", headers=_auth(token)).status_code == 404
    assert client.get("/v1/classifiers/quiz?mode=other&level=1", headers=_auth(token)).status_code == 422
    assert client.get("/v1/classifiers?level=1").status_code in (401, 403)


@pytest.fixture()
def fake_anthropic(monkeypatch):
    from app.core import config
    from app.services import llm_service

    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-fake-test-key")
    config.get_settings.cache_clear()
    fake = FakeAnthropic()
    monkeypatch.setattr(llm_service, "_get_client", lambda: fake)
    yield fake
    config.get_settings.cache_clear()


def test_generate_keeps_valid_sentences_for_the_user(client: TestClient, fake_anthropic) -> None:
    token = _register(client, "classifiers-gen@example.com")
    before = client.get("/v1/classifiers?level=1", headers=_auth(token)).json()["sentences"]
    res = client.post("/v1/classifiers/generate", headers=_auth(token), json={"level": 1})
    assert res.status_code == 200, res.text
    body = res.json()
    assert [q["classifier"] for q in body["questions"]] == ["本", "杯"]
    assert all(q["generated"] and q["id"].startswith("gen-") for q in body["questions"])
    assert body["quota_remaining"] == 19

    prompt = fake_anthropic.messages.create_calls[0]
    assert "本 :" in prompt["messages"][0]["content"] and "张 :" not in prompt["messages"][0]["content"]
    after = client.get("/v1/classifiers?level=1", headers=_auth(token)).json()["sentences"]
    assert after == before + 2
    # Same sentences again: duplicates are not stored twice.
    assert client.post("/v1/classifiers/generate", headers=_auth(token), json={"level": 1}).status_code == 502
    # Another user does not see them.
    other = _register(client, "classifiers-gen-2@example.com")
    assert client.get("/v1/classifiers?level=1", headers=_auth(other)).json()["sentences"] == before


def test_generate_on_one_classifier(client: TestClient, fake_anthropic) -> None:
    token = _register(client, "classifiers-focus@example.com")
    res = client.post("/v1/classifiers/generate", headers=_auth(token), json={"level": 1, "hanzi": "杯"})
    assert res.status_code == 200
    assert [q["classifier"] for q in res.json()["questions"]] == ["杯"]
    assert "杯 comme réponse" in fake_anthropic.messages.create_calls[0]["messages"][0]["content"]
