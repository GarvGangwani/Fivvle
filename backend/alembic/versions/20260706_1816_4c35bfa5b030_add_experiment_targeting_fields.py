"""add experiment targeting fields

Revision ID: 4c35bfa5b030
Revises: h4i5j6k7l8m9
Create Date: 2026-07-06 18:16:32.290467

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "4c35bfa5b030"
down_revision: Union[str, Sequence[str], None] = "h4i5j6k7l8m9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "experiments",
        sa.Column("target_geography", sa.String(length=200), nullable=True),
    )
    op.add_column(
        "experiments",
        sa.Column("audience_bracket", sa.String(length=300), nullable=True),
    )
    op.add_column(
        "experiments",
        sa.Column("stage", sa.String(length=20), nullable=True),
    )
    op.add_column(
        "experiments",
        sa.Column("why_now", sa.String(length=500), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("experiments", "why_now")
    op.drop_column("experiments", "stage")
    op.drop_column("experiments", "audience_bracket")
    op.drop_column("experiments", "target_geography")
