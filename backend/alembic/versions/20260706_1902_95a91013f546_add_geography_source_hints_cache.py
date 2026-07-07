"""add geography_source_hints cache

Revision ID: 95a91013f546
Revises: 4c35bfa5b030
Create Date: 2026-07-06 19:02:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "95a91013f546"
down_revision: Union[str, Sequence[str], None] = "4c35bfa5b030"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "geography_source_hints",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("normalized_key", sa.String(length=200), nullable=False),
        sa.Column("original_geography", sa.String(length=200), nullable=False),
        sa.Column(
            "include_domains",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("rationale", sa.Text(), nullable=True),
        sa.Column("model_used", sa.String(length=100), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("normalized_key"),
    )
    op.create_index(
        op.f("ix_geography_source_hints_normalized_key"),
        "geography_source_hints",
        ["normalized_key"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_geography_source_hints_normalized_key"),
        table_name="geography_source_hints",
    )
    op.drop_table("geography_source_hints")
