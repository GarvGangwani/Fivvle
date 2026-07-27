"""remap ANALYZING/COMPLETED experiment statuses to INSIGHT_READY

Revision ID: o2p3q4r5s6t7
Revises: n1o2p3q4r5s6
Create Date: 2026-07-27 08:45:00.000000

Data-only migration. ANALYZING was never assigned on the forward path;
COMPLETED was only reached via unarchive when an insight report existed.
Both meant "insight terminal" — INSIGHT_READY is the honest terminal.

No column/enum/index changes (status is varchar). Downgrade cannot restore
the original status values (data loss); downgrade is a no-op on the DB side.
"""

from __future__ import annotations

import logging
from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

revision: str = "o2p3q4r5s6t7"
down_revision: Union[str, Sequence[str], None] = "n1o2p3q4r5s6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_logger = logging.getLogger("alembic.runtime.migration")


def upgrade() -> None:
    result = op.get_bind().execute(
        text(
            "UPDATE experiments SET status = 'INSIGHT_READY' "
            "WHERE status IN ('ANALYZING', 'COMPLETED')"
        )
    )
    _logger.warning(
        "PR-4 phantom status remap: %s experiment row(s) set to INSIGHT_READY "
        "(from ANALYZING or COMPLETED). Original values are not recoverable.",
        result.rowcount if result.rowcount is not None and result.rowcount >= 0 else "?",
    )


def downgrade() -> None:
    """Cannot restore ANALYZING/COMPLETED — originals were overwritten.

    Intentionally a no-op. Re-adding phantom enum members in application code
    would not resurrect which rows held which value.
    """
