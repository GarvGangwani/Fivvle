"""Add generation_phase to landing_page_v2_specs for multi-stage runtime pipeline."""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "h4i5j6k7l8m9"
down_revision: str | None = "g3h4i5j6k7l8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "landing_page_v2_specs",
        sa.Column(
            "generation_phase",
            sa.String(length=24),
            nullable=False,
            server_default="idle",
        ),
    )


def downgrade() -> None:
    op.drop_column("landing_page_v2_specs", "generation_phase")
