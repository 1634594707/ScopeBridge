"""close requirements that already carry an order snapshot

Revision ID: e2f4a6b8c0d1
Revises: a4c1e7d20b53
Create Date: 2026-11-02 22:00:00.000000

"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op


revision: str = "e2f4a6b8c0d1"
down_revision: str | None = "a4c1e7d20b53"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Legacy paid requirements were written before `CLOSED` was applied at
    # finalization. The snapshot is the receipt; repair the status from it.
    op.execute(
        "UPDATE requirements SET status = 'CLOSED' "
        "WHERE id IN (SELECT requirement_id FROM order_snapshots)"
    )


def downgrade() -> None:
    # Status is a derived fact from the snapshot; there is no pre-migration value
    # to restore safely. Keep the repaired rows.
    pass
