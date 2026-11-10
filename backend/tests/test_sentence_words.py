"""Écriture HSK, 'Écris une phrase avec le mot donné': imposed words from the user's own vocabulary."""

from __future__ import annotations

import random
from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.session import SessionLocal
from app.models import Entry, Quiz, UserVocabMastery
from app.services import exercise_service as es
from tests.conftest import link_entries_to_home_quiz
from tests.fake_anthropic import FakeAnthropic


def _register(client: TestClient, email: str) -> tuple[str, int]:
    res = client.post("/v1/auth/register", json={"email": email, "password": "supersecret"})
    return res.json()["access_token"], res.json()["user"]["id"]


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def words() -> dict[str, list[int]]:
    """HSK 3.0 levels 1, 3 and 4: 40 words each. Returns entry ids per level."""
    now = datetime.utcnow()
    out: dict[str, list[int]] = {}
    with SessionLocal() as s:
        for level in (1, 3, 4):
            quiz = Quiz(key=f"HSK{level}", title=f"HSK {level}", level=level, created_at=now, updated_at=now)
            s.add(quiz)
            s.flush()
            entries = [
                Entry(quiz_id=quiz.id, hanzi=f"词{level}{i:02d}", pinyin="cí", translation=f"mot {level}-{i}", is_active=True, created_at=now)
                for i in range(40)
            ]
            s.add_all(entries)
            s.flush()
            out[f"L{level}"] = [e.id for e in entries]
        link_entries_to_home_quiz(s)
        s.commit()
    return out


def _seen(user_id: int, scores: dict[int, float]) -> None:
    now = datetime.utcnow()
    with SessionLocal() as s:
        s.add_all(
            UserVocabMastery(user_id=user_id, entry_id=e, status="learning", confidence_score=c, review_count=2,
                             last_seen_at=now, created_at=now, updated_at=now)
            for e, c in scores.items()
        )
        s.commit()


def test_seen_words_only_and_levels_1_to_3(client: TestClient, words) -> None:
    _, user_id = _register(client, "seen@example.com")
    # 3 seen words at level 1, 2 at level 3, 5 at level 4 (out of the exam); the rest never seen.
    _seen(user_id, {**{e: 0.8 for e in words["L1"][:3]}, **{e: 0.2 for e in words["L3"][:2]}, **{e: 0.1 for e in words["L4"][:5]}})
    with SessionLocal() as s:
        pool = es.sentence_words(s, user_id, "3.0", 3, "seen")
        assert {w["entry"].id for w in pool} == set(words["L1"][:3] + words["L3"][:2])
        items = es.sentence_items(s, user_id, "3.0", 3, "seen", 5, random.Random(1))
    assert len(items) == 5 and len({i["id"] for i in items}) == 5
    assert all(i["type"] == "make_sentence" and i["word"].startswith("词") and i["translation"] for i in items)
    assert all(i["id"].startswith("word-") for i in items)


def test_weak_words_are_the_50_lowest_scores_below_half(client: TestClient, words) -> None:
    _, user_id = _register(client, "weak@example.com")
    # 70 seen words: 60 "à revoir" with scores 0.00..0.59 step 0.01 -> 50 below 0.5; 10 known (0.9).
    pool_ids = words["L1"] + words["L3"]
    scores = {e: i / 100 for i, e in enumerate(pool_ids[:60])}
    scores.update({e: 0.9 for e in pool_ids[60:70]})
    _seen(user_id, scores)
    with SessionLocal() as s:
        weak = es.sentence_words(s, user_id, "3.0", 3, "weak")
        assert len(weak) == 50
        assert max(w["confidence"] for w in weak) < 0.5
        assert [w["confidence"] for w in weak] == sorted(w["confidence"] for w in weak)
        # 55 words below 0.5 now (five at 0.495): still the 50 lowest (0.00..0.49).
        for e in pool_ids[60:65]:
            row = s.execute(select(UserVocabMastery).where(UserVocabMastery.user_id == user_id, UserVocabMastery.entry_id == e)).scalar_one()
            row.confidence_score = 0.495
        s.commit()
        weak = es.sentence_words(s, user_id, "3.0", 3, "weak")
        assert len(weak) == 50 and all(w["confidence"] <= 0.49 for w in weak)
        assert not {w["entry"].id for w in weak} & set(pool_ids[60:65])
        picked = {i["id"] for i in es.sentence_items(s, user_id, "3.0", 3, "weak", 5, random.Random(3))}
    assert picked <= {f"word-{w['entry'].id}" for w in weak}


