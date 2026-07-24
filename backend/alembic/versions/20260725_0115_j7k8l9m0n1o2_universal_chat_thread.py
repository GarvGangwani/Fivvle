"""universal_chat_thread

Revision ID: j7k8l9m0n1o2
Revises: b4c5d6e7f8a9
Create Date: 2026-07-25 01:15:00.000000

Additive schema for the universal-chat surface (isolated from Refine/Evidence):

- experiments.universal_thread_id  UUID NULL  FK → chat_threads (ON DELETE SET NULL), indexed
- chat_messages.tool_payload       JSONB NULL  structured tool_call / tool_result payload

ChatRole TOOL_CALL / TOOL_RESULT and ChatTurnKind UNIVERSAL_CHAT are Python-side
StrEnum extensions stored via native_enum=False VARCHAR — no Postgres ALTER TYPE.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "j7k8l9m0n1o2"
down_revision: Union[str, Sequence[str], None] = "b4c5d6e7f8a9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "experiments",
        sa.Column(
            "universal_thread_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )
    op.create_index(
        op.f("ix_experiments_universal_thread_id"),
        "experiments",
        ["universal_thread_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_experiments_universal_thread_id_chat_threads",
        "experiments",
        "chat_threads",
        ["universal_thread_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.add_column(
        "chat_messages",
        sa.Column(
            "tool_payload",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("chat_messages", "tool_payload")
    op.drop_constraint(
        "fk_experiments_universal_thread_id_chat_threads",
        "experiments",
        type_="foreignkey",
    )
    op.drop_index(
        op.f("ix_experiments_universal_thread_id"),
        table_name="experiments",
    )
    op.drop_column("experiments", "universal_thread_id")
