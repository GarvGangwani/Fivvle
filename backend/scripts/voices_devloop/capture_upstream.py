"""Capture upstream research fixtures by re-running the pipeline (dev-only).

Requires RESEARCH_DEV_CAPTURE_DIR to be set (this script sets it from --output-dir).

Usage:
  uv run python -m scripts.voices_devloop.capture_upstream \\
      --experiment-id <uuid> \\
      --output-dir scripts/voices_devloop/fixtures/upstream_us_founder_platform

Or after creating a REFINED experiment manually, pass its id. The founder's
chosen fixture idea is the US founder validation platform (see README).
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path
from uuid import UUID

from app.config import get_settings
from app.db.session import get_sessionmaker, init_engine
from app.services.research_engine_service import run_research_engine_pipeline


async def _run(experiment_id: UUID, output_dir: Path) -> None:
    os.environ["RESEARCH_DEV_CAPTURE_DIR"] = str(output_dir.resolve())
    init_engine(get_settings())
    sm = get_sessionmaker()
    await run_research_engine_pipeline(experiment_id, sm)
    print(f"Capture complete. Fixtures written to: {output_dir.resolve()}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Capture upstream research fixtures")
    parser.add_argument("--experiment-id", required=True, help="REFINED experiment UUID")
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Directory for captured JSON artifacts",
    )
    args = parser.parse_args(argv)
    asyncio.run(_run(UUID(args.experiment_id), Path(args.output_dir)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
