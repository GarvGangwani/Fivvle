"""DEV-ONLY: write research pipeline phase outputs to JSON for voices_devloop fixtures.

Enabled only when RESEARCH_DEV_CAPTURE_DIR is set in the environment.
Never wire this into user-facing routes.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from app.logging_config import get_logger

_logger = get_logger(__name__)


def dev_capture_dir() -> Path | None:
    """Return capture directory when RESEARCH_DEV_CAPTURE_DIR is set, else None."""
    raw = os.environ.get("RESEARCH_DEV_CAPTURE_DIR", "").strip()
    if not raw:
        return None
    return Path(raw)


def dev_capture_write(filename: str, payload: Any) -> None:
    """Serialize *payload* to JSON under the capture directory if enabled."""
    directory = dev_capture_dir()
    if directory is None:
        return
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / filename
    serialized = _serialize(payload)
    path.write_text(json.dumps(serialized, indent=2, default=str), encoding="utf-8")
    _logger.info(
        "research dev capture wrote artifact",
        filename=filename,
        capture_dir=str(directory),
    )


def _serialize(payload: Any) -> Any:
    if hasattr(payload, "model_dump"):
        return payload.model_dump(mode="json")
    if isinstance(payload, list):
        return [_serialize(item) for item in payload]
    if isinstance(payload, dict):
        return {key: _serialize(value) for key, value in payload.items()}
    return payload
