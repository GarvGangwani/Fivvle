"""Add archived_at to coupons for soft-delete."""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f2a3b4c5d6e7"
down_revision: str | None = "e1f2a3b4c5d6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "coupons",
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_coupons_archived_at", "coupons", ["archived_at"])


def downgrade() -> None:
    op.drop_index("ix_coupons_archived_at", table_name="coupons")
    op.drop_column("coupons", "archived_at")
