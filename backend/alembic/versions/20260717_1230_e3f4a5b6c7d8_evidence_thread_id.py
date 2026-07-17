"""evidence_thread_id

Revision ID: e3f4a5b6c7d8
Revises: d2e3f4a5b6c7
Create Date: 2026-07-17 12:30:00.000000

Add the evidence-chat thread link to experiments:

- evidence_thread_id  UUID  NULL  FK → chat_threads.id (ON DELETE SET NULL), indexed

Mirrors the existing thread_id column (refinement thread). Separate column so
evidence chat never mixes with refinement/discussion history. Created on the
first evidence-chat message.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "e3f4a5b6c7d8"
down_revision: Union[str, Sequence[str], None] = "d2e3f4a5b6c7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "experiments",
        sa.Column(
            "evidence_thread_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )
    op.create_index(
        op.f("ix_experiments_evidence_thread_id"),
        "experiments",
        ["evidence_thread_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_experiments_evidence_thread_id_chat_threads",
        "experiments",
        "chat_threads",
        ["evidence_thread_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_experiments_evidence_thread_id_chat_threads",
        "experiments",
        type_="foreignkey",
    )
    op.drop_index(
        op.f("ix_experiments_evidence_thread_id"),
        table_name="experiments",
    )
    op.drop_column("experiments", "evidence_thread_id")
