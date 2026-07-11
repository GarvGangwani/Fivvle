"""chat_message_tree

Revision ID: f9a0b1c2d3e4
Revises: e8f9a0b1c2d3
Create Date: 2026-07-11 13:30:00.000000

Add parent_message_id (message tree) and chat_threads.active_leaf_message_id.
Backfill existing linear threads into degenerate single-branch trees.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "f9a0b1c2d3e4"
down_revision: Union[str, Sequence[str], None] = "e8f9a0b1c2d3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "chat_messages",
        sa.Column(
            "parent_message_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )
    op.create_foreign_key(
        "fk_chat_messages_parent_message_id",
        "chat_messages",
        "chat_messages",
        ["parent_message_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index(
        "ix_chat_messages_parent",
        "chat_messages",
        ["parent_message_id"],
    )

    op.add_column(
        "chat_threads",
        sa.Column(
            "active_leaf_message_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )
    op.create_foreign_key(
        "fk_chat_threads_active_leaf_message_id",
        "chat_threads",
        "chat_messages",
        ["active_leaf_message_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # Linear chats → degenerate trees (each message's parent is the prior in thread).
    op.execute(
        """
        WITH ordered_messages AS (
            SELECT
                id,
                thread_id,
                LAG(id) OVER (
                    PARTITION BY thread_id ORDER BY created_at, id
                ) AS prev_id
            FROM chat_messages
        )
        UPDATE chat_messages
        SET parent_message_id = ordered_messages.prev_id
        FROM ordered_messages
        WHERE chat_messages.id = ordered_messages.id
          AND ordered_messages.prev_id IS NOT NULL
        """
    )

    # Active leaf = chronologically latest message per thread.
    op.execute(
        """
        UPDATE chat_threads
        SET active_leaf_message_id = latest.id
        FROM (
            SELECT DISTINCT ON (thread_id) thread_id, id
            FROM chat_messages
            ORDER BY thread_id, created_at DESC, id DESC
        ) AS latest
        WHERE chat_threads.id = latest.thread_id
        """
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_chat_threads_active_leaf_message_id",
        "chat_threads",
        type_="foreignkey",
    )
    op.drop_column("chat_threads", "active_leaf_message_id")
    op.drop_index("ix_chat_messages_parent", table_name="chat_messages")
    op.drop_constraint(
        "fk_chat_messages_parent_message_id",
        "chat_messages",
        type_="foreignkey",
    )
    op.drop_column("chat_messages", "parent_message_id")
