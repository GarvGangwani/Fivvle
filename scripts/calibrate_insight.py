"""Calibration runner for insight_v1_cached against real Kimi k2.6.

Picks 5 experiments from the dev DB, injects synthetic AnalyticsAggregate
scenarios via monkeypatch, calls insight_service.generate_insight_report,
and captures: latency, cost (from LLMCall rows), success/failure, full
InsightReportOutput draft, and auto-checked quality signals.

Outputs:
    docs/calibration/runs/eval-insight-<timestamp>/
        summary.md             â€” auto-generated table + rubric template
        <scenario>_<id8>.json  â€” full draft + scenario + analytics per run

Pre-flight requirements (the script asserts these at startup):
    - MOONSHOT_API_KEY env var set
    - Settings.insight_provider == "kimi"
    - Settings.insight_model == "kimi-k2.6"

Run from project root:
    cd backend; uv run python ..\\scripts\\calibrate_insight.py; cd ..

Per planning doc Â§10, calibration gates:
    - â‰¥95% INSIGHT_READY (no failures)
    - Mean cost â‰¤ $0.15
    - p90 latency â‰¤ 30s
    - Zero hallucinated finding IDs
    - Rubric median â‰¥ 4/5 (manually scored in summary.md)
"""

from __future__ import annotations

import asyncio
import json
import os
import statistics
import sys
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from typing import Any
from unittest.mock import patch
from uuid import UUID

from sqlalchemy import select

_REPO_ROOT = Path(__file__).resolve().parent.parent
_BACKEND_ROOT = _REPO_ROOT / "backend"
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(_BACKEND_ROOT / ".env")

from app.config import get_settings  # noqa: E402
from app.db.models.experiment import Experiment  # noqa: E402
from app.db.models.llm_call import LLMCall  # noqa: E402
from app.db.session import get_sessionmaker, init_engine  # noqa: E402
from app.llm.prompts.insight import PROMPT_NAME  # noqa: E402
from app.schemas.validation_report import ValidationReport  # noqa: E402
from app.services.analytics_aggregator import LandingPageNotLiveError  # noqa: E402
from app.services.insight_service import (  # noqa: E402
    InsightCitationHallucinatedError,
    MissingValidationReportError,
    _compute_valid_finding_id_set,
    generate_insight_report,
)
from scripts.insight_calibration_scenarios import build_scenario_analytics  # noqa: E402


# ---------------------------------------------------------------------------
# CONFIG â€” adjust if dev DB doesn't have these experiment IDs
# ---------------------------------------------------------------------------

PICKS: list[tuple[str, str, str]] = [
    # (experiment_id, scenario_name, short_label)
    ("d47261f9-00e4-4264-8832-7a8b0667fd56", "warm_only_low_volume", "toddler-box"),
    ("c822a2f4-877b-4fff-9ed1-e1000b050940", "cold_high_volume_no_conversion", "vet-scribe"),
    ("fd237ba2-1f03-49c8-bc9e-0e44b41758af", "insufficient_data", "auto-marketplace"),
    ("abf721e0-8221-4983-a2bf-de079ec5203a", "bimodal_engagement", "cart-recovery"),
    ("f810fec6-6af3-4bb9-8b95-62e9a31b6fc1", "high_warm_high_conversion", "freelancer-loneliness"),
]


@dataclass
class CalibrationRun:
    label: str
    scenario: str
    experiment_id: str
    raw_idea_preview: str
    success: bool
    latency_seconds: float
    cost_usd: float
    recommendation_type: str | None
    cited_finding_id_count: int
    invalid_finding_ids: list[str] = field(default_factory=list)
    missing_source_type_count: int = 0
    what_would_change_chars: int = 0
    error: str | None = None
    json_path: str = ""


