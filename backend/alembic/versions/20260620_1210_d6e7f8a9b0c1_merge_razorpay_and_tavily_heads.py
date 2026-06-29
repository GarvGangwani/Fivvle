"""Merge wallet Razorpay metadata and Tavily backfill branches."""

from __future__ import annotations

from collections.abc import Sequence

revision: str = "d6e7f8a9b0c1"
down_revision: str | tuple[str, ...] | None = ("b5c6d7e8f9a0", "c1d2e3f4a5b6")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
