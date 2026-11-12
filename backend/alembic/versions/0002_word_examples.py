"""Add word_examples: Claude-generated example sentences per user and entry.

Idempotent: skips the CREATE when the table already exists, so a re-run on a
database that was patched by hand does not fail the deploy.

Revision ID: 0002_word_examples
Revises: 0001_baseline
Create Date: 2026-10-15

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision: str = "0002_word_examples"
down_revision = "0001_baseline"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if inspector.has_table("word_examples"):
        return

    op.create_table(
        "word_examples",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "entry_id",
            sa.Integer(),
            sa.ForeignKey("entries.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("hsk_level", sa.Integer(), nullable=True),
        sa.Column("sentence", sa.Text(), nullable=False),
        sa.Column("pinyin", sa.Text(), nullable=False, server_default=""),
        sa.Column("translation", sa.Text(), nullable=False, server_default=""),
        sa.Column("meaning_in_sentence", sa.Text(), nullable=False, server_default=""),
        sa.Column("general_meaning", sa.Text(), nullable=False, server_default=""),
        sa.Column("tokens_input", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("tokens_output", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("model_id", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index(
        "ix_word_examples_user_entry", "word_examples", ["user_id", "entry_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_word_examples_user_entry", table_name="word_examples")
    op.drop_table("word_examples")
