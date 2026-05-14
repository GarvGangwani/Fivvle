"""B2.4: validation_reports raw_report payload + experiments research_error_detail

Revision ID: a9f3e21d84bc
Revises: c3d8a1f92b47
Create Date: 2026-05-14 06:00:00.000000

Changes
-------
validation_reports
  ADD   raw_report  JSONB NOT NULL  — verbatim ValidationReport Pydantic payload.
        Two-step pattern: add with server_default='{}', then DROP the default so
        future inserts must supply the value explicitly (fails loudly on bad code).
  DROP  research_questions, findings_per_question, competitors, reddit_signals,
        search_trends, news_signals, citations, risks, market_summary  (9 columns)
  KEEP  clarity_score      — queryable scalar; B3 synthesizer prompt will populate it.
  KEEP  reflection_loops_used — queryable scalar; B3 reflector will populate it.
  KEEP  generated_at       — audit timestamp; retained for all report versions.

experiments
  ADD   research_error_detail  TEXT NULL  — sanitised error string written by the
        state machine on RESEARCH_FAILED. NULL on success. Never stack traces.

Downgrade note
--------------
Downgrade re-creates the 9 scalar columns as nullable — existing data in raw_report
is NOT unpacked back into them (that would be costly and error-prone). The downgrade
is provided for schema rollback on a fresh/dev DB; a production rollback requires a
separate data migration to re-populate the scalar columns from raw_report.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "a9f3e21d84bc"
down_revision: Union[str, Sequence[str], None] = "c3d8a1f92b47"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    # -------------------------------------------------------------------------
    # experiments — add research_error_detail
    # -------------------------------------------------------------------------
    op.add_column(
        "experiments",
        sa.Column("research_error_detail", sa.Text(), nullable=True),
    )

    # -------------------------------------------------------------------------
    # validation_reports — add raw_report (two-step: server_default then drop)
    #
    # Step 1: Add with server_default='{}' so existing rows satisfy NOT NULL.
    #         Any existing rows are dev/test data; '{}' is a sentinel that makes
    #         them obviously invalid rather than silently hiding bad state.
    # Step 2: Alter to remove server_default so application code must supply the
    #         value — an INSERT without raw_report now raises a DB-level error
    #         rather than silently writing a wrong value.
    # -------------------------------------------------------------------------
    op.add_column(
        "validation_reports",
        sa.Column(
            "raw_report",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
    )
    op.alter_column(
        "validation_reports",
        "raw_report",
        server_default=None,
    )

    # -------------------------------------------------------------------------
    # validation_reports — drop the 9 legacy scalar columns
    # -------------------------------------------------------------------------
    _COLUMNS_TO_DROP = [
        "research_questions",
        "findings_per_question",
        "competitors",
        "reddit_signals",
        "search_trends",
        "news_signals",
        "citations",
        "risks",
        "market_summary",
    ]
    for col in _COLUMNS_TO_DROP:
        op.drop_column("validation_reports", col)


def downgrade() -> None:
    """Downgrade schema.

    WARNING: The 9 scalar columns are re-created as nullable but are NOT
    repopulated from raw_report. Use only on dev/test databases. A production
    rollback requires a separate data migration step.
    """

    # -------------------------------------------------------------------------
    # validation_reports — restore 9 legacy columns (nullable, no data)
    # -------------------------------------------------------------------------
    op.add_column("validation_reports", sa.Column("market_summary", sa.Text(), nullable=True))
    op.add_column("validation_reports", sa.Column("risks", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("validation_reports", sa.Column("citations", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("validation_reports", sa.Column("news_signals", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("validation_reports", sa.Column("search_trends", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("validation_reports", sa.Column("reddit_signals", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("validation_reports", sa.Column("competitors", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("validation_reports", sa.Column("findings_per_question", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("validation_reports", sa.Column("research_questions", postgresql.JSONB(astext_type=sa.Text()), nullable=True))

    # -------------------------------------------------------------------------
    # validation_reports — drop raw_report
    # -------------------------------------------------------------------------
    op.drop_column("validation_reports", "raw_report")

    # -------------------------------------------------------------------------
    # experiments — drop research_error_detail
    # -------------------------------------------------------------------------
    op.drop_column("experiments", "research_error_detail")
