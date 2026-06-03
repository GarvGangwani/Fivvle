"""chat_threads_and_refinement_metadata

Revision ID: c4a1b2e3d5f6
Revises: b8c2d4e6f0a1
Create Date: 2026-06-03 12:00:00.000000

Adds chat-mode refinement tables (chat_threads, chat_messages,
refinement_idempotency) and experiments.thread_id / dispatch_trigger per
ADR 0019 and docs/planning/chat-mode-refinement.md §8.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "c4a1b2e3d5f6"
down_revision: Union[str, Sequence[str], None] = "b8c2d4e6f0a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "chat_threads",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_chat_threads_user_id"), "chat_threads", ["user_id"], unique=False)

    op.create_table(
        "chat_messages",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("thread_id", sa.UUID(), nullable=False),
        sa.Column(
            "role",
            sa.Enum("user", "assistant", name="chat_role", native_enum=False, length=20),
            nullable=False,
        ),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("experiment_id", sa.UUID(), nullable=True),
        sa.Column(
            "turn_kind",
            sa.Enum(
                "normal_chat",
                "refinement_clarify",
                "refinement_finalize",
                "dispatch_announce",
                "pipeline_progress",
                "pipeline_complete",
                "pipeline_failed",
                name="chat_turn_kind",
                native_enum=False,
                length=40,
            ),
            nullable=True,
        ),
        sa.Column("clarifying_dimension", sa.String(length=40), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["experiment_id"], ["experiments.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["thread_id"], ["chat_threads.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_chat_messages_thread_id",
        "chat_messages",
        ["thread_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "idx_chat_messages_experiment_id",
        "chat_messages",
        ["experiment_id"],
        unique=False,
    )

    op.create_table(
        "refinement_idempotency",
        sa.Column("thread_id", sa.UUID(), nullable=False),
        sa.Column("idempotency_key", sa.Text(), nullable=False),
        sa.Column(
            "response_payload",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("experiment_id", sa.UUID(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["experiment_id"], ["experiments.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("thread_id", "idempotency_key"),
    )
    op.create_index(
        "idx_refinement_idempotency_created_at",
        "refinement_idempotency",
        ["created_at"],
        unique=False,
    )

    op.add_column("experiments", sa.Column("thread_id", sa.UUID(), nullable=True))
    op.add_column(
        "experiments",
        sa.Column(
            "dispatch_trigger",
            sa.Enum(
                "user_confirm",
                "auto_fire",
                name="dispatch_trigger",
                native_enum=False,
                length=20,
            ),
            nullable=True,
        ),
    )
    op.create_foreign_key(
        "fk_experiments_thread_id_chat_threads",
        "experiments",
        "chat_threads",
        ["thread_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(op.f("ix_experiments_thread_id"), "experiments", ["thread_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_experiments_thread_id"), table_name="experiments")
    op.drop_constraint("fk_experiments_thread_id_chat_threads", "experiments", type_="foreignkey")
    op.drop_column("experiments", "dispatch_trigger")
    op.drop_column("experiments", "thread_id")

    op.drop_index(
        "idx_refinement_idempotency_created_at",
        table_name="refinement_idempotency",
    )
    op.drop_table("refinement_idempotency")

    op.drop_index("idx_chat_messages_experiment_id", table_name="chat_messages")
    op.drop_index("idx_chat_messages_thread_id", table_name="chat_messages")
    op.drop_table("chat_messages")

    op.drop_index(op.f("ix_chat_threads_user_id"), table_name="chat_threads")
    op.drop_table("chat_threads")
