"""Add word_drawings: handwriting-practice drawings (PNG) per user and entry.

Idempotent: skips the CREATE when the table already exists.

Revision ID: 0006_word_drawings
Revises: 0005_hsk3_vocabulary
Create Date: 2026-10-19

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision: str = "0006_word_drawings"
down_revision = "0005_hsk3_vocabulary"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if sa.inspect(op.get_bind()).has_table("word_drawings"):
        return
    op.create_table(
        "word_drawings",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("entry_id", sa.Integer(), sa.ForeignKey("entries.id", ondelete="CASCADE"), nullable=False),
        sa.Column("image_png", sa.LargeBinary(), nullable=False),
        sa.Column("width", sa.Integer(), nullable=False),
        sa.Column("height", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_word_drawings_user_entry", "word_drawings", ["user_id", "entry_id"])
    op.create_index("ix_word_drawings_user_created", "word_drawings", ["user_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_word_drawings_user_created", table_name="word_drawings")
    op.drop_index("ix_word_drawings_user_entry", table_name="word_drawings")
    op.drop_table("word_drawings")
