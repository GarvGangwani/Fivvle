"""Add viewport pan/zoom columns to experiment_canvas_layouts.

Revision ID: d7e8f9a0b1c2
Revises: c6d7e8f9a0b1
Create Date: 2026-07-10 15:45:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d7e8f9a0b1c2"
down_revision: Union[str, Sequence[str], None] = "c6d7e8f9a0b1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "experiment_canvas_layouts",
        sa.Column("viewport_x", sa.Float(), nullable=True),
    )
    op.add_column(
        "experiment_canvas_layouts",
        sa.Column("viewport_y", sa.Float(), nullable=True),
    )
    op.add_column(
        "experiment_canvas_layouts",
        sa.Column("viewport_zoom", sa.Float(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("experiment_canvas_layouts", "viewport_zoom")
    op.drop_column("experiment_canvas_layouts", "viewport_y")
    op.drop_column("experiment_canvas_layouts", "viewport_x")
