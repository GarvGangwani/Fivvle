# B4 — Insight Generator (v2 APPROVED)

Status: APPROVED — 2026-06-06. Supersedes v1 DRAFT (commit 85b3896).

## 1. Goal

Combine the validation report (cognitive) + page-view / waitlist data (behavioral) into a single structured `InsightReport` row with an AI recommendation (proceed / iterate / pivot / kill). Auto-archive abandoned experiments via cron.

Per USER_FLOW Stage 6.

The insight report is where the founder decides whether the product is worth paying for. Quality of reasoning, specificity of insight, and audit-trail trust are the primary investment areas. Surrounding feature scaffolding (notifications, progress UIs, confirmation modals) is deferred until real user data justifies it.

## 2. Scope (in)

1. **Insight generation Cloud Function** — HTTP, follows ADR 0020 dispatcher pattern.
2. **Auto-archive Cloud Function** — separate workload, cron-driven.
3. **Analytics aggregator service** — reads page_views, signups, landing_pages → produces derived metrics (not just counts).
4. **Pydantic sub-schemas** — strict contracts for every JSONB field, versioned with `schema_version: int = 1`.
5. **LLM prompt** — single-phase, `insight_v1_cached`, Kimi k2.6, zone A/B/C cache structure.
6. **Service layer** — orchestrates aggregator + LLM + DB write with citation/confidence validation.
7. **FastAPI endpoint** — `POST /experiments/{id}/generate-insight` (user-triggered, sync 15–30s).
8. **Re-generation** — unlimited, logged for cost monitoring.
9. **Tests** — unit + service-level integration with mocked LLM, parity with research engine coverage.

## 3. Architecture

Mirror research engine. `HttpDispatcher` already in place (ADR 0020). Add `POST /generate-insight` Cloud Function endpoint accepting `{experiment_id}`. FastAPI route enqueues via dispatcher; dispatcher chooses in-process (dev) or HTTP (prod).

Auto-archive: separate Cloud Function, Cloud Scheduler trigger, no HTTP body. Scans `LANDING_LIVE` experiments inactive past threshold and archives them. **Not** in the insight Cloud Function — different lifecycle, different failure semantics.

Single-phase LLM. No multi-phase pipeline. One call combining two structured inputs.

## 4. Data contract

### 4.1 Analytics aggregator output (input to LLM, derived not raw)

```python
class AnalyticsAggregate(BaseModel):
    schema_version: int = 1
    days_live: int
    total_page_views: int
    unique_visitors: int
    total_signups: int
    conversion_rate: float
    views_by_source: dict[str, int]
    signups_by_source: dict[str, int]
    conversion_rate_by_source: dict[str, float]   # derived
    warm_network_bias_index: float                 # derived — share of views from warm sources
    time_on_page_p50_seconds: int
    time_on_page_p90_seconds: int
    signups_by_day: list[int]                      # cohort timeline
    views_by_day: list[int]                        # cohort timeline
    drop_off_signals: dict[str, str]               # high-bounce indicators if detectable
    data_quality_notes: list[str]                  # e.g. "Bot-suspect traffic spike on day 3"
```

The aggregator is where most of the analytical work happens. The LLM only finds what we show it. Derived metrics > raw counts.

### 4.2 LLM output → InsightReport DB row

```python
class TrafficSummary(BaseModel):
    schema_version: int = 1
    narrative: str                                 # 2-3 sentence AI write-up
    headline_metric: str                           # e.g. "12% conversion from cold traffic"
    confidence: Literal["high", "medium", "low"]
    confidence_rationale: str
    source_type: Literal["BEHAVIORAL", "COGNITIVE", "SYNTHESIZED"]

class ConversionBySource(BaseModel):
    schema_version: int = 1
    per_source: dict[str, ConversionSourceCommentary]
    warm_network_bias_commentary: str
    confidence: Literal["high", "medium", "low"]
    confidence_rationale: str

class ResearchTakeaway(BaseModel):
    schema_version: int = 1
    claim: str
    cited_finding_ids: list[str]                   # must resolve to ValidationReport finding IDs
    source_type: Literal["BEHAVIORAL", "COGNITIVE", "SYNTHESIZED"]
    confidence: Literal["high", "medium", "low"]
    confidence_rationale: str

class InsightReportOutput(BaseModel):
    schema_version: int = 1
    traffic_summary: TrafficSummary
    conversion_by_source: ConversionBySource
    research_takeaways: list[ResearchTakeaway]     # 3-5 items
    recommendation_type: InsightRecommendation
    recommendation: str                             # 2-3 paragraph reasoning
    recommendation_confidence: Literal["high", "medium", "low"]
    recommendation_rationale: str
    what_would_change_this: str                     # forward-looking — what data would flip the verdict
```

