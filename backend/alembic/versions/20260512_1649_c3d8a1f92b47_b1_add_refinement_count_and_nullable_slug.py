"""B1: add ExperimentStatus enum and refinement_count to experiments

Revision ID: c3d8a1f92b47
Revises: 8f9aefb8ca69
Create Date: 2026-05-12 16:49:00.000000

Changes:
- experiments.slug: DROP NOT NULL (slug is generated at landing-page publish time, per
  ARCHITECTURE.md and USER_FLOW Stage 4.3; it is not available at experiment creation).
- experiments.refinement_count: ADD COLUMN INTEGER NOT NULL DEFAULT 0
  Tracks regeneration cap (5 per experiment, per .cursorrules "Cost Tracking & Limits").

Note: ExperimentStatus enum already exists in full in the initial migration (all 17
values). No enum changes are required here.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "c3d8a1f92b47"
down_revision: Union[str, Sequence[str], None] = "8f9aefb8ca69"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Make slug nullable — slug is generated at landing-page publish time (B3/FE5),
    # not at idea submission time. Keeping it NOT NULL blocked experiment creation.
    op.alter_column("experiments", "slug", existing_type=sa.String(length=50), nullable=True)

    # Add refinement_count — tracks the regeneration cap (5 per experiment).
    # server_default="0" so existing rows get a valid value without a data migration.
    op.add_column(
        "experiments",
        sa.Column(
            "refinement_count",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("experiments", "refinement_count")

    # Reverting slug to NOT NULL requires all existing rows to have a slug.
    # In practice this downgrade is only safe on a fresh DB with no data.
    # A production rollback would need a data backfill first.
    op.alter_column("experiments", "slug", existing_type=sa.String(length=50), nullable=False)
