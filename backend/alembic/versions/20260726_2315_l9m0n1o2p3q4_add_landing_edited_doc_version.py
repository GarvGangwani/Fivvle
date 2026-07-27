"""add landing_pages.edited_doc_version stamp

Revision ID: l9m0n1o2p3q4
Revises: k8l9m0n1o2p3
Create Date: 2026-07-26 23:15:00.000000

Third staleness dimension for Launch: stamp of ValidationReport.edited_doc_version
at landing generation time. NULLABLE — null means "generated before this dimension
existed" and is treated as not-stale by _is_stale.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "l9m0n1o2p3q4"
down_revision: Union[str, Sequence[str], None] = "k8l9m0n1o2p3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "landing_pages",
        sa.Column("edited_doc_version", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("landing_pages", "edited_doc_version")
