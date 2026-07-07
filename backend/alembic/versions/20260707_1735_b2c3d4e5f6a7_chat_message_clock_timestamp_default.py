"""chat_messages created_at uses clock_timestamp() default

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-07-07 17:35:00.000000

PostgreSQL NOW() is stable within a transaction, so user and assistant rows
written in the same chat turn shared identical created_at values. Use
clock_timestamp() so each INSERT gets the actual statement time.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "chat_messages",
        "created_at",
        server_default=sa.text("clock_timestamp()"),
    )


def downgrade() -> None:
    op.alter_column(
        "chat_messages",
        "created_at",
        server_default=sa.text("now()"),
    )
