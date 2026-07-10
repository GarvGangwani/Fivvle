"""Add SPARK status, spark timestamps, and experiment_attachments.

Revision ID: a4b5c6d7e8f9
Revises: f3a4b5c6d7e8
Create Date: 2026-07-10 13:30:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "a4b5c6d7e8f9"
down_revision: Union[str, Sequence[str], None] = "f3a4b5c6d7e8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "experiments",
        sa.Column(
            "spark_last_edited_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        "experiments",
        sa.Column(
            "refinement_started_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )

    # Empty-idea DRAFT rows become SPARK (new first-phase semantics).
    # DRAFT rows that already have idea text stay DRAFT (legacy mid-flow).
    op.execute(
        sa.text(
            """
            UPDATE experiments
            SET status = 'SPARK'
            WHERE status = 'DRAFT'
              AND (raw_idea IS NULL OR BTRIM(raw_idea) = '')
            """
        )
    )

    op.create_table(
        "experiment_attachments",
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
        sa.Column("attachment_type", sa.String(length=50), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("content_text", sa.Text(), nullable=True),
        sa.Column("file_url", sa.Text(), nullable=True),
        sa.Column("file_mime", sa.String(length=100), nullable=True),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("clock_timestamp()"),
        ),
    )
    op.create_index(
        "ix_attachments_experiment",
        "experiment_attachments",
        ["experiment_id"],
    )
    op.create_index(
        "ix_experiment_attachments_user_id",
        "experiment_attachments",
        ["user_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_experiment_attachments_user_id",
        table_name="experiment_attachments",
    )
    op.drop_index("ix_attachments_experiment", table_name="experiment_attachments")
    op.drop_table("experiment_attachments")

    op.execute(
        sa.text(
            """
            UPDATE experiments
            SET status = 'DRAFT'
            WHERE status = 'SPARK'
            """
        )
    )
    op.drop_column("experiments", "refinement_started_at")
    op.drop_column("experiments", "spark_last_edited_at")
