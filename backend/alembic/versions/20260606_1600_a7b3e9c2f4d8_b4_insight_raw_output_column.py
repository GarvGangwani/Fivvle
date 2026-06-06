"""b4_insight_raw_output_column

Revision ID: a7b3e9c2f4d8
Revises: f3a8b2c9d1e4
Create Date: 2026-06-06 16:00:00.000000

Adds insight_reports.raw_output JSONB column. Holds the full InsightReportOutput
Pydantic payload, mirroring the ValidationReport.raw_report pattern. Required by
B4 insight service per docs/planning/b4-insight-generator.md §4.2 — fields like
recommendation_confidence, recommendation_rationale, what_would_change_this, and
schema_version do not have scalar columns and live inside raw_output.

Nullable to keep existing rows backfillable. New insight rows written by the
service will always populate this column.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "a7b3e9c2f4d8"
down_revision: Union[str, Sequence[str], None] = "f3a8b2c9d1e4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "insight_reports",
        sa.Column(
            "raw_output",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("insight_reports", "raw_output")
