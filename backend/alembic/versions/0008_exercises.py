"""Add exercise_results and generated_exercises (HSK-format listening / writing / grammar).

Idempotent: skips the tables that already exist.

Revision ID: 0008_exercises
Revises: 0007_hsk_versions
Create Date: 2026-10-19

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision: str = "0008_exercises"
down_revision = "0007_hsk_versions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("exercise_results"):
        op.create_table(
            "exercise_results",
            sa.Column("id", sa.Integer(), primary_key=True, index=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("version", sa.String(length=8), nullable=False),
            sa.Column("level", sa.Integer(), nullable=False),
            sa.Column("section", sa.String(length=16), nullable=False),
            sa.Column("part_key", sa.String(length=32), nullable=False),
            sa.Column("score", sa.Integer(), nullable=False),
            sa.Column("total", sa.Integer(), nullable=False),
            sa.Column("details", sa.Text(), nullable=False, server_default="[]"),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )
        op.create_index(
            "ix_exercise_results_user_part", "exercise_results", ["user_id", "section", "level", "part_key"]
        )
    if not inspector.has_table("generated_exercises"):
        op.create_table(
            "generated_exercises",
            sa.Column("id", sa.Integer(), primary_key=True, index=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("version", sa.String(length=8), nullable=False),
            sa.Column("level", sa.Integer(), nullable=False),
            sa.Column("item_type", sa.String(length=32), nullable=False),
            sa.Column("payload", sa.Text(), nullable=False),
            sa.Column("model_id", sa.String(length=64), nullable=False, server_default=""),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )
        op.create_index(
            "ix_generated_exercises_user_level_type", "generated_exercises", ["user_id", "level", "item_type"]
        )


def downgrade() -> None:
    op.drop_index("ix_generated_exercises_user_level_type", table_name="generated_exercises")
    op.drop_table("generated_exercises")
    op.drop_index("ix_exercise_results_user_part", table_name="exercise_results")
    op.drop_table("exercise_results")
