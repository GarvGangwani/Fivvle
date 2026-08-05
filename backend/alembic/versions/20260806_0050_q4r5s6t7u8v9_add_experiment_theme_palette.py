"""Add per-experiment canvas palette columns.

Revision ID: q4r5s6t7u8v9
Revises: p3q4r5s6t7u8
Create Date: 2026-08-06 00:50:00.000000

Additive only — no backfill. Existing experiments keep null theme_palette
(platform default purple) and null suggested_palette until their next capture.
The legacy idea_theme column is left in place, unwritten.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "q4r5s6t7u8v9"
down_revision: str | Sequence[str] | None = "p3q4r5s6t7u8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "experiments",
        sa.Column("theme_palette", sa.String(length=40), nullable=True),
    )
    op.add_column(
        "experiments",
        sa.Column("suggested_palette", sa.String(length=40), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("experiments", "suggested_palette")
    op.drop_column("experiments", "theme_palette")
