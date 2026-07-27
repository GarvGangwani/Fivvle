"""add refined_idea_version provenance columns

Revision ID: k8l9m0n1o2p3
Revises: i5j6k7l8m9n0
Create Date: 2026-07-26 22:30:00.000000

Second staleness dimension alongside spark_version_id:

- experiments.refined_idea_version          INTEGER NOT NULL DEFAULT 0
- validation_reports.refined_idea_version   INTEGER NULL
- landing_pages.refined_idea_version        INTEGER NULL
- insight_reports.refined_idea_version      INTEGER NULL

Bumped on refine finalize; stamped onto downstream artifacts at generation.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "k8l9m0n1o2p3"
down_revision: Union[str, Sequence[str], None] = "i5j6k7l8m9n0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "experiments",
        sa.Column(
            "refined_idea_version",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )
    op.add_column(
        "validation_reports",
        sa.Column("refined_idea_version", sa.Integer(), nullable=True),
    )
    op.add_column(
        "landing_pages",
        sa.Column("refined_idea_version", sa.Integer(), nullable=True),
    )
    op.add_column(
        "insight_reports",
        sa.Column("refined_idea_version", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("insight_reports", "refined_idea_version")
    op.drop_column("landing_pages", "refined_idea_version")
    op.drop_column("validation_reports", "refined_idea_version")
    op.drop_column("experiments", "refined_idea_version")