`what_would_change_this` is critical. A "PIVOT" verdict without a forward-looking signpost is useless. "If cold-traffic signups grow above 5% in the next 14 days, this becomes PROCEED" is actionable.

### 4.3 Citation + confidence validation

After LLM returns, before DB write:
1. Every `cited_finding_ids` value MUST exist in the ValidationReport's findings. Reject + retry once if hallucinated.
2. Confidence labels must be present on every claim. Schema enforces.
3. Source-type labels must be present. Schema enforces.

## 5. LLM strategy

- **Provider/model:** Kimi k2.6 (per ADR 0018).
- **Prompt name:** `insight_v1_cached`.
- **Cache zones:** A = system + schema + instructions, B = ValidationReport JSON (large, cacheable across regenerations of the same experiment), C = AnalyticsAggregate (small, hot).
- **Cost target:** mean ≤ $0.15, ceiling $0.30.
- **Latency target:** mean ≤ 25s, p90 ≤ 30s.

### 5.1 Prompt obligations

Explicit instructions in Zone A:
- Every claim labeled with confidence + rationale.
- Every research_takeaway labeled with source_type (BEHAVIORAL / COGNITIVE / SYNTHESIZED) + cited finding IDs.
- `[SYNTHESIZED]` takeaways must genuinely combine both data streams — restating one or the other is a failure.
- `what_would_change_this` mandatory.
- Recommendations must reference specific evidence (numbers from analytics, finding IDs from research).
- No claims unsupported by either data stream. Strong null hypothesis: if neither stream supports a claim, omit it.

### 5.2 Strong vs weak examples in the prompt

Embed in Zone A:
- **Weak takeaway:** "Users are interested in the product." (No citation, no source, no specificity.)
- **Strong takeaway:** "[SYNTHESIZED — high] Cold-traffic conversion (8.3%) exceeds warm-network conversion (5.1%), inverting the typical bias documented in finding f4. This is unusual and suggests the value proposition lands without social proof — supports PROCEED if reproducible at higher volume."

## 6. Trigger model (user-triggered for v1)

- Dashboard "Generate insights" button, disabled until minimum data: `(≥10 page views) OR (≥1 signup) OR (≥7 days live)`.
- Tooltip when disabled: "Best results after 30+ page views or 5+ signups."
- Button label dynamic: "Generate insights from {N views, M signups, D days}."
- No confirmation modal. Button label IS the preview.
- Regenerable freely. Each regeneration replaces the existing `InsightReport` row.

System-triggered auto-firing is deferred. Today there are zero users. Threshold values can't be set without observation. Revisit after launch when real founder behavior is visible.

## 7. Status transitions

New states on the experiment status enum:
- `INSIGHT_GENERATING` — Cloud Function running
- `INSIGHT_READY` — row written, awaiting founder decision
- `INSIGHT_FAILED` — Cloud Function exhausted retries; manual retry available
- `COMPLETED` — founder clicked a decision button (Stage 6.3)
- `ARCHIVED` — auto-archive Cloud Function ran (or founder manually archived)

Alembic migration: add new enum values + appropriate constraints. No state machine validation logic changes; existing pattern applies.

## 8. Failure handling

