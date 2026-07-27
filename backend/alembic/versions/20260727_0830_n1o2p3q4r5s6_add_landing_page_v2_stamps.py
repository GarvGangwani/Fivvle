"""add landing_page_v2_specs cascade stamps

Revision ID: n1o2p3q4r5s6
Revises: m0n1o2p3q4r5
Create Date: 2026-07-27 08:30:00.000000

Bring LandingPageV2Spec under the same staleness stamp dimensions as v1
landing_pages: spark_version_id, refined_idea_version, edited_doc_version.
NULLABLE — null means generated before this dimension existed (not-stale).
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "n1o2p3q4r5s6"
down_revision: Union[str, Sequence[str], None] = "m0n1o2p3q4r5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "landing_page_v2_specs",
        sa.Column(
            "spark_version_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("experiment_spark_versions.id"),
            nullable=True,
        ),
    )
    op.add_column(
        "landing_page_v2_specs",
        sa.Column("refined_idea_version", sa.Integer(), nullable=True),
    )
    op.add_column(
        "landing_page_v2_specs",
        sa.Column("edited_doc_version", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("landing_page_v2_specs", "edited_doc_version")
    op.drop_column("landing_page_v2_specs", "refined_idea_version")
    op.drop_column("landing_page_v2_specs", "spark_version_id")
