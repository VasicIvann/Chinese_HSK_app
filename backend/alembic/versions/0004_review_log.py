"""Add review_log: one row per quiz answer (full review history).

Idempotent: skips the CREATE when the table already exists.

Revision ID: 0004_review_log
Revises: 0003_example_decomposition
Create Date: 2026-10-18

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision: str = "0004_review_log"
down_revision = "0003_example_decomposition"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if sa.inspect(op.get_bind()).has_table("review_log"):
        return
    op.create_table(
        "review_log",
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
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("was_new", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("was_due", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("mode", sa.String(length=32), nullable=True),
        sa.Column("elapsed_ms", sa.Integer(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(), nullable=False),
    )
    op.create_index(
        "ix_review_log_user_reviewed_at", "review_log", ["user_id", "reviewed_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_review_log_user_reviewed_at", table_name="review_log")
    op.drop_table("review_log")
