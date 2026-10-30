"""add payment recovery fields

Revision ID: b9318d6cb37a
Revises: 3c85c4db4f4b
Create Date: 2026-10-30 22:54:09.450488

"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = 'b9318d6cb37a'
down_revision: str | None = '3c85c4db4f4b'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        'payment_attempts',
        sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'),
    )
    op.add_column('payment_attempts', sa.Column('resolved_by', sa.Uuid(), nullable=True))
    op.add_column(
        'payment_attempts',
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column('payment_attempts', sa.Column('resolution_note', sa.Text(), nullable=True))
    op.create_foreign_key(
        'fk_payment_attempts_resolved_by_users',
        'payment_attempts',
        'users',
        ['resolved_by'],
        ['id'],
        ondelete='SET NULL',
    )


def downgrade() -> None:
    op.drop_constraint(
        'fk_payment_attempts_resolved_by_users',
        'payment_attempts',
        type_='foreignkey',
    )
    op.drop_column('payment_attempts', 'resolution_note')
    op.drop_column('payment_attempts', 'resolved_at')
    op.drop_column('payment_attempts', 'resolved_by')
    op.drop_column('payment_attempts', 'retry_count')
