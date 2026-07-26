# PR-2 Public Accessibility + Evidence→Launch Edge Survey

**Date:** 2026-07-26 · Read-only · Complements cascade + PR-1 surveys (not re-done here)

---

### 1. Public accessibility gates today

**Canonical set + helpers** — `backend/app/utils/landing_page_public.py` L7–L33:

```python
PUBLIC_LANDING_PAGE_STATUSES = frozenset({
    LANDING_LIVE, INSIGHT_GENERATING, INSIGHT_READY, INSIGHT_FAILED,
    COMPLETED, ANALYZING,
})
# ARCHIVED excluded.
def is_public_landing_page_accessible(status) -> bool:
    return status in PUBLIC_LANDING_PAGE_STATUSES
```

| Consumer | File:lines | Predicate | Protects |
|----------|------------|-----------|----------|
| `_fetch_live_landing_page` | `routers/public.py` L121–L140 | `LandingPage.live_at.is_not(None)` **AND** `Experiment.status.in_(PUBLIC_LANDING_PAGE_STATUSES)` | Shared loader for GET `/e/{slug}`, waitlist POST, page-view ingest |
| `get_public_landing_page` | `public.py` L176–L197 | via `_fetch_live_landing_page` | Public SSR payload (404 if miss) |
| `submit_waitlist_signup` | `public.py` L200–L216 | same | Waitlist accept |
| `record_page_view` | `public.py` L235–L254 | same; miss → soft `"recorded"` (no write) | Analytics ingest |
| `_ensure_metrics_access_allowed` | `experiments.py` L216–L226 | `is_public_landing_page_accessible(status)` | Founder metrics unlock (not public serve) |

**Not status-gated for serve:** upload file GETs under `/uploads/landing-*` (filename/path only).

**Frontend public path:** `frontend/app/e/[slug]/page.tsx` — no status check; `fetchPublishedPage(slug)` → `GET {API}/e/{slug}` (`lib/published-page.ts` L39–L55). 404 → `notFound()`. ISR `revalidate = 60`. Status gate is entirely backend.

Other frontend `LANDING_LIVE` hits are founder lifecycle (canvas, Signal, Launch tabs) — not the public renderer.

---

### 2. Evidence rerun → status demotion

**Allowed sources** — `dispatch_service.py` L20–L30 `_EVIDENCE_RERUN_ALLOWED`: `RESEARCH_READY`, `RESEARCH_FAILED`, `LANDING_GENERATING`, `LANDING_DRAFT`, `LANDING_LIVE`, `INSIGHT_GENERATING`, `INSIGHT_READY`, `INSIGHT_FAILED`.

**Route:** `POST /experiments/{id}/evidence/rerun` — `experiments.py` L685–L730 → `transition_to_researching_and_dispatch(..., EVIDENCE_RERUN)` sets `RESEARCHING` (L65–L68).

**Success land:** `research_engine_service.py` L547–L560 → `_set_status(..., RESEARCH_READY)`.

**Confirm prior finding:** rerun from `LANDING_LIVE` → success `RESEARCH_READY` while landing row kept. `live_at` assignment sites: only publish sets it (`experiments.py` L1884 `landing_page.live_at = now`). Grep for `live_at =` elsewhere: **no null-out** on Evidence rerun / research write. Landing row not deleted (cascade survey). Public set excludes `RESEARCH_READY` → `_fetch_live_landing_page` 404s despite `live_at` set.

---

### 3. Other status-gated landing behaviors

| Check | File:lines | Allowed | Protects | Gate type for PR-2 |
|-------|------------|---------|----------|-------------------|
| Public serve / waitlist / page-view | `public.py` L131–L132 | `PUBLIC_LANDING_PAGE_STATUSES` + `live_at` | Reachability + ingest | → **artifact** (`live_at` + not archived) per PR-2 scope |
| Metrics unlock | `experiments.py` L216–L226 | same public set | Founder paid metrics | Founder lifecycle (today tied to public set) |
| PATCH landing + logo/section uploads | `_ensure_landing_page_editable` L197–L213; `LANDING_PAGE_EDITABLE_STATUSES` = draft ∪ public set | Edit copy/design | **Stay status-gated** (founder lifecycle; blocked mid-`LANDING_GENERATING` / archived) |
| Publish | `experiments.py` L1870–L1874 | `LANDING_DRAFT` only | First publish → `live_at` + `LANDING_LIVE` | **Stay status-gated** |
| Generate landing | `experiments.py` ~L992–L1001 | `RESEARCH_READY` / `LANDING_DRAFT` / `LANDING_LIVE` | Regen dispatch | Founder lifecycle |
| Generate insight | ~L864 | `LANDING_LIVE` / `INSIGHT_*` | Insight start | Founder lifecycle |
| Launch kit generate | `launch_kit.py` L61–L68 | draft/live/insight band | Kit dispatch | Founder lifecycle |
| GET landing-page | L1579–L1604 | ownership only | Founder fetch | Row existence |

