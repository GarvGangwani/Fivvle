# B4 — Insight Generator (v1 DRAFT)

Status: DRAFT — open questions §6 must be resolved before v2 APPROVED.

## 1. Goal

Combine the validation report (cognitive) + page-view / waitlist data (behavioral) into a single structured `InsightReport` row with an AI recommendation (proceed / iterate / pivot / kill), and auto-archive completed experiments via cron.

Per USER_FLOW Stage 6.

## 2. Scope (in)

1. **Insight generation Cloud Function** — HTTP, follows ADR 0020 dispatcher pattern (in_process / http modes).
2. **Auto-archive Cloud Function** — separate workload, cron-driven, scans experiments past retention threshold.
3. **Pydantic schemas** — `InsightReportInput`, `InsightReportOutput` (mirrors DB JSONB fields).
4. **LLM prompt** — single-phase, `insight_v1_cached`, Kimi k2.6.
5. **Service layer** — read validation report + analytics aggregates → LLM call → write `InsightReport` row.
6. **FastAPI endpoint** — `POST /experiments/{id}/generate-insight` (user-triggered, sync 15–30s per Stage 6 UX).
7. **Tests** — unit + service-level integration with mocked LLM, parity with research engine coverage.

## 3. Architecture

- **Pattern:** Mirror research engine. `HttpDispatcher` already in place (ADR 0020). Add a second Cloud Function endpoint `POST /generate-insight` accepting `{experiment_id}`. FastAPI route enqueues via dispatcher; dispatcher chooses in-process (dev) or HTTP (prod).
- **Auto-archive:** Separate Cloud Function, Cloud Scheduler trigger, no HTTP body. Scans for `COMPLETED` experiments past retention threshold and archives them (status → `ARCHIVED`).
- **No multi-phase pipeline.** Insight is one LLM call combining two structured inputs. Unlike research engine which has 5 phases.

## 4. Data contract

### Inputs to LLM
- `ValidationReport` (existing schema, full structured object)
- Analytics aggregates (new — fetched from `page_views`, `signups`, `landing_pages`):
  - `total_page_views: int`
  - `unique_visitors: int`
  - `total_signups: int`
  - `conversion_rate: float`
  - `views_by_source: dict[str, int]` (warm-network / cold / search / social etc — source tag breakdown)
  - `signups_by_source: dict[str, int]`
  - `time_on_page_p50_seconds: int`
  - `time_on_page_p90_seconds: int`
  - `days_live: int`

### Output (LLM → `InsightReport` row)
- `traffic_summary` (JSONB) — aggregated metrics, AI-written 2-3 sentence narrative
- `conversion_by_source` (JSONB) — per-source breakdown + AI commentary on warm-network bias
- `research_takeaways` (JSONB) — 3-5 bullets distilling the validation report through the lens of observed behavior
- `recommendation` (Text) — 2-3 paragraph reasoning
- `recommendation_type` (Enum) — proceed / iterate / pivot / kill
- `generated_at` (Timestamp, server default)

## 5. LLM strategy

- **Provider/model:** Kimi k2.6 (consistent with research engine, per ADR 0018).
- **Prompt name:** `insight_v1_cached`.
- **Caching layout:** Zone A (system instructions + schema), Zone B (validation report — large, cacheable across regenerations), Zone C (analytics aggregates — small, hot).
- **Cost ceiling:** $0.20 per run (research engine is $0.59 mean; insight is smaller — one call, no Tavily, no parallel fan-out).
- **Latency ceiling:** 30s per Stage 6 UX ("sync if user-triggered, async if system-triggered").
- **Calibration:** N=3 runs on diverse experiments before launch gate. Real-API smoke + rubric scoring.

## 6. Open questions (must resolve before v2 APPROVED)

### Q1 — Trigger model
USER_FLOW Stage 6 says "sync if user-triggered, async if system-triggered." For v1, propose: **user-triggered only.** Founder clicks "Generate insights" on dashboard once they're ready. Threshold-driven auto-trigger deferred to a later milestone. Confirm or override.

### Q2 — Auto-archive criteria
Stage 6.3 says experiment is archived when founder clicks a decision button. So what does the auto-archive Cloud Function archive? Candidates:
- (a) `COMPLETED` experiments past N days (cleanup of decided experiments).
- (b) `LANDING_LIVE` experiments inactive past N days (no new signups + no founder activity → assume abandoned).
- (c) Both, with different thresholds.

Pick one. Need retention windows (7 / 30 / 90 days).

### Q3 — Status transitions
New states needed on the experiment status enum:
- `INSIGHT_GENERATING` (during Cloud Function run)
- `INSIGHT_READY` (insight row written, awaiting founder decision)
- `COMPLETED` (founder clicked a decision button)
- `ARCHIVED` (auto-archive Cloud Function ran)

Confirm enum names. Migration required.

### Q4 — Failure handling
If the LLM call fails after retries, what happens?
- (a) Hard error, status → `INSIGHT_FAILED` (matches research engine pattern).
- (b) Partial write — analytics aggregates persisted, recommendation null, founder sees "AI write-up unavailable, here are the raw numbers."

Recommend (a) for parity. Confirm.

### Q5 — Zero-data case
Common during MVP: founder publishes landing page, zero or near-zero traffic. What does the recommendation say? Propose: explicit "insufficient behavioral data" pathway in the prompt — recommendation_type is whatever the validation report said, with a research_takeaway noting the behavioral signal is missing.

### Q6 — Schema for JSONB fields
`traffic_summary`, `conversion_by_source`, `research_takeaways` are typed `dict | None` at DB. Do we want Pydantic sub-schemas for each (stronger contract) or keep them loose? Recommend Pydantic sub-schemas matching what the frontend will render. Confirm.

### Q7 — Calibration & launch gate
Propose Tier-3 gates analogous to research engine:
- `INSIGHT_READY` rate ≥ 95%
- Mean cost ≤ $0.15
- Mean latency ≤ 25s
- Zero hallucinated source references (citations in `research_takeaways` must resolve to actual `ValidationReport` citations — no new URLs introduced)

Confirm.

## 7. Out of scope (v1)

- Email notifications (Stage 6.1) — deferred to B5.
- In-app notification UI — frontend.
- Stage 8 "Continue collecting" regeneration flow.
- Multi-experiment insight comparison.
- Visualizations / charts — frontend renders JSONB.
- Localization.

## 8. Build order (proposed)

1. Define Pydantic schemas (input aggregates + LLM output + DB row shape).
2. Add new ExperimentStatus enum values + Alembic migration.
3. Write `insight_v1_cached` prompt (zones A/B/C); commit as DRAFT.
4. Analytics aggregator service (reads page_views, signups; returns the aggregate object).
5. Insight generator service (orchestrates aggregator + LLM + DB write).
6. FastAPI endpoint `POST /experiments/{id}/generate-insight` + dispatcher integration.
7. Cloud Function adapter (mirrors research engine).
8. Auto-archive Cloud Function (separate, cron-driven).
9. Calibration N=3, gate against §6.Q7 thresholds.
10. Commit ADR for insight generator architecture (or extend ADR 0020).

Each step lands as its own commit with its own pytest pass.

## 9. References

- USER_FLOW.md Stage 6, Stage 8
- ADR 0009 (pluggable research dispatcher)
- ADR 0020 (Cloud Function HTTP dispatcher)
- `backend/app/db/models/insight_report.py` (existing model)
- `backend/app/db/enums.py` `InsightRecommendation`
- `.cursorrules` Build Order: "B4. Insight generation Cloud Function ... Includes the auto-archive Cloud Function (cron-driven)."