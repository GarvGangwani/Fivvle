"""H-1: LLMCall Anthropic prompt caching token columns

Revision ID: b8c2d4e6f0a1
Revises: a9f3e21d84bc
Create Date: 2026-05-18 12:00:00.000000

Adds nullable columns for cache read / cache write input token counts
(see ADR 0014). No backfill — legacy rows remain NULL; aggregations use
COALESCE in application SQL.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b8c2d4e6f0a1"
down_revision: Union[str, Sequence[str], None] = "a9f3e21d84bc"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "llm_calls",
        sa.Column("cached_input_tokens", sa.Integer(), nullable=True),
    )
    op.add_column(
        "llm_calls",
        sa.Column("cache_creation_input_tokens", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("llm_calls", "cache_creation_input_tokens")
    op.drop_column("llm_calls", "cached_input_tokens")
