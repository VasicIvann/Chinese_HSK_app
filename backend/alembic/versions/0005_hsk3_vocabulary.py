"""Switch the vocabulary to the HSK 3.0 syllabus (levels 1–5) without losing progress.

Source of truth: backend/data/hsk3/hsk{1..5}.csv (see the README there).

What it does, idempotently:
1. Ensures quizzes HSK1..HSK5 exist (creates HSK4/HSK5, refreshes titles).
2. For every word of the new lists, reuses an existing entry with the same hanzi
   and pinyin (then, as a fallback, the same hanzi when that is unambiguous) and
   moves it to its new level: the entry id is kept, so the user's FSRS history,
   review log and saved examples stay attached to the word.
3. Inserts the words that did not exist yet.
4. Deactivates (never deletes) old entries that are not in the new lists, so
   their history is kept but they no longer appear in quizzes or stats.

Running it again changes nothing.

Revision ID: 0005_hsk3_vocabulary
Revises: 0004_review_log
Create Date: 2026-10-19

"""

from __future__ import annotations

import csv
import unicodedata
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import sqlalchemy as sa
from alembic import op


revision: str = "0005_hsk3_vocabulary"
down_revision = "0004_review_log"
branch_labels = None
depends_on = None

DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "hsk3"
LEVELS = (1, 2, 3, 4, 5)
SOURCE_TAG = "hsk3.0-2025"

# Old HSK 2.0 words that the new syllabus lists under another form of the same
# word (erhua, full form): the progress moves to the new form instead of being hidden.
ALIASES = {  # new form -> old form
    "面条儿": "面条",
    "聊天儿": "聊天",
    "大熊猫": "熊猫",
    "相机": "照相机",
    "公交车": "公共汽车",
    "冬天": "冬",
    "夏天": "夏",
    "秋天": "秋",
    "绿色": "绿",
}

quizzes = sa.table(
    "quizzes",
    sa.column("id", sa.Integer),
    sa.column("key", sa.String),
    sa.column("title", sa.String),
    sa.column("description", sa.Text),
    sa.column("level", sa.Integer),
    sa.column("created_at", sa.DateTime),
    sa.column("updated_at", sa.DateTime),
)
entries = sa.table(
    "entries",
    sa.column("id", sa.Integer),
    sa.column("quiz_id", sa.Integer),
    sa.column("hanzi", sa.String),
    sa.column("pinyin", sa.String),
    sa.column("translation", sa.String),
    sa.column("alt_translations", sa.Text),
    sa.column("tags", sa.String),
    sa.column("is_active", sa.Boolean),
    sa.column("created_at", sa.DateTime),
)


def _norm_pinyin(p: str) -> str:
    return unicodedata.normalize("NFC", (p or "").lower()).replace(" ", "").replace("'", "").replace("’", "")


