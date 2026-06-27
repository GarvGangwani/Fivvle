"""Backfill api_credits on historical Tavily external_api_calls rows."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "c1d2e3f4a5b6"
down_revision = "b7c8d9e0f1a2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            UPDATE external_api_calls
            SET api_credits = GREATEST(
                1,
                ROUND(cost_usd / 0.008)::integer
            )
            WHERE provider = 'tavily'
              AND api_credits IS NULL
              AND success = true
              AND cost_usd > 0
            """
        )
    )


def downgrade() -> None:
    pass