async def _run_one(
    db, exp_id: UUID, scenario: str, label: str, output_dir: Path
) -> CalibrationRun:
    exp_result = await db.execute(
        select(Experiment.raw_idea).where(Experiment.id == exp_id)
    )
    raw_idea = exp_result.scalar_one_or_none() or "(unknown)"

    aggregate = build_scenario_analytics(scenario, exp_id)
    fixture_mode_target = "app.services.insight_service.build_analytics_aggregate"

    async def _fake_aggregator(_db, _exp_id):
        return aggregate

    start = perf_counter()
    try:
        with patch(fixture_mode_target, _fake_aggregator):
            row = await generate_insight_report(db, exp_id)
            await db.commit()
        latency = perf_counter() - start

        cost_result = await db.execute(
            select(LLMCall)
            .where(LLMCall.experiment_id == exp_id)
            .where(LLMCall.phase == "insight")
            .where(LLMCall.prompt_name == PROMPT_NAME)
            .order_by(LLMCall.called_at.desc())
            .limit(2)
        )
        recent_calls = list(cost_result.scalars())
        cost = sum(float(c.cost_usd or 0) for c in recent_calls)

        draft: dict[str, Any] = row.raw_output or {}
        takeaways = draft.get("research_takeaways") or []
        cited_ids: list[str] = []
        missing_source_type = 0
        for tk in takeaways:
            cited_ids.extend(tk.get("cited_finding_ids") or [])
            if not tk.get("source_type"):
                missing_source_type += 1
        what_would_change = draft.get("what_would_change_this") or ""

        from app.db.models.validation_report import ValidationReport as VRRow  # noqa: PLC0415

        vr_row_result = await db.execute(
            select(VRRow).where(VRRow.experiment_id == exp_id)
        )
        vr_row = vr_row_result.scalar_one_or_none()
        valid_ids: set[str] = set()
        if vr_row and vr_row.raw_report:
            vr = ValidationReport.model_validate(vr_row.raw_report)
            valid_ids = _compute_valid_finding_id_set(vr)

        invalid_ids = sorted(set(cited_ids) - valid_ids)

        json_path = output_dir / f"{scenario}_{str(exp_id)[:8]}.json"
        json_path.write_text(
            json.dumps(
                {
                    "label": label,
                    "experiment_id": str(exp_id),
                    "scenario": scenario,
                    "raw_idea": raw_idea,
                    "analytics_used": aggregate.model_dump(mode="json"),
                    "draft": draft,
                    "cost_usd": cost,
                    "latency_seconds": latency,
                    "valid_finding_ids": sorted(valid_ids),
                    "invalid_finding_ids": invalid_ids,
                    "missing_source_type_count": missing_source_type,
                },
                indent=2,
            ),
            encoding="utf-8",
        )

        rec_type = draft.get("recommendation_type")
        if rec_type is not None and not isinstance(rec_type, str):
            rec_type = str(rec_type)

        return CalibrationRun(
            label=label,
            scenario=scenario,
            experiment_id=str(exp_id),
            raw_idea_preview=raw_idea[:100],
            success=True,
            latency_seconds=latency,
            cost_usd=cost,
            recommendation_type=rec_type,
            cited_finding_id_count=len(cited_ids),
            invalid_finding_ids=invalid_ids,
            missing_source_type_count=missing_source_type,
            what_would_change_chars=len(what_would_change),
            json_path=str(json_path.relative_to(output_dir.parent)),
        )

    except (
        MissingValidationReportError,
        LandingPageNotLiveError,
        InsightCitationHallucinatedError,
    ) as exc:
        await db.rollback()
        return CalibrationRun(
            label=label,
            scenario=scenario,
            experiment_id=str(exp_id),
            raw_idea_preview=raw_idea[:100],
            success=False,
            latency_seconds=perf_counter() - start,
            cost_usd=0.0,
            recommendation_type=None,
            cited_finding_id_count=0,
            error=f"{type(exc).__name__}: {exc}",
        )
    except Exception as exc:  # noqa: BLE001
        await db.rollback()
        return CalibrationRun(
            label=label,
            scenario=scenario,
            experiment_id=str(exp_id),
            raw_idea_preview=raw_idea[:100],
            success=False,
            latency_seconds=perf_counter() - start,
            cost_usd=0.0,
            recommendation_type=None,
            cited_finding_id_count=0,
            error=f"{type(exc).__name__}: {exc}",
        )