def load_words(data_dir: Path = DATA_DIR) -> list[dict]:
    words = []
    for level in LEVELS:
        with open(data_dir / f"hsk{level}.csv", encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                words.append(
                    {
                        "level": level,
                        "hanzi": row["hanzi"].strip(),
                        "pinyin": row["pinyin"].strip(),
                        "translation": row["translation"].strip()[:255],
                        "alt_translations": (row.get("alt_translations") or "").strip() or None,
                        "tags": ",".join(t for t in (SOURCE_TAG, row.get("part_of_speech", "").strip()) if t)[:255],
                    }
                )
    return words


def sync_vocabulary(conn, words: list[dict]) -> dict[str, int]:
    now = datetime.utcnow()
    stats = {"moved_or_updated": 0, "inserted": 0, "deactivated": 0}

    # 1. Quizzes
    quiz_ids: dict[int, int] = {}
    existing = {row.key: row.id for row in conn.execute(sa.select(quizzes.c.id, quizzes.c.key))}
    counts = defaultdict(int)
    for w in words:
        counts[w["level"]] += 1
    for level in LEVELS:
        key = f"HSK{level}"
        values = {
            "title": f"HSK {level}",
            "description": f"HSK 3.0 — niveau {level} ({counts[level]} nouveaux mots)",
            "level": level,
            "updated_at": now,
        }
        if key in existing:
            conn.execute(sa.update(quizzes).where(quizzes.c.id == existing[key]).values(**values))
            quiz_ids[level] = existing[key]
        else:
            conn.execute(sa.insert(quizzes).values(key=key, created_at=now, **values))
            quiz_ids[level] = conn.execute(
                sa.select(quizzes.c.id).where(quizzes.c.key == key)
            ).scalar_one()

    # 2. Match new words to existing entries
    old_rows = list(conn.execute(sa.select(entries.c.id, entries.c.quiz_id, entries.c.hanzi, entries.c.pinyin)))
    by_key: dict[tuple[str, str], list] = defaultdict(list)
    by_hanzi: dict[str, list] = defaultdict(list)
    for row in sorted(old_rows, key=lambda r: r.id):
        by_key[(row.hanzi, _norm_pinyin(row.pinyin))].append(row)
        by_hanzi[row.hanzi].append(row)
    used: set[int] = set()

    def take(candidates: list, quiz_id: int):
        free = [r for r in candidates if r.id not in used]
        if not free:
            return None
        # Prefer an entry already in the target level (keeps re-runs stable).
        free.sort(key=lambda r: (r.quiz_id != quiz_id, r.id))
        used.add(free[0].id)
        return free[0]

    matches: list[tuple[dict, object]] = []
    unmatched: list[dict] = []
    for w in words:
        row = take(by_key[(w["hanzi"], _norm_pinyin(w["pinyin"]))], quiz_ids[w["level"]])
        (matches.append((w, row)) if row else unmatched.append(w))

    # Fallback: same hanzi, different pinyin spelling (tone sandhi, spacing) — only
    # when exactly one candidate is left, to avoid mixing two senses of a homograph.
    still_new: list[dict] = []
    for w in unmatched:
        free = [r for r in by_hanzi[w["hanzi"]] if r.id not in used]
        pending_same_hanzi = sum(1 for x in unmatched if x["hanzi"] == w["hanzi"])
        alias = [r for r in by_hanzi.get(ALIASES.get(w["hanzi"], ""), []) if r.id not in used]
        if len(free) == 1 and pending_same_hanzi == 1:
            used.add(free[0].id)
            matches.append((w, free[0]))
        elif not free and len(alias) == 1:
            used.add(alias[0].id)
            matches.append((w, alias[0]))
        else:
            still_new.append(w)

    # One batched statement (executemany): the database may be far from the app server.
    if matches:
        conn.execute(
            sa.update(entries)
            .where(entries.c.id == sa.bindparam("b_id"))
            .values(
                quiz_id=sa.bindparam("b_quiz_id"),
                hanzi=sa.bindparam("b_hanzi"),
                pinyin=sa.bindparam("b_pinyin"),
                translation=sa.bindparam("b_translation"),
                alt_translations=sa.bindparam("b_alt"),
                tags=sa.bindparam("b_tags"),
                is_active=True,
            ),
            [
                {
                    "b_id": row.id,
                    "b_quiz_id": quiz_ids[w["level"]],
                    "b_hanzi": w["hanzi"],
                    "b_pinyin": w["pinyin"],
                    "b_translation": w["translation"],
                    "b_alt": w["alt_translations"],
                    "b_tags": w["tags"],
                }
                for w, row in matches
            ],
        )
        stats["moved_or_updated"] = len(matches)

    # 3. New words
    if still_new:
        conn.execute(
            sa.insert(entries),
            [
                {
                    "quiz_id": quiz_ids[w["level"]],
                    "hanzi": w["hanzi"],
                    "pinyin": w["pinyin"],
                    "translation": w["translation"],
                    "alt_translations": w["alt_translations"],
                    "tags": w["tags"],
                    "is_active": True,
                    "created_at": now,
                }
                for w in still_new
            ],
        )
        stats["inserted"] = len(still_new)

    # 4. Old words that are not in the new syllabus: keep, but hide.
    leftover = [r.id for r in old_rows if r.id not in used]
    if leftover:
        conn.execute(sa.update(entries).where(entries.c.id.in_(leftover)).values(is_active=False))
        stats["deactivated"] = len(leftover)
    return stats


def upgrade() -> None:
    stats = sync_vocabulary(op.get_bind(), load_words())
    print(f"[0005_hsk3_vocabulary] {stats}")


def downgrade() -> None:
    # Data migration: the previous word lists are not restored automatically.
    # Entries keep their ids; re-import backend/data/legacy-hsk2.0 by hand if needed.
    pass
