"""add landing_page_publishes cohorts + publish_id FKs

Revision ID: m0n1o2p3q4r5
Revises: l9m0n1o2p3q4
Create Date: 2026-07-26 23:45:00.000000

Publish cohorts isolate Signal analytics across republishes.
Also adds insight_reports.publish_id (SET NULL) so insight reports
stamp the cohort they were generated against (PR-3 Step 6).
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "m0n1o2p3q4r5"
down_revision: Union[str, Sequence[str], None] = "l9m0n1o2p3q4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "landing_page_publishes",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "landing_page_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("landing_pages.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("publish_number", sa.Integer(), nullable=False),
        sa.Column(
            "published_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("clock_timestamp()"),
        ),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint(
            "landing_page_id",
            "publish_number",
            name="uq_landing_page_publishes_landing_number",
        ),
    )
    op.create_index(
        "ix_landing_page_publishes_landing_page_id",
        "landing_page_publishes",
        ["landing_page_id"],
    )

    # Synthetic cohort #1 for every already-published landing page.
    op.execute(
        """
        INSERT INTO landing_page_publishes (
            id, landing_page_id, publish_number, published_at, ended_at
        )
        SELECT gen_random_uuid(), id, 1, live_at, NULL
        FROM landing_pages
        WHERE live_at IS NOT NULL
        """
    )

    op.add_column(
        "page_views",
        sa.Column(
            "publish_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )
    op.create_foreign_key(
        "fk_page_views_publish_id_landing_page_publishes",
        "page_views",
        "landing_page_publishes",
        ["publish_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_page_views_publish_id", "page_views", ["publish_id"])

    op.add_column(
        "waitlist_signups",
        sa.Column(
            "publish_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )
    op.create_foreign_key(
        "fk_waitlist_signups_publish_id_landing_page_publishes",
        "waitlist_signups",
        "landing_page_publishes",
        ["publish_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index(
        "ix_waitlist_signups_publish_id",
        "waitlist_signups",
        ["publish_id"],
    )

    op.execute(
        """
        UPDATE page_views AS pv
        SET publish_id = lpp.id
        FROM landing_pages AS lp
        JOIN landing_page_publishes AS lpp
          ON lpp.landing_page_id = lp.id
         AND lpp.publish_number = 1
        WHERE pv.experiment_id = lp.experiment_id
          AND lp.live_at IS NOT NULL
          AND pv.publish_id IS NULL
        """
    )
    op.execute(
        """
        UPDATE waitlist_signups AS ws
        SET publish_id = lpp.id
        FROM landing_pages AS lp
        JOIN landing_page_publishes AS lpp
          ON lpp.landing_page_id = lp.id
         AND lpp.publish_number = 1
        WHERE ws.experiment_id = lp.experiment_id
          AND lp.live_at IS NOT NULL
          AND ws.publish_id IS NULL
        """
    )

    # Insight reports stamp the cohort they document; SET NULL so they survive
    # cohort deletion (unlike analytics rows which CASCADE).
    op.add_column(
        "insight_reports",
        sa.Column(
            "publish_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )
    op.create_foreign_key(
        "fk_insight_reports_publish_id_landing_page_publishes",
        "insight_reports",
        "landing_page_publishes",
        ["publish_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_insight_reports_publish_id",
        "insight_reports",
        ["publish_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_insight_reports_publish_id", table_name="insight_reports")
    op.drop_constraint(
        "fk_insight_reports_publish_id_landing_page_publishes",
        "insight_reports",
        type_="foreignkey",
    )
    op.drop_column("insight_reports", "publish_id")

    op.drop_index("ix_waitlist_signups_publish_id", table_name="waitlist_signups")
    op.drop_constraint(
        "fk_waitlist_signups_publish_id_landing_page_publishes",
        "waitlist_signups",
        type_="foreignkey",
    )
    op.drop_column("waitlist_signups", "publish_id")

    op.drop_index("ix_page_views_publish_id", table_name="page_views")
    op.drop_constraint(
        "fk_page_views_publish_id_landing_page_publishes",
        "page_views",
        type_="foreignkey",
    )
    op.drop_column("page_views", "publish_id")

    op.drop_index(
        "ix_landing_page_publishes_landing_page_id",
        table_name="landing_page_publishes",
    )
    op.drop_table("landing_page_publishes")
