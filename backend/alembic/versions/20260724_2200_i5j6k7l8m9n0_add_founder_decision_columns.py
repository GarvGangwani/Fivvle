"""add founder_decision columns on experiments

Revision ID: i5j6k7l8m9n0
Revises: c5d6e7f8a9b0
Create Date: 2026-07-24 22:00:00.000000

Persists the founder's Signal decision separately from /archive.

Columns (all nullable — no decision is a valid state):

- founder_decision         VARCHAR(20)  proceed|iterate|pivot|kill
- founder_decision_at      TIMESTAMPTZ  set on write via clock_timestamp()
- founder_decision_note    VARCHAR(500) optional rationale (matches why_now)
- founder_decision_version INTEGER      CAS version; NULL until first write

Does not change archive behavior or experiment.status.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "i5j6k7l8m9n0"
down_revision: Union[str, Sequence[str], None] = "c5d6e7f8a9b0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "experiments",
        sa.Column("founder_decision", sa.String(length=20), nullable=True),
    )
    op.add_column(
        "experiments",
        sa.Column(
            "founder_decision_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        "experiments",
        sa.Column("founder_decision_note", sa.String(length=500), nullable=True),
    )
    op.add_column(
        "experiments",
        sa.Column("founder_decision_version", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("experiments", "founder_decision_version")
    op.drop_column("experiments", "founder_decision_note")
    op.drop_column("experiments", "founder_decision_at")
    op.drop_column("experiments", "founder_decision")
