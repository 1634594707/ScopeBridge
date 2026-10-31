"""two-sided accounts: user roles, shared sessions, client-owned requirements

Revision ID: a4c1e7d20b53
Revises: b9318d6cb37a
Create Date: 2026-10-31 12:00:00.000000

"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = 'a4c1e7d20b53'
down_revision: str | None = 'b9318d6cb37a'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Roles: the only existing account at this point in history is the seeded
    # seller, so every current row is the studio account.
    op.add_column(
        'users',
        sa.Column('role', sa.String(length=20), server_default='CLIENT', nullable=False),
    )
    op.execute("UPDATE users SET role = 'SELLER'")

    # One session table for both roles.
    op.rename_table('seller_sessions', 'user_sessions')

    # Briefs belong to the client who created them. Nullable so the legacy seed
    # row can be claimed by the seed's demo client instead of guessed at.
    op.add_column(
        'requirements',
        sa.Column('client_id', sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        'fk_requirements_client_id_users',
        'requirements',
        'users',
        ['client_id'],
        ['id'],
        ondelete='RESTRICT',
    )

    # Portal tokens no longer authorise anything; the session is the identity.
    op.drop_index('ix_requirements_portal_token_hash', table_name='requirements')
    op.drop_column('requirements', 'portal_token_hash')


def downgrade() -> None:
    op.add_column(
        'requirements',
        sa.Column('portal_token_hash', sa.String(length=64), nullable=False),
    )
    op.create_index(
        'ix_requirements_portal_token_hash',
        'requirements',
        ['portal_token_hash'],
        unique=True,
    )
    op.drop_constraint('fk_requirements_client_id_users', 'requirements', type_='foreignkey')
    op.drop_column('requirements', 'client_id')
    op.rename_table('user_sessions', 'seller_sessions')
    op.drop_column('users', 'role')
