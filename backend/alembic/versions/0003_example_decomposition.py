"""Add word_examples.decomposition: components / per-character meaning of the word.

Existing rows get an empty string. Idempotent: skips when the column exists.

Revision ID: 0003_example_decomposition
Revises: 0002_word_examples
Create Date: 2026-10-16

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision: str = "0003_example_decomposition"
down_revision = "0002_word_examples"
branch_labels = None
depends_on = None


def upgrade() -> None:
    columns = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("word_examples")}
    if "decomposition" in columns:
        return
    op.add_column(
        "word_examples",
        sa.Column("decomposition", sa.Text(), nullable=False, server_default=""),
    )


def downgrade() -> None:
    op.drop_column("word_examples", "decomposition")
