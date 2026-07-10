"""Add experiment_spark_versions and phase spark_version_id FKs.

Revision ID: c6d7e8f9a0b1
Revises: a4b5c6d7e8f9
Create Date: 2026-07-10 15:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "c6d7e8f9a0b1"
down_revision: Union[str, Sequence[str], None] = "a4b5c6d7e8f9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "experiment_spark_versions",
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
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("raw_idea", sa.Text(), nullable=True),
        sa.Column(
            "attachment_ids_snapshot",
            postgresql.ARRAY(postgresql.UUID(as_uuid=True)),
            nullable=False,
            server_default="{}",
        ),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("clock_timestamp()"),
        ),
        sa.UniqueConstraint(
            "experiment_id",
            "version_number",
            name="uq_spark_version_experiment",
        ),
    )
    op.create_index(
        "ix_spark_versions_experiment",
        "experiment_spark_versions",
        ["experiment_id", "version_number"],
    )

    op.add_column(
        "chat_threads",
        sa.Column(
            "spark_version_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("experiment_spark_versions.id"),
            nullable=True,
        ),
    )
    op.add_column(
        "validation_reports",
        sa.Column(
            "spark_version_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("experiment_spark_versions.id"),
            nullable=True,
        ),
    )
    op.add_column(
        "landing_pages",
        sa.Column(
            "spark_version_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("experiment_spark_versions.id"),
            nullable=True,
        ),
    )
    op.add_column(
        "insight_reports",
        sa.Column(
            "spark_version_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("experiment_spark_versions.id"),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("insight_reports", "spark_version_id")
    op.drop_column("landing_pages", "spark_version_id")
    op.drop_column("validation_reports", "spark_version_id")
    op.drop_column("chat_threads", "spark_version_id")
    op.drop_index("ix_spark_versions_experiment", table_name="experiment_spark_versions")
    op.drop_table("experiment_spark_versions")
