"""Add api_credits to external_api_calls for Tavily reconciliation."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "b7c8d9e0f1a2"
down_revision = "a3b4c5d6e7f8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "external_api_calls",
        sa.Column("api_credits", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("external_api_calls", "api_credits")
