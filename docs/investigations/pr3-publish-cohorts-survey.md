# PR-3 Publish Cohorts Survey

**Date:** 2026-07-26 · Read-only · Complements cascade / PR-1 / PR-2 surveys (not re-done)

---

### 1. Publish + republish paths

**First publish** — `experiments.py` L1860–L1904 `POST …/landing-page/publish`:
- Requires `LANDING_DRAFT` + landing row.
- Sets `landing_page.live_at = now` (L1892) and `status = LANDING_LIVE` (L1893).
- Calls `notify_live_landing_page_changed`; returns slug + public URL.

**No distinct republish endpoint.** Live-page regen reuses `POST …/generate-landing-page` (`experiments.py` L1014–L1024): `was_live = (status == LANDING_LIVE)` → dispatcher.

**Regen-while-live** — `in_process_landing_page.py` L70–L95:
```python
success_status = LANDING_LIVE if was_live else LANDING_DRAFT
failure_status = LANDING_LIVE if was_live else RESEARCH_READY
# … generate_landing_page → commit → _transition_status(…, success_status)
```
Does **not** touch `live_at`.

**Every `live_at` write:** only `experiments.py` L1892 (`landing_page.live_at = now` on publish). Other hits are reads (`public.py` L151, metrics/threshold selects).

---

### 2. Analytics ingest

**Waitlist** — `public.py` L210–L236: `_fetch_live_landing_page` → `record_waitlist_signup(…, experiment_id=experiment.id, email, source_tag, client_ip)`. No `landing_page_id`.

**Page view** — `public.py` L245–L277: writes `PageView(experiment_id, source_tag, time_on_page_sec, user_agent, ip_address, referrer)`. Identified by experiment via slug→live landing join. Soft-no-op if slug invalid / not live.

**Models (experiment-scoped only):**

| Table | Columns | Indexes | FK |
|-------|---------|---------|-----|
| `page_views` (`page_view.py`) | id, experiment_id, source_tag, ts, time_on_page_sec, user_agent, ip_address, referrer | experiment_id, source_tag | `experiments.id` **CASCADE** |
| `waitlist_signups` (`waitlist_signup.py`) | id, experiment_id, email, source_tag, ip_address, geo_*, ts | experiment_id, source_tag | `experiments.id` **CASCADE** |

No `landing_page_id` / publish FK today.

---

### 3. Insight / other readers

`build_analytics_aggregate` (`analytics_aggregator.py` L96–L130): requires `LandingPage.live_at`; loads **all** `PageView` / `WaitlistSignup` for `experiment_id` (ordered by `ts`). No date-range / cohort filter. `days_live` from `now - live_at`. Day arrays span `days_live`.

`insight_service.generate_insight` L220: `analytics = await build_analytics_aggregate(db, experiment_id)`.

**Other `experiment_id`-only readers:** `insight_threshold.py` (counts); `experiment_service` canvas metrics (page_view count); `experiment_dashboard_stats.py` (counts); `chat_discussion_context.py` (aggregate + counts); `universal_chat_tools.py` (counts + by source); `experiments.py` threshold preview (~L801–808), GET analytics L2016, waitlist list/export (~L2071+).

---

### 4. Migration history / volume

- Created: `20260511_1422_648fe71ca40e_initial_schema_…` — `page_views` / `waitlist_signups` with experiment CASCADE.
- Geo: `20260617_1200_e4b7c2a1f9d3_waitlist_signup_geo_fields.py`.
- Grep migrations for `publish` / `cohort` / `session` as analytics concepts: **NOT FOUND** (only slug-at-publish comments).
- Confirm: experiment-scoped only; no `landing_page_id`.

---

### 5. Founder republish UI

- `grep republish|Republish|new cohort` in `frontend/`: **NOT FOUND**.
- Publish button: `DeepDiveOverlay.tsx` L147–L185 — label `"Publish landing page"` / `"Live at /{slug}"`; enabled only when `status === "LANDING_DRAFT"`; when live, click copies link (not republish). Also `PublishConfirmDialog.tsx`, `EditorLayout.tsx` Publish tab (~L536, L639).
- Launch state: `LaunchStagePanel` `isLive` from `page.live_at`; preview `live`/`draft`/`generate`; overlay uses `launchLanding?.isLive` + status.

---

### 6. Signal / metrics UI

- Readers: `MetricsWidget.tsx`, `useExperimentAnalytics.ts`, `DistributeSection.tsx`, Signal panels via `getExperimentAnalytics` → totals + by-source + locations + days + threshold.
- Publish-cohort / analytics-session concept in Signal: **NOT FOUND** (`first_cohort_hint` is LaunchKit marketing copy only).
- Insight UI: totals, conversion, per-source breakdowns, geo buckets, days_live — not a separate time-series chart component beyond day arrays in API payload for LLM.

---

### 7. Metrics API shape

`GET /experiments/{id}/analytics` → `AnalyticsResponse` (`api_responses.py` L118–L133): `total_page_views`, `total_signups`, `unique_visitors`, `conversion_rate`, `views_by_source`, `signups_by_source`, `conversion_rate_by_source`, `signups_by_location`, `days_live`, `insight_threshold_met`, `insight_progress`. Built from full-experiment `AnalyticsAggregate` (`insight.py` L72–L99) + threshold.

---

### 8. Data migration surface

- Whether local/staging DBs already have live-page telemetry: **unknown from repo** — migration must adopt orphan rows into synthetic cohort #1 either way.
- Downgrades: project writes **real** `downgrade()` (e.g. PR-1/PR-2 `op.drop_column`); not `pass`.

---

### 9. Tests needing updates

| File | Analytics / publish facts |
|------|---------------------------|
| `test_insight_service.py` | Seeds landing `live_at`, `PageView` / `WaitlistSignup` by experiment; asserts aggregate / insight path |
| `test_generate_insight_endpoint.py` | Seeds `live_at` + N page_views / signups / days for threshold gates |
| `test_analytics_aggregator.py` | Full aggregate math over experiment-scoped rows |
| `test_waitlist_geo.py` | `record_waitlist_signup` |
| `test_public_landing_accessibility.py` | live fetch; no row writes |
| `test_in_process_landing_page.py` | generation status; **no** `was_live` / publish assertions found |
| `test_landing_page_service.py` | persist/stamps; not publish cohorts |

---

### 10. FK cascade patterns

- Dominant child→parent: `ondelete="CASCADE"` (landing_pages, validation_reports, page_views, waitlist_signups, launch_kits→landing_pages, etc.).
- Soft links: `SET NULL` (llm_calls.experiment_id, some chat FKs).
- Analytics → experiment: **CASCADE** (models + initial migration). New `landing_page_publishes → landing_pages` would match CASCADE peers (`launch_kits.landing_page_id` already CASCADE).
