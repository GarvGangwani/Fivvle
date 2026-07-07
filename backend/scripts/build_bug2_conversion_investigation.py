"""Build docs/BUG2_CONVERSION_INVESTIGATION.md — conversion mismatch investigation."""

from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
FRONTEND = REPO / "frontend"
BACKEND = REPO / "backend"
OUT = REPO / "docs" / "BUG2_CONVERSION_INVESTIGATION.md"

FENCE = "```"


def read(path: Path) -> str:
    raw = path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        return raw.decode("utf-8-sig")
    return raw.decode("utf-8")


def block(content: str, lang: str) -> str:
    return f"{FENCE}{lang}\n{content.rstrip()}\n{FENCE}\n\n"


def file_block(path: Path, lang: str | None = None) -> str:
    suffix = path.suffix.lstrip(".")
    use_lang = lang or ("tsx" if suffix in {"tsx", "ts"} else suffix)
    rel = path.relative_to(REPO).as_posix()
    return f"### `{rel}`\n\n{block(read(path), use_lang)}"


def extract_api_functions(path: Path, names: list[str]) -> str:
    lines = read(path).splitlines()
    chunks: list[str] = []
    for name in names:
        start = None
        for i, line in enumerate(lines):
            if line.startswith(f"export async function {name}"):
                start = i
                break
        if start is None:
            continue
        depth = 0
        end = len(lines)
        for j in range(start, len(lines)):
            if "{" in lines[j]:
                depth += lines[j].count("{")
            if "}" in lines[j]:
                depth -= lines[j].count("}")
            if j > start and depth == 0 and lines[j].strip() == "}":
                end = j + 1
                break
        chunks.append("\n".join(lines[start:end]))
    rel = path.relative_to(REPO).as_posix()
    return f"### `{rel}` (relevant exports)\n\n{block(chr(10).join(chunks), 'typescript')}"


def extract_types(path: Path, names: list[str]) -> str:
    lines = read(path).splitlines()
    chunks: list[str] = []
    for name in names:
        start = None
        for i, line in enumerate(lines):
            if line.startswith(f"export interface {name}"):
                start = i
                break
        if start is None:
            continue
        end = len(lines)
        for j in range(start + 1, len(lines)):
            if lines[j].startswith("export ") and not lines[j].startswith("export interface "):
                end = j
                break
        chunks.append("\n".join(lines[start:end]).rstrip())
    rel = path.relative_to(REPO).as_posix()
    return f"### `{rel}` (relevant types)\n\n{block(chr(10).join(chunks), 'typescript')}"


def extract_model_class(path: Path, class_name: str) -> str:
    lines = read(path).splitlines()
    start = None
    for i, line in enumerate(lines):
        if line.startswith(f"class {class_name}"):
            start = i
            break
    if start is None:
        return f"### {class_name}\n\n(not found in `{path.relative_to(REPO).as_posix()}`)\n\n"
    end = len(lines)
    for j in range(start + 1, len(lines)):
        if lines[j].startswith("class ") and not lines[j].startswith("class _"):
            end = j
            break
    return f"### {class_name}\n\n`{path.relative_to(REPO).as_posix()}`\n\n{block(chr(10).join(lines[start:end]), 'python')}"


