"""One-time backfill: generate tags for existing experiments with empty tags."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Allow running as `python -m scripts.backfill_experiment_tags` from backend/
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from sqlalchemy import select

from app.config import get_settings
from app.db.models.experiment import Experiment
from app.db.session import get_sessionmaker, init_engine
from app.logging_config import configure_logging, get_logger
from app.schemas.refinement import RefinedIdea
from app.services.tag_service import build_refined_idea_text, generate_tags

_logger = get_logger(__name__)
_CONCURRENCY = 5


async def _process_one(session_factory, experiment: Experiment) -> bool:
    async with session_factory() as db:
        if not experiment.refined_idea:
            return False
        try:
            refined = RefinedIdea.model_validate(experiment.refined_idea)
        except Exception:
            return False
        text = build_refined_idea_text(refined)
        tags = await generate_tags(db, text, experiment.id)
        row = await db.get(Experiment, experiment.id)
        if row is None:
            return False
        row.tags = tags
        await db.commit()
        return bool(tags)


async def main() -> None:
    settings = get_settings()
    configure_logging(settings)
    init_engine(settings)

    session_factory = get_sessionmaker()

    async with session_factory() as db:
        result = await db.execute(
            select(Experiment).where(
                Experiment.refined_idea.is_not(None),
                Experiment.tags == [],
            )
        )
        experiments = list(result.scalars().all())

    total = len(experiments)
    _logger.info("backfill starting", experiment_count=total)
    if total == 0:
        print("No experiments to backfill.")
        return

    semaphore = asyncio.Semaphore(_CONCURRENCY)
    processed = 0
    succeeded = 0
    failed = 0

    async def run(exp: Experiment) -> None:
        nonlocal processed, succeeded, failed
        async with semaphore:
            try:
                ok = await _process_one(session_factory, exp)
                if ok:
                    succeeded += 1
                else:
                    failed += 1
            except Exception:
                failed += 1
                _logger.warning("backfill row failed", experiment_id=str(exp.id), exc_info=True)
            processed += 1
            if processed % 10 == 0 or processed == total:
                _logger.info(
                    "backfill progress",
                    processed=processed,
                    total=total,
                    succeeded=succeeded,
                    failed=failed,
                )

    await asyncio.gather(*(run(exp) for exp in experiments))
    print(
        f"Backfill complete: {processed} processed, {succeeded} tagged, {failed} empty/failed."
    )


if __name__ == "__main__":
    asyncio.run(main())