def test_set_and_catalog_endpoints(client: TestClient, words) -> None:
    token, user_id = _register(client, "sentence-api@example.com")
    _seen(user_id, {**{e: 0.7 for e in words["L1"][:10]}, **{e: 0.3 for e in words["L3"][:3]}})

    catalog = client.get("/v1/exercises/catalog?section=writing&level=3&version=3.0", headers=_auth(token)).json()
    w2 = next(p for p in catalog["parts"] if p["type"] == "make_sentence")
    assert w2["word_counts"] == {"seen": 13, "weak": 3} and w2["available"] == 13
    assert next(p for p in catalog["parts"] if p["type"] == "char_pinyin")["word_counts"] is None

    seen_set = client.get("/v1/exercises/set?section=writing&level=3&part=W2&version=3.0", headers=_auth(token)).json()
    part = seen_set["parts"][0]
    assert part["word_source"] == "seen" and part["word_pool"] == 13 and len(part["items"]) == 5

    weak_set = client.get("/v1/exercises/set?section=writing&level=3&part=W2&version=3.0&words=weak", headers=_auth(token)).json()
    part = weak_set["parts"][0]
    # Only 3 words to review: a shorter series.
    assert part["word_source"] == "weak" and part["word_pool"] == 3 and len(part["items"]) == 3
    assert {i["id"] for i in part["items"]} == {f"word-{e}" for e in words["L3"][:3]}

    whole = client.get("/v1/exercises/set?section=writing&level=3&part=all&version=3.0&words=weak", headers=_auth(token)).json()
    assert [p["part"] for p in whole["parts"]][-1] == "W2"

    gen = client.post("/v1/exercises/generate", headers=_auth(token), json={"section": "writing", "level": 3, "part": "W2", "version": "3.0"})
    assert gen.status_code == 400
    assert client.get("/v1/exercises/set?section=writing&level=3&part=W2&words=other", headers=_auth(token)).status_code == 422


def test_no_seen_word_drops_the_part(client: TestClient, words) -> None:
    token, _ = _register(client, "nothing-seen@example.com")
    res = client.get("/v1/exercises/set?section=writing&level=3&part=W2&version=3.0", headers=_auth(token)).json()
    assert res["parts"] == []


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


def test_check_sentence_gives_a_model_only_when_wrong(client: TestClient, fake_anthropic) -> None:
    token, _ = _register(client, "model@example.com")
    body = {"level": 3, "word": "认真", "sentence": "他很认真。", "meaning": "sérieux, consciencieux"}
    fake_anthropic.messages.sentence_check_response = {
        "correct": True, "uses_word": True, "corrected": "他很认真。", "pinyin": "tā hěn rènzhēn.",
        "translation": "Il est très sérieux.", "explanation": "Correct.",
        "model": "我们要认真学习。", "model_pinyin": "x", "model_translation": "y",
    }
    ok = client.post("/v1/exercises/check-sentence", headers=_auth(token), json=body).json()
    assert ok["correct"] is True and ok["model"] == "" and ok["model_translation"] == ""
    sent = fake_anthropic.messages.create_calls[-1]["messages"][0]["content"]
    assert "Mot imposé : 认真 (sens : sérieux, consciencieux)" in sent

    fake_anthropic.messages.sentence_check_response = {
        "correct": False, "uses_word": True, "corrected": "他学习很认真。", "pinyin": "", "translation": "",
        "explanation": "Il manque le verbe.", "model": "我们要认真学习。", "model_pinyin": "wǒmen yào rènzhēn xuéxí.",
        "model_translation": "Nous devons étudier sérieusement.",
    }
    wrong = client.post("/v1/exercises/check-sentence", headers=_auth(token), json={**body, "sentence": "他认真。"}).json()
    assert wrong["correct"] is False
    assert wrong["model"] == "我们要认真学习。" and wrong["model_translation"] == "Nous devons étudier sérieusement."
