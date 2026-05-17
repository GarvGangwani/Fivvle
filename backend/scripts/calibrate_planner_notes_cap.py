"""Empirical calibration helper for planner_v1 `notes_for_synthesizer` length.

Until length-log harvesting is wired up (e.g. aggregating structured
`planner_field_lengths` DEBUG events from Cloud Logging), this script will
return zero non-null observations against `llm_calls` alone. The script logic
remains correct; the durable store for planner output payloads is the blocker.

Queries Postgres for planner LLM audit rows (`llm_calls.prompt_name`), attempts
to read structured payloads if present, and prints length statistics plus the
five longest notes.

Run from the repository root:

    backend/.venv/Scripts/python.exe backend/scripts/calibrate_planner_notes_cap.py

Expects DATABASE_URL via backend/.env (loaded explicitly below); requires the
Docker Postgres instance to be reachable.
"""

from __future__ import annotations

import asyncio
import json
import math
import re
import sys
from pathlib import Path
from typing import Any

from sqlalchemy import func, select, text

# ---------------------------------------------------------------------------
# Path + env: runnable from repo root (Fivvle/) or backend/
# ---------------------------------------------------------------------------
_BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_BACKEND_ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(_BACKEND_ROOT / ".env")

from app.config import get_settings  # noqa: E402
from app.db.models.llm_call import LLMCall  # noqa: E402
from app.db.session import dispose_engine, get_sessionmaker, init_engine  # noqa: E402
from app.llm.prompts.planner import PROMPT_NAME  # noqa: E402


_IDENT = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")


def _safe_pg_ident(name: str) -> str:
    if not _IDENT.fullmatch(name):
        raise ValueError(f"unexpected column identifier from introspection: {name!r}")
    return '"' + name.replace('"', "") + '"'


def _pct_linear(sorted_lens: list[int], pct: float) -> float | None:
    """Linear-interpolation percentile; pct in [0, 100]."""
    n = len(sorted_lens)
    if n == 0:
        return None
    idx = pct * (n - 1) / 100.0
    lo = math.floor(idx)
    hi = math.ceil(idx)
    if lo == hi:
        return float(sorted_lens[int(idx)])
    return sorted_lens[int(lo)] + (idx - lo) * (sorted_lens[int(hi)] - sorted_lens[int(lo)])


def _mean(vals: list[int]) -> float | None:
    if not vals:
        return None
    return sum(vals) / len(vals)


def _extract_notes(payload: Any) -> str | None:
    """Best-effort: parse dict or JSON string and read notes_for_synthesizer."""
    if payload is None:
        return None
    if isinstance(payload, memoryview):
        payload = payload.tobytes().decode()
    if isinstance(payload, bytes):
        payload = payload.decode()

    obj: dict[str, Any] | None = None
    if isinstance(payload, dict):
        obj = payload
    elif isinstance(payload, str):
        try:
            parsed = json.loads(payload)
            if isinstance(parsed, dict):
                obj = parsed
        except json.JSONDecodeError:
            return None
    else:
        return None

    if obj is None:
        return None
    v = obj.get("notes_for_synthesizer")
    if isinstance(v, str):
        return v
    return None


def _pick_payload_columns(pg_columns: list[tuple[str, str, str]]) -> list[str]:
    """Prefer obvious names, else any JSON/JSONB column on llm_calls."""
    preferred = []
    aliases = {"output_json", "response_json", "structured_output", "output", "parsed_output"}
    for name, data_type, udt_name in pg_columns:
        lname = name.lower()
        if lname in aliases:
            preferred.append(name)
    json_cols = []
    for name, data_type, udt_name in pg_columns:
        if data_type == "USER-DEFINED" and udt_name == "jsonb":
            json_cols.append(name)
        elif data_type in ("json", "jsonb"):
            json_cols.append(name)
    ordered = [*preferred]
    for c in json_cols:
        if c not in ordered:
            ordered.append(c)
    return ordered


async def main() -> None:
    print("Planner notes_for_synthesizer - empirical length calibration")
    print(f"prompt_name filter: {PROMPT_NAME} (from app.llm.prompts.planner)")
    print()

    settings = get_settings()
    init_engine(settings)
    try:
        session_maker = get_sessionmaker()
        async with session_maker() as session:
            intro = (
                await session.execute(
                    text(
                        """
                    SELECT column_name, data_type, udt_name
                    FROM information_schema.columns
                    WHERE table_schema = 'public' AND table_name = 'llm_calls'
                    ORDER BY ordinal_position
                    """
                    )
                )
            ).fetchall()
            colnames = [(r[0], r[1], r[2]) for r in intro]
            print("llm_calls columns (Postgres introspection):")
            for name, dt, ud in colnames:
                print(f"  - {name}: {dt} ({ud})")
            print()

            total = (
                await session.execute(
                    select(func.count()).select_from(LLMCall).where(LLMCall.prompt_name == PROMPT_NAME)
                )
            ).scalar_one()
            total = int(total)

            payload_cols = _pick_payload_columns(colnames)
            lengths: list[int] = []
            samples: list[tuple[int, str, str]] = []  # (len, text, llm_call_id)

            if not payload_cols:
                print(
                    "No JSON/JSONB column found on llm_calls - this matches the current "
                    "Fivvle schema: app.llm.client._log_llm_call() persists only audit "
                    "metadata (tokens, cost, latency), not structured LLM output."
                )
            else:
                print(f"Payload column candidate(s): {', '.join(payload_cols)}")
                for col in payload_cols:
                    ident = _safe_pg_ident(col)
                    q = text(
                        f'SELECT id, {ident} AS payload '
                        "FROM llm_calls WHERE prompt_name = :pn"
                    )
                    rs = await session.execute(q, {"pn": PROMPT_NAME})
                    for rid, blob in rs:
                        notes = _extract_notes(blob)
                        if notes is None:
                            continue
                        ln = len(notes)
                        lengths.append(ln)
                        samples.append((ln, notes, str(rid)))
                    break  # Use first actionable column only

            non_null = len(lengths)
            sorted_lens = sorted(lengths)
            longest = sorted(samples, key=lambda t: (-t[0], t[2]))[:5]

            print()
            print("--- Results ---")
            print(f"Total {PROMPT_NAME} planner LLMCall rows: {total}")
            print(f"Rows with non-null notes_for_synthesizer (decoded): {non_null}")

            if non_null == 0:
                print()
                print(
                    "Cannot compute min/median/mean/p90/p95/max - no decoded notes strings. "
                    "Collect more runs after persisting Planner JSON alongside LLM calls, "
                    "or probe another store that snapshots ResearchPlan."
                )
                return

            print(f"Min length (chars): {min(sorted_lens)}")
            median = _pct_linear(sorted_lens, 50.0)
            assert median is not None
            print(f"Median length: {median:.1f}")
            m = _mean(sorted_lens)
            assert m is not None
            print(f"Mean length: {m:.2f}")
            p90 = _pct_linear(sorted_lens, 90.0)
            p95 = _pct_linear(sorted_lens, 95.0)
            assert p90 is not None and p95 is not None
            print(f"P90 length: {p90:.1f}")
            print(f"P95 length: {p95:.1f}")
            print(f"Max length: {max(sorted_lens)}")
            print()
            print("Top 5 longest notes_for_synthesizer (full text):")
            for i, (_ln, text_val, cid) in enumerate(longest, 1):
                print(f"--- #{i} (llm_calls.id={cid}, chars={len(text_val)}) ---")
                print(text_val)
    finally:
        await dispose_engine()


if __name__ == "__main__":
    asyncio.run(main())
