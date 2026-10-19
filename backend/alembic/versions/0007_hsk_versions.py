"""HSK 2.0 next to HSK 3.0: one word = one entry, listed under a level per version.

Source of the 2.0 lists: backend/data/hsk2/hsk{1..5}.csv (see the README there).

What it does, idempotently:
1. Adds `quizzes.version` ("3.0" for the existing HSK1..HSK5) and the
   `quiz_entries` table (which quiz lists which word).
2. Lists every active word under its current (3.0) quiz.
3. Creates the HSK 2.0 quizzes (keys HSK1-2.0 .. HSK5-2.0) and lists their words:
   a 2.0 word reuses the existing entry with the same hanzi and pinyin (then the
   same hanzi, then a known variant form such as 面条 -> 面条儿), so the user's
   progress, review history, examples and drawings are shared by both versions.
   Old words hidden by 0005 come back when they are in the 2.0 lists; the
   others are inserted.

Running it again changes nothing.

Revision ID: 0007_hsk_versions
Revises: 0006_word_drawings
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


revision: str = "0007_hsk_versions"
down_revision = "0006_word_drawings"
branch_labels = None
depends_on = None

DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "hsk2"
LEVELS = (1, 2, 3, 4, 5)
SOURCE_TAG = "hsk2.0-2012"

# 2.0 form -> form used by the 3.0 lists (same word).
ALIASES = {
    "面条": "面条儿",
    "聊天": "聊天儿",
    "熊猫": "大熊猫",
    "照相机": "相机",
    "公共汽车": "公交车",
    "冬": "冬天",
    "夏": "夏天",
    "秋": "秋天",
    "绿": "绿色",
}

quizzes = sa.table(
    "quizzes",
    sa.column("id", sa.Integer),
    sa.column("key", sa.String),
    sa.column("title", sa.String),
    sa.column("description", sa.Text),
    sa.column("level", sa.Integer),
    sa.column("version", sa.String),
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
quiz_entries = sa.table(
    "quiz_entries",
    sa.column("quiz_id", sa.Integer),
    sa.column("entry_id", sa.Integer),
)


def v2_key(level: int) -> str:
    return f"HSK{level}-2.0"


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
                    }
                )
    return words


def _ensure_schema() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "version" not in {c["name"] for c in inspector.get_columns("quizzes")}:
        op.add_column(
            "quizzes", sa.Column("version", sa.String(length=8), nullable=False, server_default="3.0")
        )
    if not inspector.has_table("quiz_entries"):
        op.create_table(
            "quiz_entries",
            sa.Column(
                "quiz_id", sa.Integer(), sa.ForeignKey("quizzes.id", ondelete="CASCADE"), primary_key=True
            ),
            sa.Column(
                "entry_id", sa.Integer(), sa.ForeignKey("entries.id", ondelete="CASCADE"), primary_key=True
            ),
        )
        op.create_index("ix_quiz_entries_entry", "quiz_entries", ["entry_id"])


def link_v3(conn) -> int:
    """List each active word of a 3.0 quiz under that quiz (its current level)."""
    result = conn.execute(
        sa.text(
            "INSERT INTO quiz_entries (quiz_id, entry_id) "
            "SELECT e.quiz_id, e.id FROM entries e JOIN quizzes q ON q.id = e.quiz_id "
            "WHERE e.is_active = :active AND q.version = '3.0' "
            "AND NOT EXISTS (SELECT 1 FROM quiz_entries qe WHERE qe.quiz_id = e.quiz_id AND qe.entry_id = e.id)"
        ),
        {"active": True},
    )
    return result.rowcount or 0


def sync_v2(conn, words: list[dict]) -> dict[str, int]:
    now = datetime.utcnow()
    stats = {"shared": 0, "revived": 0, "inserted": 0, "links_added": 0, "links_removed": 0}

    # 1. Quizzes
    counts = defaultdict(int)
    for w in words:
        counts[w["level"]] += 1
    existing = {row.key: row.id for row in conn.execute(sa.select(quizzes.c.id, quizzes.c.key))}
    quiz_ids: dict[int, int] = {}
    for level in LEVELS:
        values = {
            "title": f"HSK {level}",
            "description": f"HSK 2.0 — niveau {level} ({counts[level]} nouveaux mots)",
            "level": level,
            "version": "2.0",
            "updated_at": now,
        }
        key = v2_key(level)
        if key in existing:
            conn.execute(sa.update(quizzes).where(quizzes.c.id == existing[key]).values(**values))
            quiz_ids[level] = existing[key]
        else:
            conn.execute(sa.insert(quizzes).values(key=key, created_at=now, **values))
            quiz_ids[level] = conn.execute(sa.select(quizzes.c.id).where(quizzes.c.key == key)).scalar_one()
    v2_quiz_ids = set(quiz_ids.values())

    # 2. Match each 2.0 word to an existing entry
    rows = list(
        conn.execute(sa.select(entries.c.id, entries.c.hanzi, entries.c.pinyin, entries.c.is_active))
    )
    in_v2 = {
        r.entry_id
        for r in conn.execute(
            sa.select(quiz_entries.c.entry_id).where(quiz_entries.c.quiz_id.in_(v2_quiz_ids))
        )
    }
    by_key: dict[tuple[str, str], list] = defaultdict(list)
    by_hanzi: dict[str, list] = defaultdict(list)
    for r in rows:
        by_key[(r.hanzi, _norm_pinyin(r.pinyin))].append(r)
        by_hanzi[r.hanzi].append(r)
    used: set[int] = set()

    def take(candidates: list):
        free = [r for r in candidates if r.id not in used]
        if not free:
            return None
        # Stable re-runs first, then words in use (3.0), then the oldest entry.
        free.sort(key=lambda r: (r.id not in in_v2, not r.is_active, r.id))
        used.add(free[0].id)
        return free[0]

    matches: list[tuple[dict, object]] = []
    unmatched: list[dict] = []
    for w in words:
        row = take(by_key[(w["hanzi"], _norm_pinyin(w["pinyin"]))])
        (matches.append((w, row)) if row else unmatched.append(w))

    new_words: list[dict] = []
    for w in unmatched:
        same_hanzi = [r for r in by_hanzi[w["hanzi"]] if r.id not in used]
        pending = sum(1 for x in unmatched if x["hanzi"] == w["hanzi"])
        row = None
        if same_hanzi and pending == 1:
            row = take(same_hanzi)  # other pinyin spelling or reading of the same word
        elif not same_hanzi and w["hanzi"] in ALIASES:
            row = take(by_hanzi.get(ALIASES[w["hanzi"]], []))
        (matches.append((w, row)) if row else new_words.append(w))

    # Hidden old words come back; their home quiz becomes their 2.0 level, so they
    # are not mistaken for 3.0 words.
    revived = [{"b_id": row.id, "b_quiz_id": quiz_ids[w["level"]]} for w, row in matches if not row.is_active]
    linked: list[tuple[dict, int]] = [(w, row.id) for w, row in matches]
    if revived:
        conn.execute(
            sa.update(entries)
            .where(entries.c.id == sa.bindparam("b_id"))
            .values(is_active=True, quiz_id=sa.bindparam("b_quiz_id")),
            revived,
        )
    stats["revived"] = len(revived)
    stats["shared"] = len(matches) - len(revived)

    # 3. Words that exist in no list yet
    if new_words:
        conn.execute(
            sa.insert(entries),
            [
                {
                    "quiz_id": quiz_ids[w["level"]],
                    "hanzi": w["hanzi"],
                    "pinyin": w["pinyin"],
                    "translation": w["translation"],
                    "alt_translations": w["alt_translations"],
                    "tags": SOURCE_TAG,
                    "is_active": True,
                    "created_at": now,
                }
                for w in new_words
            ],
        )
        ids = {
            (r.quiz_id, r.hanzi, r.pinyin): r.id
            for r in conn.execute(
                sa.select(entries.c.id, entries.c.quiz_id, entries.c.hanzi, entries.c.pinyin).where(
                    entries.c.quiz_id.in_(v2_quiz_ids)
                )
            )
        }
        linked += [(w, ids[(quiz_ids[w["level"]], w["hanzi"], w["pinyin"])]) for w in new_words]
        stats["inserted"] = len(new_words)

    # 4. Membership of the 2.0 quizzes = exactly the lists
    wanted = {(quiz_ids[w["level"]], entry_id) for w, entry_id in linked}
    current = {
        (r.quiz_id, r.entry_id)
        for r in conn.execute(
            sa.select(quiz_entries.c.quiz_id, quiz_entries.c.entry_id).where(
                quiz_entries.c.quiz_id.in_(v2_quiz_ids)
            )
        )
    }
    to_add = sorted(wanted - current)
    to_remove = sorted(current - wanted)
    if to_add:
        conn.execute(sa.insert(quiz_entries), [{"quiz_id": q, "entry_id": e} for q, e in to_add])
    for q, e in to_remove:
        conn.execute(
            sa.delete(quiz_entries).where(quiz_entries.c.quiz_id == q, quiz_entries.c.entry_id == e)
        )
    stats["links_added"], stats["links_removed"] = len(to_add), len(to_remove)
    return stats


def upgrade() -> None:
    _ensure_schema()
    conn = op.get_bind()
    linked = link_v3(conn)
    stats = sync_v2(conn, load_words())
    print(f"[0007_hsk_versions] 3.0 links: {linked}, 2.0: {stats}")


def downgrade() -> None:
    conn = op.get_bind()
    # Never delete a word (that would delete the users' progress on it): words that
    # are not in a 3.0 list are hidden again and re-homed under the 3.0 quiz of the
    # same level, then the 2.0 quizzes are dropped.
    conn.execute(
        sa.text(
            "UPDATE entries SET is_active = :inactive WHERE id NOT IN ("
            "SELECT qe.entry_id FROM quiz_entries qe JOIN quizzes q ON q.id = qe.quiz_id WHERE q.version = '3.0')"
        ),
        {"inactive": False},
    )
    conn.execute(
        sa.text(
            "UPDATE entries SET quiz_id = (SELECT q3.id FROM quizzes q2 JOIN quizzes q3 "
            "ON q3.level = q2.level AND q3.version = '3.0' WHERE q2.id = entries.quiz_id) "
            "WHERE quiz_id IN (SELECT id FROM quizzes WHERE version = '2.0')"
        )
    )
    conn.execute(sa.text("DELETE FROM quizzes WHERE version = '2.0'"))
    op.drop_index("ix_quiz_entries_entry", table_name="quiz_entries")
    op.drop_table("quiz_entries")
    op.drop_column("quizzes", "version")