def _write_summary(runs: list[CalibrationRun], output_dir: Path) -> None:
    success_count = sum(1 for r in runs if r.success)
    total = len(runs)
    success_rate = (success_count / total * 100) if total else 0.0
    costs = [r.cost_usd for r in runs if r.success]
    latencies = [r.latency_seconds for r in runs if r.success]
    mean_cost = statistics.mean(costs) if costs else 0.0
    mean_latency = statistics.mean(latencies) if latencies else 0.0
    p90_latency = (
        sorted(latencies)[int(0.9 * (len(latencies) - 1))] if latencies else 0.0
    )
    total_invalid_ids = sum(len(r.invalid_finding_ids) for r in runs)
    total_missing_source_type = sum(r.missing_source_type_count for r in runs)

    gates = [
        ("â‰¥95% INSIGHT_READY", success_rate, ">= 95.0%", success_rate >= 95.0),
        ("Mean cost â‰¤ $0.15", mean_cost, "<= 0.15", mean_cost <= 0.15),
        ("p90 latency â‰¤ 30s", p90_latency, "<= 30.0s", p90_latency <= 30.0),
        ("Zero hallucinated IDs", total_invalid_ids, "== 0", total_invalid_ids == 0),
        (
            "All takeaways tagged with source_type",
            total_missing_source_type,
            "== 0",
            total_missing_source_type == 0,
        ),
    ]

    lines = [
        f"# Insight calibration â€” eval-insight-{output_dir.name.split('-', 2)[-1]}",
        "",
        f"Prompt: `{PROMPT_NAME}` (insight_v1_cached, pre-N=5 calibration)",
        f"Runs: {total}",
        "",
        "## Auto-gates",
        "",
        "| Gate | Observed | Target | Pass |",
        "|---|---|---|---|",
    ]
    for name, observed, target, passed in gates:
        lines.append(f"| {name} | {observed} | {target} | {'âœ…' if passed else 'âŒ'} |")
    lines.extend([
        "",
        "## Per-run summary",
        "",
        "| Label | Scenario | Success | Recommendation | Latency (s) | Cost ($) | Cited IDs | Invalid IDs | Missing source_type | WWCT chars |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ])
    for r in runs:
        lines.append(
            f"| {r.label} | {r.scenario} | {'âœ…' if r.success else 'âŒ'} | "
            f"{r.recommendation_type or 'â€”'} | {r.latency_seconds:.1f} | "
            f"{r.cost_usd:.4f} | {r.cited_finding_id_count} | "
            f"{len(r.invalid_finding_ids)} | {r.missing_source_type_count} | "
            f"{r.what_would_change_chars} |"
        )

    lines.extend([
        "",
        "## Aggregates (success runs only)",
        f"- Mean cost: ${mean_cost:.4f}",
        f"- Total cost: ${sum(costs):.4f}",
        f"- Mean latency: {mean_latency:.1f}s",
        f"- p90 latency: {p90_latency:.1f}s",
        "",
        "## Rubric â€” fill manually after reading each draft JSON",
        "",
        "Per planning doc Â§10. Score each dimension 1-5. Median â‰¥ 4 across all five",
        "dimensions and all five runs is the gate.",
        "",
        "| Label | Non-obvious | Useful | Synthesis accuracy | Justification | Forward-looking |",
        "|---|---|---|---|---|---|",
    ])
    for r in runs:
        lines.append(f"| {r.label} | _ | _ | _ | _ | _ |")

    lines.extend([
        "",
        "### Dimension definitions",
        "",
        "- **Non-obvious (1-5)** â€” Does the report surface something the founder couldn't have figured out from raw numbers? 1 = restates obvious facts. 5 = genuine insight.",
        "- **Useful (1-5)** â€” Does the report enable a concrete decision? 1 = vague. 5 = pointed action.",
        "- **Synthesis accuracy (1-5)** â€” Are [SYNTHESIZED] takeaways genuine cross-stream claims? 1 = label is decorative. 5 = labels are precise; [BEHAVIORAL]/[COGNITIVE]/[SYNTHESIZED] are used correctly.",
        "- **Justification quality (1-5)** â€” Are confidence_rationale fields meaningful? 1 = generic. 5 = each rationale references specific data.",
        "- **Forward-looking (1-5)** â€” Is what_would_change_this concrete and measurable? 1 = generic. 5 = specific threshold, specific data type, reachable.",
        "",
        "## Errors",
        "",
    ])
    for r in runs:
        if r.error:
            lines.append(f"- **{r.label}** ({r.scenario}): {r.error}")
    if all(r.success for r in runs):
        lines.append("None.")

    (output_dir / "summary.md").write_text("\n".join(lines), encoding="utf-8")


async def _delete_prior_insight_row(db, exp_id: UUID) -> None:
    """Delete any existing InsightReport for this experiment so calibration
    can re-run cleanly. v2 §6 says regen replaces the row; production service
    will eventually upsert, but for calibration a simple DELETE suffices."""
    from app.db.models.insight_report import InsightReport  # noqa: PLC0415
    from sqlalchemy import delete  # noqa: PLC0415
    await db.execute(delete(InsightReport).where(InsightReport.experiment_id == exp_id))
    await db.commit()

async def main() -> None:
    settings = get_settings()
    if settings.insight_provider != "kimi" or settings.insight_model != "kimi-k2.6":
        raise SystemExit(
            f"insight_provider/model mismatch: "
            f"got {settings.insight_provider}/{settings.insight_model}, "
            f"expected kimi/kimi-k2.6. Set env vars or fix Settings defaults."
        )
    if not os.environ.get("MOONSHOT_API_KEY"):
        raise SystemExit(
            "MOONSHOT_API_KEY env var is not set. Cannot run real calibration."
        )

    init_engine(settings)
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    output_dir = _REPO_ROOT / "docs" / "calibration" / "runs" / f"eval-insight-{timestamp}"
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\nCalibration run: {output_dir}\n")
    runs: list[CalibrationRun] = []
    sm = get_sessionmaker()
    for exp_id_str, scenario, label in PICKS:
        async with sm() as db:
            await _delete_prior_insight_row(db, UUID(exp_id_str))
            run = await _run_one(db, UUID(exp_id_str), scenario, label, output_dir)
            runs.append(run)
        ok = "OK" if run.success else "FAIL"
        print(
            f"  [{ok}] {label:<28} ({scenario:<32}) "
            f"latency={run.latency_seconds:5.1f}s cost=${run.cost_usd:.4f} "
            f"{run.error or ''}"
        )

    _write_summary(runs, output_dir)
    print(f"\nSummary: {output_dir / 'summary.md'}")


if __name__ == "__main__":
    asyncio.run(main())


