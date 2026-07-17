"""add launch_kits

Revision ID: c5d6e7f8a9b0
Revises: b4c5d6e7f8a9
Create Date: 2026-07-18 00:30:00.000000

LaunchKit artifact table (Launch phase, PR 1). Mirrors the ValidationReport
editable-doc pattern:

- id             UUID  PK
- experiment_id  UUID  NOT NULL  FK → experiments.id (ON DELETE CASCADE), UNIQUE
- landing_page_id UUID NOT NULL  FK → landing_pages.id (ON DELETE CASCADE)
- raw_report     JSONB NOT NULL  (immutable assembled LaunchKit payload)
- edited_doc     JSONB NULL      (founder-edited overlay)
- version        INTEGER NOT NULL DEFAULT 1  (optimistic concurrency)
- edited_at      TIMESTAMPTZ NULL
- generated_at   TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()

UNIQUE(experiment_id) enforces the 1:1 relationship with Experiment.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "c5d6e7f8a9b0"
down_revision: Union[str, Sequence[str], None] = "b4c5d6e7f8a9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "launch_kits",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("experiment_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("landing_page_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("raw_report", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("edited_doc", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "version",
            sa.Integer(),
            server_default=sa.text("1"),
            nullable=False,
        ),
        sa.Column("edited_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "generated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("clock_timestamp()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["experiment_id"],
            ["experiments.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["landing_page_id"],
            ["landing_pages.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("experiment_id", name="uq_launch_kits_experiment_id"),
    )
    op.create_index(
        "ix_launch_kits_experiment_id",
        "launch_kits",
        ["experiment_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_launch_kits_experiment_id", table_name="launch_kits")
    op.drop_table("launch_kits")
