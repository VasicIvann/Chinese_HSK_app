"""Classifiers (量词) of HSK levels 1-3: fiches, fill-in sentences and usage quizzes.

`data/classifiers/classifiers.json` is built by `scripts/build_classifiers.py` from the
reviewed sources in `data/classifiers/src` (fiches, sentences, level of every sentence
in each version). Sentences written by Claude for a user (`GeneratedExercise`,
item_type "classifier_fill") join that user's pool.

A level shows its classifiers cumulatively: HSK 3 = levels 1, 2 and 3.
"""

from __future__ import annotations

import json
import random
import re
from datetime import datetime
from functools import lru_cache
from itertools import zip_longest
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import GeneratedExercise
from app.services.exercise_service import known_chars

PATH = Path(__file__).resolve().parents[2] / "data" / "classifiers" / "classifiers.json"
ITEM_TYPE = "classifier_fill"
BLANK = re.compile(r"\{([^{}]+)\}")
# Usages too close to tell apart in a "which usage?" question.
SAME_USAGE = [{"次", "回"}]
# Classifiers that go with many nouns (一种鱼, 一群猫, 一块鱼, 一包纸, 一对鸟, 一层纸…):
# never offered as a wrong answer for "一（ ）+ noun".
OPEN_ENDED = {"个", "种", "群", "块", "包", "对", "层"}


@lru_cache(maxsize=1)
def all_classifiers() -> list[dict[str, Any]]:
    if not PATH.exists():
        return []
    with open(PATH, encoding="utf-8") as f:
        return json.load(f)["classifiers"]


def _level(c: dict[str, Any], version: str) -> int | None:
    return c["levels"].get(version)


def available(version: str, level: int) -> list[dict[str, Any]]:
    """Classifiers known at `level` (cumulative), lowest level first."""
    out = [c for c in all_classifiers() if (_level(c, version) or 99) <= level]
    return sorted(out, key=lambda c: _level(c, version) or 99)


def by_hanzi(version: str, level: int) -> dict[str, dict[str, Any]]:
    return {c["hanzi"]: c for c in available(version, level)}


def fiches(db: Session, user_id: int, version: str, level: int) -> list[dict[str, Any]]:
    generated = _count_by_answer(_generated(db, user_id, version, level))
    out = []
    for c in available(version, level):
        sentences = [s for s in c["sentences"] if (s["levels"].get(version) or 99) <= level]
        out.append(
            {
                "hanzi": c["hanzi"],
                "pinyin": c["pinyin"],
                "kind": c["kind"],
                "level": _level(c, version),
                "usage": c["usage"],
                "explanation": c["explanation"],
                "traps": c["traps"],
                "nouns": [
                    {"zh": n["zh"], "fr": n["fr"], "in_level": (n["levels"].get(version) or 99) <= level}
                    for n in c["nouns"]
                ],
                "examples": c["examples"],
                "sentence_count": len(sentences) + generated.get(c["hanzi"], 0),
            }
        )
    return out


