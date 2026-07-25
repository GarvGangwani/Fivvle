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

Idempotent: skips add/drop when columns already exist (local DBs that applied
this DDL while stamped at an earlier head).
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "i5j6k7l8m9n0"
down_revision: Union[str, Sequence[str], None] = "c5d6e7f8a9b0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    cols = {c["name"] for c in insp.get_columns("experiments")}
    for name, col in (
        (
            "founder_decision",
            sa.Column("founder_decision", sa.String(length=20), nullable=True),
        ),
        (
            "founder_decision_at",
            sa.Column(
                "founder_decision_at",
                sa.DateTime(timezone=True),
                nullable=True,
            ),
        ),
        (
            "founder_decision_note",
            sa.Column("founder_decision_note", sa.String(length=500), nullable=True),
        ),
        (
            "founder_decision_version",
            sa.Column("founder_decision_version", sa.Integer(), nullable=True),
        ),
    ):
        if name not in cols:
            op.add_column("experiments", col)


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    cols = {c["name"] for c in insp.get_columns("experiments")}
    for name in (
        "founder_decision_version",
        "founder_decision_note",
        "founder_decision_at",
        "founder_decision",
    ):
        if name in cols:
            op.drop_column("experiments", name)
