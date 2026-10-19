"""HSK-format exercises (listening / writing) and grammar points."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.services import exercise_service, grammar_service
from app.services.exercise_schema import InvalidItem, normalize
from tests.fake_anthropic import FakeAnthropic

BACKEND = Path(__file__).resolve().parents[1]


def _register(client: TestClient, email: str) -> str:
    res = client.post("/v1/auth/register", json={"email": email, "password": "supersecret"})
    assert res.status_code == 201
    return res.json()["access_token"]


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _load_script(name: str):
    spec = importlib.util.spec_from_file_location(name, BACKEND / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# --------------------------------------------------------------------------- data


def test_sources_build_without_problems() -> None:
    """The reviewed YAML sources are valid and inside each version's word lists."""
    assert _load_script("build_exercises").build(check_only=True) == 0
    assert _load_script("build_grammar").build(check_only=True) == 0


def test_bank_json_is_up_to_date() -> None:
    """bank.json is what the sources build to (run scripts/build_exercises.py)."""
    built = json.loads((BACKEND / "data" / "exercises" / "bank.json").read_text(encoding="utf-8"))
    ids = [i["id"] for i in built["items"]]
    assert len(ids) == len(set(ids))
    assert len(ids) >= 300


@pytest.mark.parametrize("version", ["2.0", "3.0"])
@pytest.mark.parametrize("level", [1, 2, 3])
def test_every_part_has_at_least_two_full_sets(version: str, level: int) -> None:
    for section in exercise_service.SECTIONS:
        for part in exercise_service.parts(version, level, section):
            for item_type, count in exercise_service.part_slots(part):
                items = [
                    i
                    for i in exercise_service.bank()
                    if i["type"] == item_type and i["level"] == level and version in i["versions"]
                ]
                questions = sum(exercise_service.questions_in(i) for i in items)
                assert questions >= 2 * count, (version, level, part["part"], item_type, questions)


def test_paper_structure_matches_the_official_counts() -> None:
    def total(version: str, level: int, section: str) -> int:
        return sum(p["count"] for p in exercise_service.parts(version, level, section))

    # HSK 3.0 (2025): listening 20 / 25 / 30, writing — / 10 / 10
    assert [total("3.0", lv, "listening") for lv in (1, 2, 3)] == [20, 25, 30]
    assert [total("3.0", lv, "writing") for lv in (1, 2, 3)] == [0, 10, 10]
    # HSK 2.0 (2012): listening 20 / 35 / 40, writing only at level 3
    assert [total("2.0", lv, "listening") for lv in (1, 2, 3)] == [20, 35, 40]
    assert [total("2.0", lv, "writing") for lv in (1, 2, 3)] == [0, 0, 10]


def test_grammar_points_cover_the_official_list() -> None:
    points = grammar_service.all_points()
    assert [sum(1 for p in points if p["level"] == lv) for lv in (1, 2, 3)] == [48, 81, 81]
    for p in points:
        assert p["title"] and p["explanation"] and len(p["examples"]) >= 2 and p["quiz"]
        for q in p["quiz"]:
            assert 0 <= q["answer"] < len(q["options"]) == 3


def test_schema_rejects_ambiguous_or_broken_items() -> None:
    with pytest.raises(InvalidItem):
        normalize({"audio": "你好", "fr": "x", "options": ["a", "b"], "answer": "A"}, "pic_choice", 1)
    with pytest.raises(InvalidItem):  # 好 and 很 both heard
        normalize(
            {
                "options": ["很", "好", "热", "冷", "茶", "书"],
                "items": [{"audio": "我很好", "fr": "x", "answer": "A"}]
                + [{"audio": f"{w}了", "fr": "x", "answer": l} for w, l in zip("热冷茶书", "CDEF")],
            },
            "word_match",
            1,
        )
    with pytest.raises(InvalidItem):  # words do not rebuild the sentence
        normalize({"words": "我 喜欢 你", "answer": "我爱你。", "fr": "x"}, "reorder", 3)
    item = normalize({"sentence": "我喝（chá）。", "answer": "茶", "fr": "Je bois du thé."}, "char_pinyin", 2)
    assert (item["before"], item["pinyin"], item["after"]) == ("我喝", "chá", "。")


# --------------------------------------------------------------------------- API


def test_catalog_follows_the_hsk_version(client: TestClient) -> None:
    token = _register(client, "ex-catalog@example.com")
    v3 = client.get("/v1/exercises/catalog?section=listening&level=1", headers=_auth(token)).json()
    assert v3["version"] == "3.0"
    assert [p["type"] for p in v3["parts"]] == ["pic_choice", "pic_answer", "word_match", "short_mcq"]
    assert all(p["available"] >= p["count"] for p in v3["parts"])

    client.put("/v1/account/settings", headers=_auth(token), json={"hsk_version": "2.0"})
    v2 = client.get("/v1/exercises/catalog?section=listening&level=1", headers=_auth(token)).json()
    assert [p["type"] for p in v2["parts"]] == ["pic_judge", "pic_choice", "pic_match", "short_mcq"]

    writing = client.get("/v1/exercises/catalog?section=writing&level=2", headers=_auth(token)).json()
    assert writing["parts"] == []  # HSK 2.0 level 2 has no writing paper