def _count_by_answer(items: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        counts[item["answer"]] = counts.get(item["answer"], 0) + 1
    return counts


# --------------------------------------------------------------------------- fill-in sentences


def _generated(db: Session, user_id: int, version: str, level: int) -> list[dict[str, Any]]:
    rows = db.execute(
        select(GeneratedExercise).where(
            GeneratedExercise.user_id == user_id,
            GeneratedExercise.version == version,
            GeneratedExercise.level <= level,
            GeneratedExercise.item_type == ITEM_TYPE,
        )
    ).scalars()
    out = []
    for row in rows:
        item = json.loads(row.payload)
        out.append({**item, "id": f"gen-{row.id}", "generated": True})
    return out


def sentence_pool(db: Session, user_id: int, version: str, level: int) -> list[dict[str, Any]]:
    """Bank sentences usable at `level` in `version`, plus the user's generated ones."""
    known = by_hanzi(version, level)
    bank = [
        s
        for c in all_classifiers()
        for s in c["sentences"]
        if (s["levels"].get(version) or 99) <= level and s["answer"] in known
    ]
    own = [s for s in _generated(db, user_id, version, level) if s["answer"] in known]
    return bank + own


def fill_question(sentence: dict[str, Any], version: str, level: int, rng: random.Random) -> dict[str, Any]:
    known = by_hanzi(version, level)
    wrong = [w for w in sentence["wrong"] if w in known and w != sentence["answer"]]
    rng.shuffle(wrong)
    options = [sentence["answer"], *wrong[:3]]
    rng.shuffle(options)
    before, _, after = BLANK.split(sentence["zh"], maxsplit=1)
    answer = known[sentence["answer"]]
    return {
        "id": sentence["id"],
        "mode": "fill",
        "before": before,
        "after": after,
        "sentence": BLANK.sub(r"\1", sentence["zh"]),
        "options": options,
        "answer": options.index(sentence["answer"]),
        "fr": sentence.get("fr", ""),
        "classifier": sentence["answer"],
        "explain": answer["usage"],
        "generated": bool(sentence.get("generated")),
    }


def fill_quiz(
    db: Session,
    user_id: int,
    version: str,
    level: int,
    *,
    count: int = 10,
    hanzi: str | None = None,
    seed: int | None = None,
) -> list[dict[str, Any]]:
    rng = random.Random(seed)
    pool = sentence_pool(db, user_id, version, level)
    if hanzi:
        pool = [s for s in pool if s["answer"] == hanzi]
    rng.shuffle(pool)
    if not hanzi:
        # Half of the set on the classifiers new at this level, then anything; one sentence
        # per classifier before a second one, so a set covers as many as possible.
        known = by_hanzi(version, level)
        newest = [s for s in pool if _level(known[s["answer"]], version) == level]
        first = _spread(newest, count // 2) if level > 1 else []
        rest = _spread([s for s in pool if s not in first], count - len(first))
        pool = first + rest
        rng.shuffle(pool)
    return [fill_question(s, version, level, rng) for s in pool[:count]]


def _spread(items: list[dict[str, Any]], count: int) -> list[dict[str, Any]]:
    seen: dict[str, int] = {}
    ranked = []
    for s in items:
        seen[s["answer"]] = seen.get(s["answer"], 0) + 1
        ranked.append((seen[s["answer"]], s))
    ranked.sort(key=lambda x: x[0])
    return [s for _, s in ranked[:count]]


# --------------------------------------------------------------------------- usage quiz


def _others(target: dict[str, Any], pool: list[dict[str, Any]], rng: random.Random, exclude: set[str]) -> list[dict[str, Any]]:
    """Three other classifiers, of the same kind when possible, never two of near-identical usage."""
    blocked = set(exclude) | {target["hanzi"]}
    candidates = [c for c in pool if c["hanzi"] not in blocked]
    rng.shuffle(candidates)
    same = [c for c in candidates if c["kind"] == target["kind"] or "both" in (c["kind"], target["kind"])]
    other = [c for c in candidates if c not in same]
    chosen: list[dict[str, Any]] = []
    taken = {target["hanzi"]}
    for c in same + other:
        group = next((g for g in SAME_USAGE if c["hanzi"] in g), {c["hanzi"]})
        if group & taken:
            continue
        chosen.append(c)
        taken |= group
        if len(chosen) == 3:
            break
    return chosen


def usage_quiz(version: str, level: int, *, count: int = 10, seed: int | None = None) -> list[dict[str, Any]]:
    rng = random.Random(seed)
    pool = available(version, level)
    if len(pool) < 4:
        return []
    # every noun → the classifiers that are correct with it
    fits: dict[str, set[str]] = {}
    for c in all_classifiers():
        for n in c["nouns"]:
            fits.setdefault(n["zh"], set()).update({c["hanzi"], *n.get("also", [])})

    # Alternate the classifiers new at this level and the older ones.
    newest = [c for c in pool if _level(c, version) == level]
    older = [c for c in pool if _level(c, version) != level]
    rng.shuffle(newest)
    rng.shuffle(older)
    targets = [c for pair in zip_longest(newest, older) for c in pair if c is not None]
    kinds = ["usage_to_cl", "noun_to_cl", "cl_to_usage"]
    questions: list[dict[str, Any]] = []
    used: dict[str, set[str]] = {}
    # Rounds over the classifiers (newest first), one question kind not used yet each time.
    for _ in range(len(kinds)):
        for target in targets:
            if len(questions) >= count:
                break
            todo = [k for k in kinds if k not in used.setdefault(target["hanzi"], set())]
            rng.shuffle(todo)
            for kind in todo:
                q = _usage_question(target, kind, pool, fits, version, level, rng)
                used[target["hanzi"]].add(kind)
                if q:
                    questions.append(q)
                    break
    rng.shuffle(questions)
    return questions


def masked_usage(c: dict[str, Any]) -> str:
    """The usage line with the classifier itself hidden (这种水果 → 这～水果): it would give the answer."""
    return c["usage"].replace(c["hanzi"], "～")


def _usage_question(
    target: dict[str, Any],
    kind: str,
    pool: list[dict[str, Any]],
    fits: dict[str, set[str]],
    version: str,
    level: int,
    rng: random.Random,
) -> dict[str, Any] | None:
    q: dict[str, Any] = {"id": f"usage-{target['hanzi']}-{kind}", "mode": "usage", "kind": kind, "classifier": target["hanzi"]}
    if kind == "noun_to_cl":
        nouns = [n for n in target["nouns"] if (n["levels"].get(version) or 99) <= level]
        if not nouns:
            return None
        noun = rng.choice(nouns)
        others = _others(target, pool, rng, fits.get(noun["zh"], set()) | OPEN_ENDED | {noun["zh"]})
    else:
        others = _others(target, pool, rng, set())
    if len(others) < 3:
        return None
    options = [target, *others]
    rng.shuffle(options)
    answer = options.index(target)
    if kind == "cl_to_usage":
        q |= {
            "prompt": target["hanzi"],
            "pinyin": target["pinyin"],
            "options": [masked_usage(c) for c in options],
            "option_hanzi": [c["hanzi"] for c in options],
        }
    elif kind == "noun_to_cl":
        q |= {"prompt": noun["zh"], "prompt_fr": noun["fr"], "options": [c["hanzi"] for c in options]}
    else:
        q |= {"prompt": masked_usage(target), "options": [c["hanzi"] for c in options]}
    q["answer"] = answer
    q["explain"] = f"{target['hanzi']} ({target['pinyin']}) : {target['usage']}"
    return q


# --------------------------------------------------------------------------- generated sentences


def validate_generated(raw: dict[str, Any], version: str, level: int) -> dict[str, Any] | None:
    """A sentence written by Claude, if usable: one blank holding a known classifier and
    three distinct, known wrong options."""
    known = by_hanzi(version, level)
    zh = str(raw.get("zh") or "").strip()
    blanks = BLANK.findall(zh)
    wrong = [str(w).strip() for w in raw.get("wrong") or []]
    if len(blanks) != 1 or blanks[0] not in known or len(zh) > 60:
        return None
    answer = blanks[0]
    if len(wrong) != 3 or len(set(wrong)) != 3 or answer in wrong or any(w not in known for w in wrong):
        return None
    # at most one character outside the level's lists (a name, a rare word)
    chars = known_chars(version, level) | set(known)
    unknown = {ch for ch in BLANK.sub(r"\1", zh) if "\u4e00" <= ch <= "\u9fff" and ch not in chars}
    if len(unknown) > 1:
        return None
    return {"zh": zh, "answer": answer, "wrong": wrong, "fr": str(raw.get("fr") or "").strip()[:200], "level": level}


def save_generated(
    db: Session, *, user_id: int, version: str, level: int, items: list[dict[str, Any]], model_id: str
) -> list[dict[str, Any]]:
    out = []
    now = datetime.utcnow()
    for item in items:
        row = GeneratedExercise(
            user_id=user_id,
            version=version,
            level=level,
            item_type=ITEM_TYPE,
            payload=json.dumps(item, ensure_ascii=False),
            model_id=model_id[:64],
            created_at=now,
        )
        db.add(row)
        db.flush()
        out.append({**item, "id": f"gen-{row.id}", "generated": True})
    return out


def existing_sentences(db: Session, user_id: int, version: str, level: int, limit: int = 40) -> list[str]:
    pool = sentence_pool(db, user_id, version, level)
    return [BLANK.sub(r"\1", s["zh"]) for s in pool[-limit:]]
