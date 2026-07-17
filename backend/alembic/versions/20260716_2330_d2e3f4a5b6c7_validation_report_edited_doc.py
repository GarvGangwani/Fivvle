"""validation_report_edited_doc

Revision ID: d2e3f4a5b6c7
Revises: a0b1c2d3e4f5
Create Date: 2026-07-16 23:30:00.000000

Add the founder-editable ProseMirror overlay columns to validation_reports:

- edited_doc          JSONB     NULL    — persisted ProseMirror-doc JSON (NULL = never edited)
- edited_doc_version  INT       NOT NULL DEFAULT 0 — optimistic-concurrency counter
- edited_at           TIMESTAMPTZ NULL  — timestamp of last successful edit

raw_report is left untouched and remains the immutable source of truth.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "d2e3f4a5b6c7"
down_revision: Union[str, Sequence[str], None] = "a0b1c2d3e4f5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "validation_reports",
        sa.Column(
            "edited_doc",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )
    op.add_column(
        "validation_reports",
        sa.Column(
            "edited_doc_version",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
    )
    op.add_column(
        "validation_reports",
        sa.Column(
            "edited_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("validation_reports", "edited_at")
    op.drop_column("validation_reports", "edited_doc_version")
    op.drop_column("validation_reports", "edited_doc")