- Auto-retry 3x with exponential backoff inside Cloud Function before transitioning to `INSIGHT_FAILED`.
- Citation validation failure (LLM cited a finding ID that doesn't exist) → 1 retry with explicit feedback, then fail.
- Analytics always visible on dashboard independent of insight status — founder is never staring at a blank page.
- `INSIGHT_FAILED` state shows: "Insight generation had trouble. Your analytics are below; click to retry." Manual retry button.

## 9. Auto-archive

- Trigger: Cloud Scheduler, daily at 02:00 UTC.
- Target: `LANDING_LIVE` experiments where `(no new page views in 14 days) AND (no founder activity in 30 days) AND (days_since_launch ≥ 60)`.
- At day 45 of inactivity: write a `warning_sent_at` timestamp on the experiment row. Frontend renders a banner: "This experiment has been quiet — archive it, or distribute the link to gather more data."
- At day 60: status → `ARCHIVED`.
- No email in v1. In-app banner only. Email deferred to whenever the notification system is built.

## 10. Calibration & launch gates (Tier-3)

Calibration on N=5 diverse experiments with varied data shapes (high-traffic-no-signups, warm-network-only, cold-traffic-dominant, near-zero-data, balanced).

Quantitative gates:
- `INSIGHT_READY` rate ≥ 95%
- Mean cost ≤ $0.15
- Cost ceiling ≤ $0.30
- p90 latency ≤ 30s
- Mean latency ≤ 25s
- Zero hallucinated finding IDs in citations (rejection at validation step counts; if final stored row contains an invalid ID, hard fail)

Rubric gates (human-scored 1–5, median ≥ 4 across N=5):
- **Non-obviousness** — Does the report tell founders something they couldn't have gotten by squinting at raw analytics?
- **Usefulness** — Could a founder act on this tomorrow?
- **Synthesis accuracy** — Do `[SYNTHESIZED]` takeaways genuinely combine both streams, or just restate one?
- **Justification quality** — Is the recommendation supported by specific evidence (numbers + finding IDs), not vibes?
- **Forward-looking value** — Is `what_would_change_this` specific, measurable, and reachable?

Rubric scoring lives in `docs/calibration/runs/<run-id>/insight-rubric.md`, pattern matches `docs/calibration/runs/2026-06-03-refinement-chatmode.md`.

## 11. Out of scope (v1)

- System-triggered auto-firing on threshold.
- Email notifications.
- In-app push/badge notification system.
- Frontend visualizations / charts (frontend renders JSONB).
- Stage 8 "Continue collecting" regeneration semantics (regeneration works in v1 but flow integration deferred).
- Multi-experiment insight comparison.
- Re-generation cost cap (revisit if abuse emerges).
- Decision confirmation modals (frontend can add later if regret data justifies).

## 12. Build order

Each step is its own commit with its own pytest pass. No skipping verification.

1. **Pydantic schemas** — `AnalyticsAggregate`, `InsightReportOutput`, all sub-schemas in `backend/app/schemas/insight.py`.
2. **Alembic migration** — new ExperimentStatus enum values.
3. **Analytics aggregator service** — `backend/app/services/analytics_aggregator.py`. Pure DB reads, derived metrics. Unit tests with fixture DB rows.
4. **`insight_v1_cached` prompt** — `backend/app/llm/prompts/insight.py`. Zone A/B/C structure. Strong/weak examples embedded. Commit as DRAFT.
5. **Insight generator service** — `backend/app/services/insight_service.py`. Orchestrates aggregator + LLM + citation validation + DB write.
6. **FastAPI endpoint** — `POST /experiments/{id}/generate-insight` + dispatcher integration.
7. **Cloud Function adapter** — mirrors research engine pattern.
8. **Auto-archive Cloud Function** — separate workload + Cloud Scheduler config.
9. **Calibration N=5** — gates per §10.
10. **ADR commit** — either extend ADR 0020 (Cloud Function HTTP dispatcher) or write `0021-insight-generator-architecture.md`. Decide at step 7.

## 13. References

- USER_FLOW.md Stage 6, Stage 8
- ADR 0009 (pluggable research dispatcher)
- ADR 0020 (Cloud Function HTTP dispatcher)
- ADR 0017 (quote guard pattern — model for citation validation)
- `backend/app/db/models/insight_report.py` (existing model)
- `backend/app/db/enums.py` `InsightRecommendation`
- `docs/calibration/runs/2026-06-03-refinement-chatmode.md` (rubric pattern)
- `.cursorrules` Quality Discipline + Build Order