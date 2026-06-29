"""waitlist signup geo fields

Revision ID: e4b7c2a1f9d3
Revises: d8f1a2b3c4e5
Create Date: 2026-06-17 12:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e4b7c2a1f9d3"
down_revision: str | None = "d8f1a2b3c4e5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "waitlist_signups",
        sa.Column("ip_address", sa.String(length=45), nullable=True),
    )
    op.add_column(
        "waitlist_signups",
        sa.Column("geo_city", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "waitlist_signups",
        sa.Column("geo_region", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "waitlist_signups",
        sa.Column("geo_country", sa.String(length=100), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("waitlist_signups", "geo_country")
    op.drop_column("waitlist_signups", "geo_region")
    op.drop_column("waitlist_signups", "geo_city")
    op.drop_column("waitlist_signups", "ip_address")
