"""add_name_to_experiments

Revision ID: b2e4f8a1c3d6
Revises: 0d993ecaf65f
Create Date: 2026-06-10 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "b2e4f8a1c3d6"
down_revision: Union[str, Sequence[str], None] = "0d993ecaf65f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("experiments", sa.Column("name", sa.String(length=100), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("experiments", "name")
