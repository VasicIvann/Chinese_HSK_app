"""Build data/classifiers/classifiers.json from the reviewed sources in data/classifiers/src.

    python scripts/build_classifiers.py            # build + report
    python scripts/build_classifiers.py --check    # report only, exit 1 on problems

For every classifier it validates the fiche, and for every fill-in sentence it:
1. checks the blank holds the classifier and the wrong options are other classifiers;
2. finds, for each version (2.0 / 3.0), the lowest level whose word lists cover the
   sentence (same check as the exercise bank) and where the answer and at least
   three wrong options are known — or marks the sentence unavailable in that version.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

import yaml

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND / "scripts"))
sys.path.insert(0, str(BACKEND))

from build_exercises import oov  # noqa: E402

DATA = BACKEND / "data" / "classifiers"
SRC = DATA / "src"
OUT = DATA / "classifiers.json"
VERSIONS = ("3.0", "2.0")
LEVELS = (1, 2, 3)
KINDS = {"nominal", "verbal", "both"}
BLANK = re.compile(r"\{([^{}]+)\}")
# Place names used in the sentences (the papers use them freely).
PROPER = {"北京", "上海", "中国"}


def min_level(text: str, version: str, extra: set[str], floor: int = 1) -> int | None:
    for level in LEVELS:
        if level >= floor and not oov([text], version, level, extra):
            return level
    return None


def parse_sentence(line: str) -> dict:
    fields = [f.strip() for f in line.split("|")]
    if len(fields) < 3:
        raise ValueError("il faut « phrase | distracteurs | traduction »")
    zh, wrong, fr, *opts = fields
    out = {"zh": zh, "wrong": wrong.split(), "fr": fr, "lv": 1, "extra": set()}
    for opt in opts:
        key, _, value = opt.partition("=")
        if key == "lv":
            out["lv"] = int(value)
        elif key == "extra":
            out["extra"] = {w for w in value.split(",") if w}
        else:
            raise ValueError(f"option inconnue : {opt}")
    return out


def build(check_only: bool) -> int:
    sources = []
    for path in sorted(SRC.glob("l*.yaml")):
        file_level = int(re.match(r"l(\d)", path.stem).group(1))
        for raw in yaml.safe_load(path.read_text(encoding="utf-8")) or []:
            sources.append((path.name, file_level, raw))

    problems = 0
    levels = {raw["hanzi"]: {v: raw.get("level", {}).get(v) for v in VERSIONS} for _, _, raw in sources}
    warnings: Counter = Counter()
    classifiers = []
    for fname, file_level, raw in sources:
        hz = raw["hanzi"]
        lv = levels[hz]
        where = f"{fname} {hz}"
        if lv["3.0"] != file_level:
            print(f"✗ {where}: niveau 3.0 {lv['3.0']} ≠ fichier {file_level}")
            problems += 1
        for v in VERSIONS:
            if lv[v] is not None and lv[v] not in LEVELS:
                print(f"✗ {where}: niveau {v} invalide ({lv[v]})")
                problems += 1
        if raw.get("kind") not in KINDS:
            print(f"✗ {where}: kind doit être {sorted(KINDS)}")
            problems += 1
        for field in ("pinyin", "usage", "explanation"):
            if not str(raw.get(field) or "").strip():
                print(f"✗ {where}: « {field} » manquant")
                problems += 1

        nouns = []
        for entry in raw.get("nouns") or []:
            zh, fr, *rest = (entry.split("|") + [""])[:3]
            also = rest[0].split() if rest and rest[0] else []
            if not zh or not fr or any(a not in levels for a in also):
                print(f"✗ {where}: nom mal formé « {entry} »")
                problems += 1
                continue
            noun_levels = {v: min_level(zh, v, set()) for v in VERSIONS}
            # `also`: other classifiers that are correct with this noun (never offered as wrong options)
            nouns.append({"zh": zh, "fr": fr, "also": also, "levels": noun_levels})

        examples = []
        for zh, fr in raw.get("examples") or []:
            examples.append({"zh": zh, "fr": fr})
            if min_level(zh, "3.0", PROPER | {hz}) is None:
                warnings[f"exemple hors HSK 1-3 (3.0) : {zh}"] += 1
        if not examples:
            print(f"✗ {where}: aucun exemple")
            problems += 1

        sentences = []
        for n, line in enumerate(raw.get("sentences") or [], start=1):
            sid = f"{hz}-{n:02d}"
            try:
                s = parse_sentence(line)
            except ValueError as exc:
                print(f"✗ {where} phrase {n}: {exc}")
                problems += 1
                continue
            blanks = BLANK.findall(s["zh"])
            if blanks != [hz]:
                print(f"✗ {sid}: le trou doit contenir {hz} (trouvé {blanks})")
                problems += 1
                continue
            bad = [w for w in s["wrong"] if w not in levels or w == hz]
            if bad or len(set(s["wrong"])) != len(s["wrong"]) or len(s["wrong"]) < 3:
                print(f"✗ {sid}: distracteurs invalides {s['wrong']}")
                problems += 1
                continue
            plain = BLANK.sub(r"\1", s["zh"])
            sentence_levels = {}
            for v in VERSIONS:
                if lv[v] is None:
                    sentence_levels[v] = None
                    continue
                # the classifier itself is known from its level on (syllabus lists it)
                known = s["extra"] | PROPER | {hz}
                level = min_level(plain, v, known, floor=max(lv[v], s["lv"]))
                # at least three wrong options the learner of that level knows
                while level is not None and sum(1 for w in s["wrong"] if (levels[w][v] or 9) <= level) < 3:
                    level = level + 1 if level < 3 else None
                sentence_levels[v] = level
            if all(x is None for x in sentence_levels.values()):
                missing = oov([plain], "3.0", 3, s["extra"] | PROPER | {hz})
                print(f"✗ {sid}: utilisable dans aucune version (hors liste 3.0 : {missing})")
                problems += 1
                continue
            if sentence_levels["3.0"] is None:
                warnings[f"{sid} absente en 3.0 : {oov([plain], '3.0', 3, s['extra'] | PROPER | {hz})}"] += 1
            sentences.append(
                {"id": sid, "zh": s["zh"], "answer": hz, "wrong": s["wrong"], "fr": s["fr"], "levels": sentence_levels}
            )
        if len(sentences) < 2:
            print(f"✗ {where}: il faut au moins 2 phrases utilisables")
            problems += 1

        classifiers.append(
            {
                "hanzi": hz,
                "pinyin": raw["pinyin"],
                "kind": raw["kind"],
                "levels": lv,
                "usage": raw["usage"].strip(),
                "explanation": raw["explanation"].strip(),
                "traps": (raw.get("traps") or "").strip(),
                "nouns": nouns,
                "examples": examples,
                "sentences": sentences,
            }
        )

    print("\nPar version et niveau (cumulé) : classificateurs / phrases")
    for v in VERSIONS:
        for level in LEVELS:
            n_cl = sum(1 for c in classifiers if (c["levels"][v] or 9) <= level)
            n_s = sum(1 for c in classifiers for s in c["sentences"] if (s["levels"][v] or 9) <= level)
            print(f"  HSK {v} niveau {level} : {n_cl:2} classificateurs, {n_s:3} phrases")
    by_level: Counter = Counter()
    for c in classifiers:
        for s in c["sentences"]:
            if s["levels"]["3.0"] and s["levels"]["3.0"] > c["levels"]["3.0"]:
                plain = BLANK.sub(r"\1", s["zh"])
                why = oov([plain], "3.0", s["levels"]["3.0"] - 1, PROPER | {c["hanzi"]})
                by_level[f"{s['id']} N{c['levels']['3.0']}→N{s['levels']['3.0']} {plain} {why or '(distracteurs)'}"] += 1
    if by_level:
        print("\nPhrases relevées à un niveau supérieur (vocabulaire ou distracteurs) :")
        for k, n in sorted(by_level.items()):
            print(f"  · {k} ×{n}")
    if warnings:
        print("\nAvertissements :")
        for w in sorted(warnings):
            print(f"  · {w}")
    print(f"\n{len(classifiers)} classificateurs, {sum(len(c['sentences']) for c in classifiers)} phrases, {problems} problème(s)")
    if not check_only:
        OUT.write_text(json.dumps({"classifiers": classifiers}, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"→ {OUT.relative_to(BACKEND)}")
    return 1 if problems else 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    sys.exit(build(parser.parse_args().check))
