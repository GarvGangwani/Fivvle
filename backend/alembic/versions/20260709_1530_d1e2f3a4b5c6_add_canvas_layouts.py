"""add experiment canvas layouts table

Revision ID: d1e2f3a4b5c6
Revises: c8d9e0f1a2b3
Create Date: 2026-07-09 15:30:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "d1e2f3a4b5c6"
down_revision: Union[str, Sequence[str], None] = "c8d9e0f1a2b3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "experiment_canvas_layouts",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "experiment_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("experiments.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "node_positions",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("clock_timestamp()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("clock_timestamp()"),
        ),
        sa.UniqueConstraint("experiment_id", "user_id", name="uq_canvas_layout_exp_user"),
    )
    op.create_index(
        "ix_experiment_canvas_layouts_experiment_id",
        "experiment_canvas_layouts",
        ["experiment_id"],
    )
    op.create_index(
        "ix_experiment_canvas_layouts_user_id",
        "experiment_canvas_layouts",
        ["user_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_experiment_canvas_layouts_user_id", table_name="experiment_canvas_layouts")
    op.drop_index(
        "ix_experiment_canvas_layouts_experiment_id",
        table_name="experiment_canvas_layouts",
    )
    op.drop_table("experiment_canvas_layouts")
