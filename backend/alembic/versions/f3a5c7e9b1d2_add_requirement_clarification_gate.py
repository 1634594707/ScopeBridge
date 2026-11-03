"""add requirement clarification gate

Revision ID: f3a5c7e9b1d2
Revises: e2f4a6b8c0d1
Create Date: 2026-11-02 23:30:00.000000

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f3a5c7e9b1d2"
down_revision: str | None = "e2f4a6b8c0d1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "requirement_clarifications",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("requirement_id", sa.Uuid(), nullable=False),
        sa.Column("source_revision", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(length=10), nullable=False),
        sa.Column("status", sa.String(length=12), nullable=False),
        sa.Column("extraction_id", sa.Uuid(), nullable=True),
        sa.Column("questions", sa.JSON(), nullable=False),
        sa.Column("unsupported_requests", sa.JSON(), nullable=False),
        sa.Column("answers", sa.Text(), nullable=False),
        sa.Column("acknowledged", sa.Boolean(), nullable=False),
        sa.Column("acknowledged_unsupported", sa.Boolean(), nullable=False),
        sa.Column("reason_code", sa.String(length=60), nullable=True),
        sa.Column("note", sa.Text(), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("confirmed_by", sa.Uuid(), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["requirement_id"], ["requirements.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["extraction_id"], ["ai_extractions.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["confirmed_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_requirement_clarifications_requirement_id"),
        "requirement_clarifications",
        ["requirement_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_requirement_clarifications_status"),
        "requirement_clarifications",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_clarifications_requirement_revision",
        "requirement_clarifications",
        ["requirement_id", "source_revision"],
        unique=False,
    )
    op.add_column(
        "quote_versions",
        sa.Column("clarification_id", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        "fk_quote_versions_clarification_id",
        "quote_versions",
        "requirement_clarifications",
        ["clarification_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_quote_versions_clarification_id", "quote_versions", type_="foreignkey"
    )
    op.drop_column("quote_versions", "clarification_id")
    op.drop_index(
        "ix_clarifications_requirement_revision",
        table_name="requirement_clarifications",
    )
    op.drop_index(
        op.f("ix_requirement_clarifications_status"),
        table_name="requirement_clarifications",
    )
    op.drop_index(
        op.f("ix_requirement_clarifications_requirement_id"),
        table_name="requirement_clarifications",
    )
    op.drop_table("requirement_clarifications")
