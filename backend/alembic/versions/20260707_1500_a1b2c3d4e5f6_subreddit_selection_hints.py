"""add subreddit_selection_hints cache

Revision ID: a1b2c3d4e5f6
Revises: 95a91013f546
Create Date: 2026-07-07 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "95a91013f546"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "subreddit_selection_hints",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("normalized_key", sa.String(length=400), nullable=False),
        sa.Column("original_topic", sa.String(length=300), nullable=False),
        sa.Column("original_geography", sa.String(length=200), nullable=True),
        sa.Column("subreddits", sa.JSON(), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=True),
        sa.Column("model_used", sa.String(length=100), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=False),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("normalized_key"),
    )
    op.create_index(
        op.f("ix_subreddit_selection_hints_normalized_key"),
        "subreddit_selection_hints",
        ["normalized_key"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_subreddit_selection_hints_normalized_key"),
        table_name="subreddit_selection_hints",
    )
    op.drop_table("subreddit_selection_hints")
