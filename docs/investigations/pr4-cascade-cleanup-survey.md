# PR-4 Cascade Cleanup Survey

**Date:** 2026-07-27 · Read-only · Complements cascade / PR-1–3 (not re-done)

**Alembic head:** `m0n1o2p3q4r5` (PR-3 publish cohorts)

**Suite baseline (this survey):** `84 failed, 1363 passed` (~6:57)

---

### Part 1 — LandingPageV2Spec

**Model** (`landing_page_v2.py` L20–L61): `id`, `experiment_id` (CASCADE, unique), `spec_json`, `generation_status`, `generation_phase`, `error_detail`, `created_at`, `updated_at`. **No** `spark_version_id` / `refined_idea_version` / `edited_doc_version`.

**VR load** (`landing_page_v2_service.py` L134–L146):
```python
if row is None or not row.raw_report:
    raise MissingResearchData(...)
return ValidationReport.model_validate(row.raw_report)
```
Confirms **raw_report only** — never `edited_doc`. Wiring edited_doc would be a one-site change in `_load_validation_report` (same flatten pattern as v1 post-PR-2).

**Generate / persist:** `generate_landing_page_v2_spec` L272–L422 writes `v2_row.spec_json` / status / phase (L409–L414). Entry: `run_landing_page_v2_generation_task` L425+; router `POST …/landing-page-v2/generate` (`landing_page_v2.py` L127–L148). Status GET L107–L124. **No PATCH edit path** — generate + get status only (regen-only).

**Migrations:** `20260628_1200_g3h4i5j6k7l8_landing_page_v2_specs.py` (create); `20260629_1200_h4i5j6k7l8m9_…` (`generation_phase`). No version stamp columns.

---

### Part 2 — Phantom statuses

**Enum** (`enums.py` L58–L66): `ANALYZING`, `COMPLETED` under “Terminal”; comment still says insight sub-states “under ANALYZING umbrella”. Also `SPARK`, `RESEARCH_VOICES` → **22** members. `test_experiment_status_count` expects **20** (pre-existing fail). `test_existing_states_preserved` asserts both string values.

**ANALYZING assignment sites:** **none** in forward flow. Occurrences: enum; `LANDING_PAGE_EDITABLE_STATUSES` (`landing_page_public.py` L20–L21); `experiment_project_context` stage map L105; frontend type union + allowlists (`types.ts`, `validation-flow`, `landing-flow`, `ChatInterface`, `canvas-helpers`, `dashboard-helpers`); tests (`test_landing_page_public`, status enum tests). Insight comment L70 still says “→ ANALYZING”.

**COMPLETED:** No forward assignment. **Only write path:** `infer_status_after_unarchive` (`experiment_service.py` L339–L352) returns `COMPLETED` when `experiment.insight_report is not None`. Also allowlists (editable, dashboard `_LIVE_LANDING_STATUSES`, project context, many FE stage sets), launch-kit test explicitly excludes COMPLETED from gate (`test_launch_kit_routes.py` ~L312–L317).

**_EVIDENCE_RERUN_ALLOWED:** neither ANALYZING nor COMPLETED (`dispatch_service.py` L20–L30).

**Migrations:** both in initial schema enum string list (`648fe71ca40e`). B4 migration docstring mentions ANALYZING umbrella; did not remove them. **Fixtures:** no test seeds `status=ANALYZING|COMPLETED` except comparisons/allowlists; lingering DB rows possible in real DBs (varchar enum, no CHECK) — speculative.

---

### Part 3 — Staleness naming

**`is_stale_since_regeneration`:** function + response key (`validation_report_editor.py` L294–L324); schema `EditedDocResponse` (`validation_report_edited_doc.py` L23–L33); GET/PATCH `…/validation-report/edited-doc` (`experiments.py` ~L1117–L1157); FE type `api.ts` L216; `EvidenceReportEditor` lifts via `onStaleChange?.(resp.is_stale_since_regeneration)` (L257/266/298); tests `test_validation_report_editor.py`, `test_validation_report_edited_doc.py`.

**Orthogonal canvas cascade:** `refine_is_stale` / `evidence_is_stale` / `launch_is_stale` / `signal_is_stale` on experiment detail (`types.ts` L297–L300; `ExperimentCanvas` L487–L502) — version stamps, not edited_at vs generated_at.

**StalenessBanner:** prop-less; shown when `EvidenceStagePanel` `stale` state is true (`EvidenceStagePanel.tsx` L43, L120–L125), driven solely by edited-doc API field above. Copy: “regenerated after your last edit”.

**External callers:** field only on founder edited-doc GET/PATCH JSON — no webhook/mobile consumer found.

---

### Hygiene

- Public accessibility: status-agnostic (`live_at` + not ARCHIVED) — no ANALYZING/COMPLETED in public gate.
- PR-4 wrap-up delta should use **84 failed / 1363 passed** as baseline.