Preview iframe loads `/e/{slug}` — inherits public gate (not a separate status check).

---

### 4. page_views / waitlist ingest

Both use `_fetch_live_landing_page` (`public.py` L214, L252). Same dual gate: `live_at` + status ∈ public set.

After Evidence rerun → `RESEARCH_READY`: public GET 404s; waitlist 404s; page-view returns 202 `"recorded"` **without inserting** (L252–L254). Ingest blocked by the same status demotion that 404s the page.

---

### 5. Landing generator input — raw_report vs edited_doc

**v1** — `landing_page_service.py` L308–L321:

```python
# parse raw_report JSONB only
return ValidationReport.model_validate(row.raw_report)
```

Sole content read in that file; passed into strategist prompt (`generate_landing_page` L798+). Persist stamps `spark_version_id` / `refined_idea_version` only (L738–L762) — no edited_doc stamp.

**v2** — `landing_page_v2_service.py` `_load_validation_report` L134–L146: also `ValidationReport.model_validate(row.raw_report)`. Out of PR-2 scope; note for PR-3.

**`edited_doc` shape:** ProseMirror JSON (`validation_report.py` L63–L68: “ProseMirror-doc JSON blob”). Renderer: `render_report_to_prosemirror_doc` (`validation_report_editor.py` L94+). **No** backend helper flattens `edited_doc` → `ValidationReport` / prose for landing. Launch-kit `edited_doc` is a different table (`launch_kits`).

---

### 6. Landing `edited_doc` stamp — column landscape

**`landing_pages`** (`landing_page.py` L22–L104): id, experiment_id, template/palette/font/density, enabled_sections, headline/subheadline/problem/solution/cta_*, features/how_it_works/faq/founder_bio, copy_json, page_json, slug, **live_at**, last_revalidated_at, **spark_version_id**, **refined_idea_version**. **No `edited_doc_version`.**

**`landing_page_v2_specs`** (`landing_page_v2.py` L20–L61): id, experiment_id, spec_json, generation_status/phase, error_detail, timestamps. No spark/riv/edited_doc stamps. PR-2 = v1 only.

---

### 7. Evidence PATCH — bump hook site

Handler: `experiments.py` L1148–L1172 `patch_validation_report_edited_doc` → `apply_edited_doc_patch` → commit.

Write site: `validation_report_editor.py` L256–L273:

```python
report.edited_doc = doc
report.edited_doc_version = report.edited_doc_version + 1
report.edited_at = datetime.now(UTC)
```

No landing touch today. Landing-stale bump would slot after this write (or in the handler post-apply), comparing VR `edited_doc_version` to a future `landing_pages.edited_doc_version` stamp.

---

### 8. PR-1 staleness API surface

`SparkPhaseVersionInfo` (`spark_version_service.py` L26–L45): current spark + riv; per-phase spark/riv versions; `*_is_stale`; `*_stale_reasons: list[str]`.

`_stale_reasons` L58–L70 emits only `"spark"` and/or `"refined_idea"`. Adding `"edited_doc"` is a taxonomy extension (same list type).

Launch stamps read at L227–L237: `select(LandingPage.spark_version_id, LandingPage.refined_idea_version)` — natural place to also select/compare `edited_doc_version` once the column exists.

---

### 9. Tests needing updates

| Area | Files |
|------|--------|
| Public status rules | `tests/utils/test_landing_page_public.py` (unit on frozenset/helpers). **No** router integration suite for `/e/{slug}` status demotion found. |
| Evidence rerun | **No** `test_evidence_rerun*` / `EVIDENCE_RERUN` tests under `backend/tests/`. Closest: `test_dispatch_service.py` (USER_CONFIRM / AUTO_FIRE only). |
| Landing generation inputs | `test_landing_page_service.py` (persist/stamp; no `_fetch_validation_report` edited_doc path); `test_generate_landing_page_endpoint.py`; `dispatchers/test_in_process_landing_page.py` |
| edited_doc PATCH | `test_validation_report_edited_doc.py`; `test_validation_report_editor.py` |
| Staleness reasons | `test_spark_version_service.py` (`_stale_reasons` spark/riv only today) |

---

### 10. Frontend impact preflight

- Public page: no local status condition; backend 404 drives `notFound()`.
- Launch preview: `isLive` from `landing_page.live_at` (`LaunchStagePanel.tsx` L137), but fetch of landing only runs when `status ∈ LANDING_READY_STATUSES` (L23–L32) — **excludes `RESEARCH_READY`**. After Evidence rerun, UI drops to `previewState: "generate"` even though row + `live_at` remain; if status were still in the ready set, iframe would hit `/e/{slug}` and still 404 from backend.
- “Based on old Evidence edit”: **none**. Canvas Launch stale is spark/riv only (`ExperimentCanvas` → `launch_is_stale`). No Launch copy about Evidence `edited_doc`. Evidence `StalenessBanner` = `is_stale_since_regeneration` (edit vs research regen), orthogonal.