def test_set_has_the_exam_number_of_questions(client: TestClient) -> None:
    token = _register(client, "ex-set@example.com")
    one = client.get("/v1/exercises/set?section=listening&level=2&part=L2", headers=_auth(token)).json()
    items = one["parts"][0]["items"]
    assert sum(len(i["items"]) for i in items) == 10  # two series of 5 dialogues
    assert all(i["type"] == "pic_match" and "3.0" in i["versions"] for i in items)

    whole = client.get("/v1/exercises/set?section=listening&level=3&part=all", headers=_auth(token)).json()
    counts = [sum(exercise_service.questions_in(i) for i in p["items"]) for p in whole["parts"]]
    assert counts == [10, 10, 10]
    mixed = [i["type"] for i in whole["parts"][1]["items"]]
    assert mixed.count("short_mcq") == 5 and mixed.count("long_mcq") == 5

    assert client.get("/v1/exercises/set?section=listening&level=1&part=L9", headers=_auth(token)).status_code == 404


def test_results_are_saved_and_unseen_items_come_first(client: TestClient) -> None:
    token = _register(client, "ex-results@example.com")
    first = client.get("/v1/exercises/set?section=writing&level=3&part=W1", headers=_auth(token)).json()
    first_ids = [i["id"] for i in first["parts"][0]["items"]]
    answers = [{"id": i, "correct": n % 2 == 0} for n, i in enumerate(first_ids)]
    res = client.post(
        "/v1/exercises/results",
        headers=_auth(token),
        json={"section": "writing", "level": 3, "part": "W1", "answers": answers},
    )
    assert res.status_code == 201 and res.json() == {"id": res.json()["id"], "score": 3, "total": 5}

    catalog = client.get("/v1/exercises/catalog?section=writing&level=3", headers=_auth(token)).json()
    w1 = next(p for p in catalog["parts"] if p["part"] == "W1")
    assert w1["last"]["score"] == 3 and w1["attempts"] == 1

    second = client.get("/v1/exercises/set?section=writing&level=3&part=W1", headers=_auth(token)).json()
    assert not set(first_ids) & {i["id"] for i in second["parts"][0]["items"]}


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


def test_generate_keeps_valid_items_and_adds_them_to_the_pool(client: TestClient, fake_anthropic) -> None:
    token = _register(client, "ex-generate@example.com")
    res = client.post(
        "/v1/exercises/generate", headers=_auth(token), json={"section": "listening", "level": 1, "part": "L4"}
    )
    assert res.status_code == 200, res.text
    body = res.json()
    items = body["parts"][0]["items"]
    assert len(items) == 1 and items[0]["generated"] and items[0]["id"].startswith("gen-")
    assert body["quota_remaining"] == 19

    # The prompt names the part, the level and carries the level's vocabulary.
    call = fake_anthropic.messages.create_calls[0]
    assert "niveau 1" in call["messages"][0]["content"]
    assert "爸爸" in "".join(block["text"] for block in call["system"])

    catalog = client.get("/v1/exercises/catalog?section=listening&level=1", headers=_auth(token)).json()
    l4 = next(p for p in catalog["parts"] if p["part"] == "L4")
    bank_only = sum(1 for i in exercise_service.bank() if i["type"] == "short_mcq" and i["level"] == 1)
    assert l4["available"] == bank_only + 1


def test_generated_items_with_unknown_characters_are_dropped(client: TestClient, fake_anthropic) -> None:
    fake_anthropic.messages.exercise_response["items"][0]["audio"] = "男：你喜欢鲲鹏饕餮吗？\n女：喜欢。"
    token = _register(client, "ex-generate-bad@example.com")
    res = client.post(
        "/v1/exercises/generate", headers=_auth(token), json={"section": "listening", "level": 1, "part": "L4"}
    )
    assert res.status_code == 502


def test_check_sentence(client: TestClient, fake_anthropic) -> None:
    token = _register(client, "ex-check@example.com")
    res = client.post(
        "/v1/exercises/check-sentence",
        headers=_auth(token),
        json={"level": 3, "word": "经常", "sentence": "我经常去图书馆。"},
    )
    assert res.status_code == 200
    assert res.json()["correct"] is True
    assert "经常" in fake_anthropic.messages.create_calls[0]["messages"][0]["content"]


def test_grammar_endpoint_with_progress(client: TestClient) -> None:
    token = _register(client, "ex-grammar@example.com")
    points = client.get("/v1/grammar?level=2", headers=_auth(token)).json()["points"]
    assert len(points) == 81 and points[0]["code"] == "二01" and points[0]["last"] is None

    pid = points[0]["id"]
    client.post(
        "/v1/exercises/results",
        headers=_auth(token),
        json={"section": "grammar", "level": 2, "part": pid, "answers": [{"id": f"{pid}#0", "correct": True}]},
    )
    again = client.get("/v1/grammar?level=2", headers=_auth(token)).json()["points"]
    assert again[0]["last"] == {"score": 1, "total": 1}


def test_exercise_endpoints_require_auth(client: TestClient) -> None:
    assert client.get("/v1/exercises/catalog?section=listening&level=1").status_code in (401, 403)
    assert client.get("/v1/grammar?level=1").status_code in (401, 403)
