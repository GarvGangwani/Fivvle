"""One-shot cleanup: remove UI telemetry rows from experiment_events."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from sqlalchemy import delete

from app.config import get_settings
from app.db.models.experiment_event import ExperimentEvent
from app.db.session import get_sessionmaker, init_engine
from app.logging_config import configure_logging, get_logger

_logger = get_logger(__name__)

TELEMETRY_EVENT_TYPES = ("node_moved", "layout_reset", "nodes_repositioned")


async def main() -> None:
    settings = get_settings()
    configure_logging(settings)
    init_engine(settings)
    session_factory = get_sessionmaker()

    async with session_factory() as db:
        result = await db.execute(
            delete(ExperimentEvent).where(
                ExperimentEvent.event_type.in_(TELEMETRY_EVENT_TYPES)
            )
        )
        await db.commit()
        deleted = result.rowcount or 0

    _logger.info("purge_ui_telemetry_events_complete", deleted=deleted)
    print(f"Deleted {deleted} UI telemetry experiment_events row(s).")


if __name__ == "__main__":
    asyncio.run(main())
