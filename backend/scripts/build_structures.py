"""Build data/exercises/structures.json from data/exercises/src/structures.yaml.

    python scripts/build_structures.py          # build + report
    python scripts/build_structures.py --check  # report only, exit 1 on problems

Checks: unique ids, official grammar point of level 2 or 3, every fixed part of the
structure appears in its example, example within the HSK 3.0 levels 1-3 word lists.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import yaml

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND / "scripts"))
sys.path.insert(0, str(BACKEND))

from build_exercises import oov  # noqa: E402

SRC = BACKEND / "data" / "exercises" / "src" / "structures.yaml"
OUT = BACKEND / "data" / "exercises" / "structures.json"
POINTS = BACKEND / "data" / "grammar" / "points.json"
FIELDS = ("id", "code", "structure", "meaning", "pattern", "example")
PROPER = {"北京", "上海", "中国", "烤鸭"}


def fixed_parts(structure: str) -> list[list[str]]:
    """'虽然……，但是／可是……' -> [['虽然'], ['但是', '可是']] (alternatives per slot)."""
    parts = []
    for chunk in re.split(r"……|[，？！。、]", structure):
        options = [o for o in chunk.split("／") if o]
        if options:
            parts.append(options)
    return parts


def build(check_only: bool) -> int:
    points = {p["code"]: p for p in json.loads(POINTS.read_text(encoding="utf-8"))["points"]}
    raw = yaml.safe_load(SRC.read_text(encoding="utf-8"))
    problems, out, seen = 0, [], set()
    for s in raw:
        where = s.get("id", "?")
        missing = [f for f in FIELDS if not s.get(f)]
        if missing:
            print(f"✗ {where}: champs manquants {missing}")
            problems += 1
            continue
        if s["id"] in seen:
            print(f"✗ {where}: id en double")
            problems += 1
        seen.add(s["id"])
        point = points.get(s["code"])
        if point is None or point["level"] not in (2, 3):
            print(f"✗ {where}: point de grammaire {s['code']} introuvable ou hors niveaux 2-3")
            problems += 1
            continue
        zh, fr = s["example"]
        for options in fixed_parts(s["structure"]):
            if not any(o in zh for o in options):
                print(f"✗ {where}: l'exemple « {zh} » n'utilise pas {'／'.join(options)}")
                problems += 1
        # The structure's own words (按照, 首先, 由于…) are what is being learnt.
        own = {o for options in fixed_parts(s["structure"]) for o in options}
        unknown = oov([zh], "3.0", 3, PROPER | own)
        if unknown:
            print(f"· {where}: exemple hors HSK 1-3 : {unknown}")
        out.append(
            {
                "id": s["id"],
                "level": point["level"],
                "code": s["code"],
                "point": point["id"],
                "structure": s["structure"],
                "meaning": s["meaning"],
                "pattern": s["pattern"],
                "example": {"zh": zh, "fr": fr},
            }
        )
    levels = {lv: sum(1 for s in out if s["level"] == lv) for lv in (2, 3)}
    print(f"{len(out)} structures (niveau 2 : {levels[2]}, niveau 3 : {levels[3]}), {problems} problème(s)")
    if not check_only and not problems:
        OUT.write_text(json.dumps({"structures": out}, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"→ {OUT.relative_to(BACKEND)}")
    return 1 if problems else 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    sys.exit(build(parser.parse_args().check))
