"""Build data/exercises/bank.json from the reviewed sources in data/exercises/src.

    python scripts/build_exercises.py            # build + report
    python scripts/build_exercises.py --check    # report only, exit 1 on problems

For every item it:
1. validates the shape (app.services.exercise_schema.normalize);
2. checks that its Chinese text can be read with the cumulative word lists of each
   version (data/hsk2, data/hsk3) up to the item's level;
3. records `versions`: the versions whose lists cover the item.

Text is covered with listed words and with the characters those words use
(早 from 早上). Characters met in no listed word are reported as out of the level. Proper nouns and other
unavoidable words go in an item's `extra:` list.
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import re
import sys
from collections import Counter, defaultdict
from functools import lru_cache
from pathlib import Path

import yaml

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.services.exercise_schema import InvalidItem, chinese_texts, normalize  # noqa: E402
from app.services.exercise_service import GROUP_TYPES, part_slots  # noqa: E402

DATA = BACKEND / "data"
SRC = DATA / "exercises" / "src"
OUT = DATA / "exercises" / "bank.json"
HAN = re.compile(r"[一-鿿]+")
# Always fine: names used in the official papers, numbers, interjections.
COMMON = set("王李张刘陈杨赵黄周吴小明红丽华") | {"小明", "小红", "小丽", "小王", "小李", "小张", "大卫", "玛丽", "安娜"}


def _clean(word: str) -> list[str]:
    word = re.sub(r"\d+$", "", word.strip())  # homograph digits (都1)
    # "（儿）" variants and slashes: keep every form
    forms = re.split(r"[／/|]", word)
    out = []
    for form in forms:
        out.append(re.sub(r"[（(]儿[）)]", "", form))
        out.append(re.sub(r"[（()）]", "", form))
    return [f for f in out if f]


@lru_cache(maxsize=None)
def allowed(version: str, level: int) -> frozenset[str]:
    folder = "hsk2" if version == "2.0" else "hsk3"
    words: set[str] = set()
    for lv in range(1, level + 1):
        with open(DATA / folder / f"hsk{lv}.csv", encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                for form in _clean(row["hanzi"]):
                    words.add(form)
                    words.update(HAN.findall(form))  # 虽然…但是… → 虽然, 但是
    return frozenset(words)


@lru_cache(maxsize=None)
def known_chars(version: str, level: int) -> frozenset[str]:
    """Characters a learner of this level can read: every character of the listed words."""
    counts: Counter = Counter()
    singles = set()
    for word in allowed(version, level):
        if len(word) == 1:
            singles.add(word)
        for ch in set(word):
            counts[ch] += 1
    # A character met in a listed word is readable on its own (早 from 早上, 考 from 考试):
    # the official papers use them that way. Characters never met are what the check catches.
    return frozenset(singles | set(counts) | set("零一二两三四五六七八九十百千万几"))


def oov(texts: list[str], version: str, level: int, extra: set[str]) -> list[str]:
    """Runs of characters that cannot be read with the level's words and characters."""
    words = allowed(version, level) | extra | COMMON
    chars = known_chars(version, level)
    missing = []
    for text in texts:
        for run in HAN.findall(text):
            n = len(run)
            # best[i] = fewest unknown characters to cover run[:i]; back[i] = start of the last piece
            best = [0] + [n + 1] * n
            back = [0] * (n + 1)
            for i in range(1, n + 1):
                ch = run[i - 1]
                best[i] = best[i - 1] + (0 if ch in chars or ch in words else 1)
                back[i] = i - 1
                for j in range(max(0, i - 6), i - 1):
                    if run[j:i] in words and best[j] < best[i]:
                        best[i], back[i] = best[j], j
            i, unknown = n, []
            while i > 0:
                j = back[i]
                if i - j == 1 and run[j] not in chars and run[j] not in words:
                    unknown.append(j)
                i = j
            # group consecutive unknown characters into one report
            for k in sorted(unknown):
                if missing and missing[-1][1] == k - 1 and missing[-1][2] is run:
                    missing[-1] = (missing[-1][0] + run[k], k, run)
                else:
                    missing.append((run[k], k, run))
    return [m[0] for m in missing]


