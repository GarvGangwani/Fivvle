"""Add original idea capture fields and chat attachment freeze link.

Revision ID: p3q4r5s6t7u8
Revises: o2p3q4r5s6t7
Create Date: 2026-08-05 21:30:00.000000

Additive only — no backfill. Existing experiments keep null original_idea /
idea_theme; chat_attachments.origin_experiment_id stays null until capture.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "p3q4r5s6t7u8"
down_revision: str | Sequence[str] | None = "o2p3q4r5s6t7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "experiments",
        sa.Column("original_idea", sa.Text(), nullable=True),
    )
    op.add_column(
        "experiments",
        sa.Column(
            "original_idea_captured_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        "experiments",
        sa.Column("idea_theme", sa.String(length=20), nullable=True),
    )

    op.add_column(
        "chat_attachments",
        sa.Column(
            "origin_experiment_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )
    op.create_foreign_key(
        "fk_chat_attachments_origin_experiment_id",
        "chat_attachments",
        "experiments",
        ["origin_experiment_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_chat_attachments_origin_experiment_id",
        "chat_attachments",
        ["origin_experiment_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_chat_attachments_origin_experiment_id",
        table_name="chat_attachments",
    )
    op.drop_constraint(
        "fk_chat_attachments_origin_experiment_id",
        "chat_attachments",
        type_="foreignkey",
    )
    op.drop_column("chat_attachments", "origin_experiment_id")
    op.drop_column("experiments", "idea_theme")
    op.drop_column("experiments", "original_idea_captured_at")
    op.drop_column("experiments", "original_idea")
