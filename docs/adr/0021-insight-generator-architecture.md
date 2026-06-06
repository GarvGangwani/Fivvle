# ADR 0021 — Insight generator architecture

Status: Accepted (v1 calibrated and frozen 2026-06-06)
Supersedes: none
Related: ADR 0009 (pluggable dispatcher), ADR 0018 (Kimi k2.6 migration), ADR 0020 (Cloud Function HTTP dispatcher)

## Context

B4 of the product roadmap: the founder-facing InsightReport synthesizes cognitive validation (ValidationReport from the research pipeline) with behavioral validation (PageView + WaitlistSignup data from the published landing page) into a recommendation (`proceed` / `iterate` / `pivot` / `kill`), backed by labeled research takeaways and a forward-looking `what_would_change_this` signpost.

The insight LLM call sits between RESEARCH_READY → LANDING_LIVE → ANALYZING in the experiment lifecycle (`ARCHITECTURE.md` §6) and is triggered by the founder on demand.

## Decision

Seven-component build, mirroring established patterns where possible:

1. **Schemas** (`backend/app/schemas/insight.py`) — `AnalyticsAggregate` (derived behavioral metrics) and `InsightReportOutputDraft` / `InsightReportOutput` (LLM emission). Pydantic validators enforce confidence labels, source-type labels (`BEHAVIORAL` / `COGNITIVE` / `SYNTHESIZED`), and citation discipline. `schema_version: Literal[1]` everywhere; `extra="forbid"`.

2. **Analytics aggregator** (`backend/app/services/analytics_aggregator.py`) — pure DB reads. Computes `conversion_rate_by_source`, `warm_network_bias_index` (v1 substring-match heuristic against `WARM_SOURCE_TAG_PATTERNS`), per-day cohorts, time percentiles, `drop_off_signals`, `data_quality_notes`. PII-clean structlog (counts only).

3. **Prompt** (`backend/app/llm/prompts/insight.py`, name `insight_v1_cached`) — Zone A/B/C cache layout matching synthesizer/reader precedent. Zone A holds non-negotiable obligations (confidence labels, source-type labels, finding-ID citation grounding, INSUFFICIENT DATA PATHWAY, STRONG NULL HYPOTHESIS) plus strong/weak examples and the security notice. Zone B holds a compressed ValidationReport view (claims + confidence + explicit qN.fM IDs only — narrative fields stripped per the latency calibration; see §5 below). Zone C holds the AnalyticsAggregate JSON. Per ADR 0018: Kimi k2.6, temperature 0.6, thinking disabled.

4. **Service** (`backend/app/services/insight_service.py`) — orchestrates aggregator + LLM + citation validation + DB write. Citation validation: every `cited_finding_ids` entry must match a positional `qN.fM` ID derived from the source ValidationReport. One retry on hallucination with `<previous_attempt_feedback>` appended to the user prompt; second failure raises `InsightCitationHallucinatedError`. Persists `InsightReport` with `raw_output` JSONB (full payload) plus queryable scalar columns.

5. **Dispatcher abstraction** (`backend/app/dispatchers/`) — `InsightDispatcher` Protocol parallels `ResearchDispatcher`. `InProcessInsightDispatcher` runs the service in an `asyncio.create_task` background and transitions `Experiment.status` to `INSIGHT_READY` (success) or `INSIGHT_FAILED` (any exception). Factory `get_insight_dispatcher` selects based on `Settings.dispatcher_mode`; the `http` branch currently raises `NotImplementedError` (pending Step 7).

6. **FastAPI endpoint** (`backend/app/routers/experiments.py`) — `POST /{experiment_id}/generate-insight`, status 202. Auth + ownership return 404 on mismatch (AGENTS.md security). Status guard allows `LANDING_LIVE`, `INSIGHT_READY` (regen), `INSIGHT_FAILED` (retry); rejects others with 409. Min-data guard: ≥10 views OR ≥1 signup OR ≥7 days live (with helpful 409 detail when below). Transitions to `INSIGHT_GENERATING` + commits before `dispatcher.dispatch`. On `DispatchError`, rolls back to `INSIGHT_FAILED` and returns 502.

7. **Status flow** (ARCHITECTURE.md §6 updated in commit 1c24d17) — added `INSIGHT_GENERATING`, `INSIGHT_READY`, `INSIGHT_FAILED` as sub-states under the `ANALYZING` umbrella. Storage is `VARCHAR`, so no DDL migration was needed for the new states.

## Calibration outcome

`docs/calibration/runs/eval-insight-20260606T183516Z` (N=5 ideas × varied behavioral scenarios). All five auto-gates pass: 100% INSIGHT_READY, p90 latency 23.9s, mean cost ~$0.022/run from structured-log totals, zero hallucinated finding IDs across 49 citations, and full source-type tagging discipline. See VERDICT.md in that eval directory.

The latency gate required Zone B compression (commit f77d48c) — full `ValidationReport.model_dump_json` embedded 10-20k tokens per run, pushing p90 to 58.8s on large VRs in the prior eval (`eval-insight-20260606T180458Z`). Stripping evidence text, citations, competitors, and signals blocks from the embedded JSON (Zone B `_build_compressed_vr_view`) brought p90 to 23.9s with no loss of synthesis quality — those fields were never used by the insight obligations.

Prompt status: FROZEN as `insight_v1_cached`.

## Deferred (intentional)

- **Step 7: HttpInsightDispatcher + Cloud Function code + GCP deploy.** Defer until frontend integration justifies idle Cloud SQL cost. Today the factory raises `NotImplementedError` on `DISPATCHER_MODE=http` for insight. `in_process` mode is sufficient for prototype.
- **Step 8: Auto-archive Cloud Function.** No users yet → nothing to archive. Daily Cloud Scheduler workload to add post-launch. Independent of frontend.
- **Service-level upsert for regen.** v2 §6 calls for "regen replaces existing InsightReport row." Current service does plain INSERT, blocked by `ix_insight_reports_experiment_id` unique constraint on second run for the same experiment. Calibration script works around it via pre-delete; production service needs DELETE-then-INSERT or proper upsert before regen UX ships from the frontend.

## Known limits

- Calibration N=5 only exercised scenarios where the source VR's `overall_recommendation` was `iterate`. The cross-stream override pathway (behavioral data overturning a cognitive `proceed` / `kill` / `pivot` verdict) is not empirically validated. Re-calibrate once non-iterate VRs exist in the dev DB or by synthesizing fixtures.
- Kimi k2.6's structured-output reliability is moderate: ~40% of calibration runs hit `instructor_attempts=2` (one schema-validation retry). The latency gate accommodates the retry cost; production should monitor this rate.
- `WARM_SOURCE_TAG_PATTERNS` (twitter, linkedin, discord, slack, personal, founder, warm, friends, network) is a v1 heuristic with no real-founder tagging data behind it. Revisit after observed traffic.

## Consequences

- Backend MVP for insight is feature-complete in `in_process` dispatcher mode.
- Frontend prototype can integrate against a stable contract: `POST /experiments/{id}/generate-insight` (202 with `INSIGHT_GENERATING`) + `GET /experiments/{id}` polled for status transition + InsightReport content in the GET response when ready.
- Production deploy is gated on Step 7 (Cloud Function + URL config) and the regen-upsert fix. Step 8 is a maintenance feature with no launch dependency.
