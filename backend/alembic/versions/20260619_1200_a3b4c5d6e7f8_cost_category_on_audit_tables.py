"""Add cost_category to llm_calls and external_api_calls with backfill."""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a3b4c5d6e7f8"
down_revision: str | None = "f1a2b3c4d5e6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_CATEGORY_COL = sa.String(length=30)

_LLM_BACKFILL = """
UPDATE llm_calls
SET cost_category = CASE
    WHEN phase IN (
        'refinement', 'refinement_chat', 'chat_normal',
        'chat_discussion', 'chat_attachment'
    ) THEN 'refinement'
    WHEN phase IN (
        'planner', 'searcher', 'reader', 'reflector', 'synthesizer'
    ) THEN 'cognitive_validation'
    WHEN phase = 'landing_page' THEN 'landing_page'
    WHEN phase = 'insight' THEN 'insight'
    ELSE 'platform'
END
WHERE cost_category IS NULL
"""

_EXT_BACKFILL = """
UPDATE external_api_calls
SET cost_category = CASE
    WHEN provider IN ('tavily', 'reddit', 'pytrends') THEN 'cognitive_validation'
    WHEN provider = 'ipwho' THEN 'landing_page'
    ELSE 'platform'
END
WHERE cost_category IS NULL
"""


def upgrade() -> None:
    op.add_column(
        "llm_calls",
        sa.Column("cost_category", _CATEGORY_COL, nullable=True),
    )
    op.add_column(
        "external_api_calls",
        sa.Column("cost_category", _CATEGORY_COL, nullable=True),
    )

    op.execute(_LLM_BACKFILL)
    op.execute(_EXT_BACKFILL)

    op.alter_column(
        "llm_calls",
        "cost_category",
        existing_type=_CATEGORY_COL,
        nullable=False,
        server_default="platform",
    )
    op.alter_column(
        "external_api_calls",
        "cost_category",
        existing_type=_CATEGORY_COL,
        nullable=False,
        server_default="platform",
    )

    op.create_index(
        op.f("ix_llm_calls_cost_category"),
        "llm_calls",
        ["cost_category"],
        unique=False,
    )
    op.create_index(
        op.f("ix_external_api_calls_cost_category"),
        "external_api_calls",
        ["cost_category"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_external_api_calls_cost_category"),
        table_name="external_api_calls",
    )
    op.drop_index(op.f("ix_llm_calls_cost_category"), table_name="llm_calls")
    op.drop_column("external_api_calls", "cost_category")
    op.drop_column("llm_calls", "cost_category")