def shuffle_options(item: dict) -> None:
    """Deterministic shuffle (seeded by the item id), so the right answer is not
    always where it was written."""
    rng = random.Random(item["id"])
    if item["type"] in ("pic_choice", "pic_answer", "short_mcq", "long_mcq", "passage_mcq"):
        order = list(range(len(item["options"])))
        rng.shuffle(order)
        item["options"] = [item["options"][i] for i in order]
        if item.get("options_fr"):
            item["options_fr"] = [item["options_fr"][i] for i in order]
        item["answer"] = order.index(item["answer"])
    elif item["type"] in ("pic_match", "word_match"):
        order = list(range(len(item["options"])))
        rng.shuffle(order)
        item["options"] = [item["options"][i] for i in order]
        for q in item["items"]:
            q["answer"] = order.index(q["answer"])
        rng.shuffle(item["items"])


def build(check_only: bool) -> int:
    from app.services.exercise_service import formats

    # Versions whose papers use each (type, level): an item should fit all of them.
    intended: dict[tuple[str, int], set[str]] = defaultdict(set)
    for version, levels in formats().items():
        for level, sections in levels.items():
            for plist in sections.values():
                for part in plist:
                    for item_type, _ in part_slots(part):
                        intended[(item_type, int(level))].add(version)

    problems = 0
    items = []
    misfits: list[str] = []
    oov_report: dict[str, Counter] = defaultdict(Counter)
    for path in sorted(SRC.glob("l*.yaml")):
        level = int(re.match(r"l(\d)", path.stem).group(1))
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        for item_type, entries in data.items():
            for n, raw in enumerate(entries or [], start=1):
                item_id = f"{level}-{item_type}-{n:03d}"
                try:
                    item = normalize(raw, item_type, level)
                except InvalidItem as exc:
                    print(f"✗ {path.name} {item_id}: {exc}")
                    problems += 1
                    continue
                extra = set(raw.get("extra") or [])
                texts = chinese_texts(item)
                versions = []
                for version in ("2.0", "3.0"):
                    missing = oov(texts, version, level, extra)
                    if missing:
                        oov_report[f"{version} L{level}"].update(missing)
                        if version in intended[(item_type, level)]:
                            misfits.append(f"{item_id} ({version}): {', '.join(sorted(set(missing)))}")
                    else:
                        versions.append(version)
                item["id"] = item_id
                item["versions"] = versions
                shuffle_options(item)
                items.append(item)

    # Coverage: questions available for every part of every paper.
    print("\nQuestions disponibles par partie (besoin : 1 série = nombre de l'examen)")
    for version, levels in formats().items():
        for level, sections in levels.items():
            for section, plist in sections.items():
                for part in plist:
                    for item_type, count in part_slots(part):
                        have = sum(
                            len(i["items"]) if i["type"] in GROUP_TYPES else 1
                            for i in items
                            if i["type"] == item_type and i["level"] == int(level) and version in i["versions"]
                        )
                        flag = "  " if have >= 2 * count else "⚠ "
                        print(f"{flag}{version} HSK{level} {section:9} {part['part']} {item_type:13} {have:3} / {count}")
    print()
    for key, counter in sorted(oov_report.items()):
        print(f"Hors liste {key}: {', '.join(f'{w}×{c}' for w, c in counter.most_common(40))}")
    if misfits:
        print("\nItems hors vocabulaire pour une version qui les utilise :")
        for line in misfits:
            print(f"  · {line}")
    no_version = [i["id"] for i in items if not i["versions"]]
    if no_version:
        print(f"\n✗ Items couverts par aucune version : {', '.join(no_version)}")
        problems += len(no_version)

    counts = Counter(f"L{i['level']} {i['type']}" for i in items)
    print(f"\n{len(items)} items, {problems} problème(s)")
    if not check_only:
        OUT.write_text(
            json.dumps({"counts": dict(sorted(counts.items())), "items": items}, ensure_ascii=False, indent=1),
            encoding="utf-8",
        )
        print(f"→ {OUT.relative_to(BACKEND)}")
    return 1 if problems else 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    sys.exit(build(parser.parse_args().check))
