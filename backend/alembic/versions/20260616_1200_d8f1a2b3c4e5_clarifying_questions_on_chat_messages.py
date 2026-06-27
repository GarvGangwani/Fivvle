"""clarifying_questions_on_chat_messages

Revision ID: d8f1a2b3c4e5
Revises: b2e4f8a1c3d6
Create Date: 2026-06-16 12:00:00.000000

Stores structured refinement questions on assistant chat messages for the
question-block UI.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "d8f1a2b3c4e5"
down_revision: Union[str, Sequence[str], None] = "b2e4f8a1c3d6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "chat_messages",
        sa.Column(
            "clarifying_questions",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("chat_messages", "clarifying_questions")