def main() -> None:
    parts: list[str] = [
        "# Bug 2 — Conversion Rate Mismatch — Investigation Dump\n\n",
        "Context: CineFund experiment shows 4 views / 1 signup as 100% on /metrics "
        "and 25% on the dashboard card.\n\n",
        "## 1. Site A — /metrics tab\n\n",
        "**Primary component:** `frontend/components/insight/MetricsWidget.tsx` "
        "(rendered by `MetricsStagePanel` when metrics are unlocked)\n\n",
        "**Parent shell:** `frontend/components/insight/MetricsStagePanel.tsx`\n\n",
        "**Secondary display on same tab:** "
        "`frontend/components/distribution/DistributeSection.tsx` "
        "(distribution header stats)\n\n",
        "**Endpoint(s) called:** `GET /experiments/{id}/analytics` via "
        "`getExperimentAnalytics()` in `frontend/lib/api.ts`\n\n",
        "**Also called (access gate, not conversion):** "
        "`GET /experiments/{id}/metrics-access`, "
        "`POST /experiments/{id}/unlock-metrics`\n\n",
        "**Conversion expression (MetricsWidget):** "
        "`formatPercent(analytics.conversion_rate)` where "
        "`formatPercent(rate) => \\`${(rate * 100).toFixed(1)}%\\``\n\n",
        "**Conversion expression (DistributeSection):** same — "
        "`formatPercent(analytics.conversion_rate)` with identical helper\n\n",
        "**Calculation location:** Backend pre-computes `conversion_rate` (0–1 ratio); "
        "frontend multiplies by 100 for display only.\n\n",
        file_block(FRONTEND / "components/insight/MetricsStagePanel.tsx"),
        file_block(FRONTEND / "components/insight/MetricsWidget.tsx"),
        file_block(FRONTEND / "components/distribution/DistributeSection.tsx"),
        extract_api_functions(
            FRONTEND / "lib/api.ts",
            ["getExperimentAnalytics", "getMetricsAccess", "unlockMetrics"],
        ),
        extract_types(
            FRONTEND / "lib/types.ts",
            ["ExperimentAnalytics", "SignupLocationBucket"],
        ),
        "## 2. Site B — Dashboard card\n\n",
        "**Primary component:** `frontend/components/dashboard/ProjectCard.tsx`\n\n",
        "**List page:** `frontend/components/dashboard/DashboardContent.tsx` "
        "calls `listExperiments()`\n\n",
        "**Endpoint(s) called:** `GET /experiments` via `listExperiments()` "
        "in `frontend/lib/api.ts`\n\n",
        "**Fields read:** `experiment.card_stats.page_views`, "
        "`experiment.card_stats.waitlist_signups`\n\n",
        "**Conversion expression:** "
        "`formatConversion(stats.page_views, stats.waitlist_signups)` where "
        "`formatConversion(views, signups) => views <= 0 ? \"—\" : "
        "`\\`${((signups / views) * 100).toFixed(1)}%\\``\n\n",
        "**Calculation location:** Frontend divides signups by page_views "
        "(raw row counts from API); no `conversion_rate` field on list response.\n\n",
        file_block(FRONTEND / "components/dashboard/DashboardContent.tsx"),
        file_block(FRONTEND / "components/dashboard/ProjectCard.tsx"),
        extract_api_functions(FRONTEND / "lib/api.ts", ["listExperiments"]),
        extract_types(
            FRONTEND / "lib/types.ts",
            ["ExperimentCardStats", "ExperimentSummary"],
        ),
        "## 3. Backend routes\n\n",
        file_block(BACKEND / "app/routers/experiments.py"),
        "## 4. Backend services\n\n",
        file_block(BACKEND / "app/services/analytics_aggregator.py"),
        file_block(BACKEND / "app/services/experiment_dashboard_stats.py"),
        "### `backend/app/schemas/api_responses.py` (AnalyticsResponse)\n\n",
        block(
            "\n".join(
                read(BACKEND / "app/schemas/api_responses.py").splitlines()[104:119]
            ),
            "python",
        ),
        "### `backend/app/schemas/experiment.py` (ExperimentCardStats, ExperimentListItemResponse)\n\n",
        block(
            "\n".join(
                read(BACKEND / "app/schemas/experiment.py").splitlines()[89:101]
            ),
            "python",
        ),
        "## 5. Models\n\n",
        extract_model_class(BACKEND / "app/db/models/page_view.py", "PageView"),
        extract_model_class(BACKEND / "app/db/models/waitlist_signup.py", "WaitlistSignup"),
        extract_model_class(BACKEND / "app/db/models/experiment.py", "Experiment"),
        extract_model_class(BACKEND / "app/db/models/landing_page.py", "LandingPage"),
        extract_model_class(
            BACKEND / "app/db/models/landing_page_v2.py", "LandingPageV2Spec"
        ),
        "## 6. Shared metrics/analytics service (if exists)\n\n",
        "`backend/app/services/analytics_aggregator.py` — included in §4 above. "
        "This is the single backend module that computes `conversion_rate` "
        "(`total_signups / unique_visitors`, where `unique_visitors` is "
        "COUNT DISTINCT `ip_address` with fallback to total row count). "
        "No separate `metrics_service.py` or `analytics_service.py` exists.\n\n",
        "## Notes\n\n",
        "1. **Site A (/metrics tab):** Conversion is **pre-computed on the backend** "
        "and returned as `conversion_rate` (float 0–1) on `GET /experiments/{id}/analytics`. "
        "The frontend displays it via `formatPercent(analytics.conversion_rate)` "
        "which multiplies by 100.\n\n",
        "2. **Site B (dashboard card):** Conversion is **computed in the frontend** "
        "from two raw count fields on `GET /experiments` → `card_stats`. "
        "No `conversion_rate` field exists on the list response.\n\n",
        "3. **Site A frontend expression (verbatim):** "
        "`return \\`${(rate * 100).toFixed(1)}%\\`;` "
        "applied to `analytics.conversion_rate` in MetricsWidget and DistributeSection.\n\n",
        "4. **Site B frontend expression (verbatim):** "
        "`return \\`${((signups / views) * 100).toFixed(1)}%\\`;` "
        "in `formatConversion(stats.page_views, stats.waitlist_signups)`.\n\n",
        "5. **Backend assignment of Site A field:** `get_experiment_analytics` in "
        "`backend/app/routers/experiments.py` sets "
        "`conversion_rate=aggregate.conversion_rate` where "
        "`aggregate = await build_analytics_aggregate(...)`. "
        "Inside `build_analytics_aggregate`: "
        "`conversion_rate = _clamp01(total_signups / unique_visitors)` "
        "with `unique_visitors = len(non_null_ips)` "
        "(distinct `PageView.ip_address` values; falls back to `total_page_views` "
        "if all IPs are null).\n\n",
        "6. **Endpoints:** Site A uses `GET /experiments/{id}/analytics`. "
        "Site B uses `GET /experiments` (embedded `card_stats`). "
        "Different endpoints.\n\n",
        "7. **PageView deduplication:** The `PageView` model has no "
        "`visitor_id`, `session_id`, or `fingerprint` field — only `ip_address`. "
        "The analytics aggregator deduplicates visitors by distinct `ip_address` "
        "for `unique_visitors` and thus overall `conversion_rate`. "
        "Per-source `conversion_rate_by_source` uses **raw view row counts** "
        "(`views_by_source`), not unique IPs. "
        "The dashboard card stats query uses `func.count(PageView.id)` — "
        "**no deduplication**, all rows counted.\n\n",
        "8. **Multiply-by-100 asymmetry:** Both sites multiply a **ratio** by 100 "
        "for display. Site A's ratio is `signups / unique_visitors` (backend). "
        "Site B's ratio is `signups / page_views` (frontend). "
        "The bug for 4 views / 1 signup: if `unique_visitors=1` (one distinct IP) "
        "backend returns `conversion_rate=1.0` → **100%** on metrics; "
        "dashboard computes `1/4*100` → **25%**.\n\n",
        "9. **Other asymmetries:** "
        "(a) Numerator/denominator mismatch: unique visitors vs total page view rows. "
        "(b) `total_page_views` on metrics tab shows raw count (4) while conversion "
        "uses unique visitors (1) — the headline numbers can look inconsistent. "
        "(c) Per-source breakdown on metrics uses views/signups row counts, "
        "not unique IPs. "
        "(d) Both paths require `metricsAnalysis` unlock for live experiments, "
        "but use different backend code paths. "
        "(e) `LandingPageV2Spec` is not referenced by either metrics endpoint; "
        "analytics reads `LandingPage.live_at` only.\n",
    ]

    OUT.write_text("".join(parts), encoding="utf-8")
    print(f"Wrote {OUT} ({OUT.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
