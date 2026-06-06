"""b4_insight_status_substates

Revision ID: f3a8b2c9d1e4
Revises: c4a1b2e3d5f6
Create Date: 2026-06-06 15:00:00.000000

Adds INSIGHT_GENERATING, INSIGHT_READY, INSIGHT_FAILED to the
ExperimentStatus enum as sub-states under the existing ANALYZING umbrella,
mirroring the RESEARCHING + RESEARCH_* precedent. Required by B4 insight
generator per docs/planning/b4-insight-generator.md §7.

This is a NO-OP at the database level. ExperimentStatus is stored as VARCHAR
with SQLAlchemy Enum(native_enum=False, length=20), so adding Python-side
enum members does not require any Postgres ALTER TYPE or constraint change.
This file exists for audit-trail lineage — every Python schema change gets
a migration file even when its DDL is empty.
"""

from typing import Sequence, Union

revision: str = "f3a8b2c9d1e4"
down_revision: Union[str, Sequence[str], None] = "c4a1b2e3d5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """No-op. See module docstring."""
    pass


def downgrade() -> None:
    """No-op. See module docstring."""
    pass
