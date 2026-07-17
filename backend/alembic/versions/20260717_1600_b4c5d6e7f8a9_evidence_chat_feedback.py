"""evidence_chat_feedback

Revision ID: b4c5d6e7f8a9
Revises: e3f4a5b6c7d8
Create Date: 2026-07-17 16:00:00.000000

Write-only thumbs feedback on assistant evidence-chat replies:

- id           UUID  PK
- message_id   UUID  NOT NULL  FK → chat_messages.id (ON DELETE CASCADE), UNIQUE
- user_id      UUID  NOT NULL  FK → users.id (ON DELETE CASCADE)
- verdict      TEXT  NOT NULL  CHECK (verdict IN ('up','down'))
- created_at   TIMESTAMPTZ  NOT NULL  DEFAULT now()

UNIQUE(message_id) enforces one verdict per message; the endpoint upserts.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "b4c5d6e7f8a9"
down_revision: Union[str, Sequence[str], None] = "e3f4a5b6c7d8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "evidence_chat_feedback",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("message_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("verdict", sa.String(length=4), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "verdict IN ('up','down')",
            name="ck_evidence_chat_feedback_verdict",
        ),
        sa.ForeignKeyConstraint(
            ["message_id"],
            ["chat_messages.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("message_id", name="uq_evidence_chat_feedback_message_id"),
    )


def downgrade() -> None:
    op.drop_table("evidence_chat_feedback")
