"""Add the founder's explicit refine-completion stamp.

Revision ID: r5s6t7u8v9w0
Revises: q4r5s6t7u8v9
Create Date: 2026-08-06 01:40:00.000000

Additive only — no backfill. Existing experiments keep a null
refine_completed_at, so the canvas hides Evidence until the founder taps
"Done refining", including on rows that already have a finalized
refined_idea. Deliberate: completion is an explicit founder action, never
derived from refined_idea presence.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "r5s6t7u8v9w0"
down_revision: str | Sequence[str] | None = "q4r5s6t7u8v9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "experiments",
        sa.Column("refine_completed_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("experiments", "refine_completed_at")
