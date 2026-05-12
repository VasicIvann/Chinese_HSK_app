"""Baseline schema: mirrors the tables already created by the Streamlit app.

When applied to a fresh DB, this migration creates every table from scratch.
When applied to an existing Neon DB (with tables already populated by Streamlit),
run `alembic stamp head` instead so this migration is recorded as applied
without re-running CREATE TABLE statements.

Revision ID: 0001_baseline
Revises:
Create Date: 2026-05-12

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision: str = "0001_baseline"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "quizzes",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("key", sa.String(length=50), nullable=False, unique=True),
        sa.Column("title", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("level", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )

    op.create_table(
        "entries",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "quiz_id",
            sa.Integer(),
            sa.ForeignKey("quizzes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("hanzi", sa.String(length=32), nullable=False),
        sa.Column("pinyin", sa.String(length=64), nullable=False),
        sa.Column("translation", sa.String(length=255), nullable=False),
        sa.Column("alt_translations", sa.Text(), nullable=True),
        sa.Column("tags", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("email", sa.String(length=255), nullable=False, unique=True, index=True),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("locale", sa.String(length=10), nullable=False, server_default="fr"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )

    op.create_table(
        "user_settings",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("key", sa.String(length=100), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("user_id", "key", name="uq_user_setting"),
    )

    op.create_table(
        "user_vocab_mastery",
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
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("confidence_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("review_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("last_seen_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("fsrs_state", sa.Integer(), nullable=True),
        sa.Column("fsrs_step", sa.Integer(), nullable=True),
        sa.Column("fsrs_stability", sa.Float(), nullable=True),
        sa.Column("fsrs_difficulty", sa.Float(), nullable=True),
        sa.Column("fsrs_due_at", sa.DateTime(), nullable=True, index=True),
        sa.Column("fsrs_last_review_at", sa.DateTime(), nullable=True),
        sa.Column("fsrs_last_rating", sa.Integer(), nullable=True),
        sa.UniqueConstraint("user_id", "entry_id", name="uq_user_entry_mastery"),
    )

    op.create_table(
        "expression_attempts",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("hsk_level", sa.Integer(), nullable=False),
        sa.Column("subject", sa.Text(), nullable=False),
        sa.Column("user_text", sa.Text(), nullable=False),
        sa.Column("correction_json", sa.Text(), nullable=False),
        sa.Column("score", sa.Integer(), nullable=True),
        sa.Column("tokens_input", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("tokens_output", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("model_id", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(), nullable=False, index=True),
    )

    op.create_table(
        "user_daily_usage",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("usage_date", sa.Date(), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("tokens_input", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("tokens_output", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("user_id", "usage_date", "kind", name="uq_user_daily_usage"),
    )


def downgrade() -> None:
    op.drop_table("user_daily_usage")
    op.drop_table("expression_attempts")
    op.drop_table("user_vocab_mastery")
    op.drop_table("user_settings")
    op.drop_table("users")
    op.drop_table("entries")
    op.drop_table("quizzes")
