"""Build data/grammar/points.json: official grammar points + French explanations.

    python scripts/build_grammar.py [--check]

- data/grammar/official.csv: the official list (语法等级大纲, levels 1-3: 48 + 81 + 81
  points), from 《国际中文教育中文水平等级标准》 as transcribed by
  github.com/shawkynasr/HSK-official-Query-System (MIT).
- data/grammar/src/l{1,2,3}.yaml: for each official number, the French title,
  explanation, pattern, examples and quiz written for this app.
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import sys
from pathlib import Path

import yaml

BACKEND = Path(__file__).resolve().parents[1]
GRAMMAR = BACKEND / "data" / "grammar"
LEVEL_CN = {1: "一", 2: "二", 3: "三"}


def build(check_only: bool) -> int:
    official = list(csv.DictReader(open(GRAMMAR / "official.csv", encoding="utf-8")))
    first_no = {lv: min(int(r["no"]) for r in official if int(r["level"]) == lv) for lv in (1, 2, 3)}
    content: dict[int, dict] = {}
    for path in sorted((GRAMMAR / "src").glob("l*.yaml")):
        content.update({int(k): v for k, v in (yaml.safe_load(path.read_text(encoding="utf-8")) or {}).items()})

    problems, points, missing = 0, [], []
    for row in official:
        no, level = int(row["no"]), int(row["level"])
        code = no - first_no[level] + 1
        src = content.get(no)
        if not src:
            missing.append(no)
            continue
        examples = [{"zh": e[0], "fr": e[1]} for e in src.get("examples", [])]
        quiz = []
        for q in src.get("quiz", []):
            options = q.get("options", [])
            answer = "ABC".find(str(q.get("answer", "A")).upper()[:1])  # default: first option
            if len(options) != 3 or answer < 0 or len(set(options)) != 3:
                print(f"✗ point {no}: question mal formée ({q.get('q')})")
                problems += 1
                continue
            # Shuffle the options (seeded): the right answer is written first in the sources.
            order = [0, 1, 2]
            random.Random(f"{no}-{len(quiz)}").shuffle(order)
            quiz.append(
                {
                    "q": q["q"],
                    "options": [options[i] for i in order],
                    "answer": order.index(answer),
                    "why": q.get("why", ""),
                }
            )
        for field in ("title", "explanation"):
            if not src.get(field):
                print(f"✗ point {no}: « {field} » manquant")
                problems += 1
        if len(examples) < 2 or not quiz:
            print(f"✗ point {no}: il faut au moins 2 exemples et 1 question")
            problems += 1
        points.append(
            {
                "id": f"{level}-{code:02d}",
                "code": f"{LEVEL_CN[level]}{code:02d}",
                "level": level,
                "no": no,
                "item": row["item"],
                "category": row["category"],
                "detail": row["detail"],
                "content": row["content"],
                "title": src.get("title", ""),
                "explanation": src.get("explanation", "").strip(),
                "pattern": src.get("pattern", "").strip(),
                "examples": examples,
                "quiz": quiz,
            }
        )
    if missing:
        print(f"⚠ {len(missing)} point(s) sans contenu : {missing[:20]}{'…' if len(missing) > 20 else ''}")
    print(f"{len(points)} points, {problems} problème(s)")
    if not check_only:
        (GRAMMAR / "points.json").write_text(
            json.dumps({"points": points}, ensure_ascii=False, indent=1), encoding="utf-8"
        )
    return 1 if problems else 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    sys.exit(build(parser.parse_args().check))
