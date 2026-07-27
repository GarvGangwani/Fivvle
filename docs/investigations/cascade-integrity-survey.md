# Cascade Integrity Survey

**Date:** 2026-07-26  
**Scope:** Read-only architectural survey of the Spark → Refine → Evidence → Launch → Signal derivation chain.  
**Method:** Filesystem read + grep only. No app runs, migrations, installs, or git changes.

---

## 1. Status state machine

### 1.1 Full `ExperimentStatus` enum

From `backend/app/db/enums.py` L21–L66:

```python
class ExperimentStatus(StrEnum):
    """Matches ARCHITECTURE.md state machine exactly — 21 states total.
    ...
    """

    # --- Spark + refinement states (4) ---
    SPARK = "SPARK"
    DRAFT = "DRAFT"  # legacy mid-flow rows; new creates use SPARK
    REFINING = "REFINING"
    REFINED = "REFINED"

    # --- Research umbrella + sub-states (1 umbrella + 5 sub + 2 terminal = 8) ---
    RESEARCHING = "RESEARCHING"
    RESEARCH_PLANNING = "RESEARCH_PLANNING"
    RESEARCH_SEARCHING = "RESEARCH_SEARCHING"
    RESEARCH_READING = "RESEARCH_READING"
    RESEARCH_REFLECTING = "RESEARCH_REFLECTING"
    RESEARCH_VOICES = "RESEARCH_VOICES"
    RESEARCH_SYNTHESIZING = "RESEARCH_SYNTHESIZING"
    RESEARCH_READY = "RESEARCH_READY"
    RESEARCH_FAILED = "RESEARCH_FAILED"

    # --- Landing page states (3) ---
    LANDING_GENERATING = "LANDING_GENERATING"
    LANDING_DRAFT = "LANDING_DRAFT"
    LANDING_LIVE = "LANDING_LIVE"

    # --- Insight sub-states (3, under ANALYZING umbrella per RESEARCHING precedent) ---
    INSIGHT_GENERATING = "INSIGHT_GENERATING"
    INSIGHT_READY = "INSIGHT_READY"
    INSIGHT_FAILED = "INSIGHT_FAILED"

    # --- Terminal states (3) ---
    ANALYZING = "ANALYZING"
    COMPLETED = "COMPLETED"
    ARCHIVED = "ARCHIVED"
```

### 1.2 Assignment sites

Grep: `experiment.status\s*=|\.status\s*=\s*ExperimentStatus` and `_set_status(` under `backend/app`.

| File | Line(s) | From-status (inferable) | To-status | Trigger |
|------|---------|-------------------------|-----------|---------|
| `backend/app/services/experiment_service.py` | L102 | (create) | `SPARK` | `create_experiment_in_spark` |
| `backend/app/services/experiment_service.py` | L143 | `SPARK` | `REFINING` | `begin_refinement_from_spark` |
| `backend/app/services/experiment_service.py` | L196 | (create) | `DRAFT` | legacy `create_experiment_with_refinement` |
| `backend/app/services/experiment_service.py` | L208 | `DRAFT` | `REFINING` | same, after flush |
| `backend/app/services/experiment_service.py` | L227 | `REFINING` | `DRAFT` | refinement failure rollback (in-memory) |
| `backend/app/services/experiment_service.py` | L238 | `REFINING` | `REFINED` | legacy refine success |
| `backend/app/services/experiment_service.py` | L305 | `REFINED`/`REFINING` | `REFINING` | `regenerate_refinement` start |
| `backend/app/services/experiment_service.py` | L327 | `REFINING` | prior | regen failure rollback |
| `backend/app/services/experiment_service.py` | L339 | `REFINING` | `REFINED` | regen success |
| `backend/app/services/chat_service.py` | L536 | `REFINED` | `REFINING` | reopen refine chat after finalize |
| `backend/app/services/chat_service.py` | L559 | (create) | `REFINING` | new experiment from chat message |
| `backend/app/services/refine_session_service.py` | L70 | `SPARK`/`REFINING`/`DRAFT`/`REFINED` only | `REFINED` | `finalize_refinement` (status unchanged if already past those) |
| `backend/app/services/refine_session_service.py` | L112 | `REFINED` | `SPARK` | `reset_refinement_session` when no validation report |
| `backend/app/services/dispatch_service.py` | L65 | allowed set by trigger | `RESEARCHING` | `transition_to_researching_and_dispatch` |
| `backend/app/services/research_engine_service.py` | L240–L242, L278–L280, …, L526–L537, L577 | mid-research / any | `RESEARCH_FAILED` | phase failures via `_set_status` |
| `backend/app/services/research_engine_service.py` | L264 | `RESEARCHING` | `RESEARCH_PLANNING` | pipeline |
| `backend/app/services/research_engine_service.py` | L295 | prior phase | `RESEARCH_SEARCHING` | pipeline |
| `backend/app/services/research_engine_service.py` | L338 | prior | `RESEARCH_READING` | pipeline |
| `backend/app/services/research_engine_service.py` | L399 | prior | `RESEARCH_REFLECTING` | pipeline |
| `backend/app/services/research_engine_service.py` | L424 | prior | `RESEARCH_VOICES` | pipeline |
| `backend/app/services/research_engine_service.py` | L478 | prior | `RESEARCH_SYNTHESIZING` | pipeline |
| `backend/app/services/research_engine_service.py` | L553 | synthesizing | `RESEARCH_READY` | pipeline success |
| `backend/app/routers/experiments.py` | L885 | `LANDING_LIVE`/`INSIGHT_READY`/`INSIGHT_FAILED` | `INSIGHT_GENERATING` | `POST …/generate-insight` |
| `backend/app/routers/experiments.py` | L901 | `INSIGHT_GENERATING` | `INSIGHT_FAILED` | dispatch error rollback |
| `backend/app/routers/experiments.py` | L991 | `RESEARCH_READY`/`LANDING_DRAFT`/`LANDING_LIVE` (+ stuck generating) | `LANDING_GENERATING` | `POST …/generate-landing-page` |
| `backend/app/routers/experiments.py` | L1008 | `LANDING_GENERATING` | `RESEARCH_READY` | landing dispatch error rollback |
| `backend/app/routers/experiments.py` | L1869 | `LANDING_DRAFT` | `LANDING_LIVE` | `POST …/landing-page/publish` |
| `backend/app/routers/experiments.py` | L2262 | any non-archived | `ARCHIVED` | archive endpoint |
| `backend/app/routers/experiments.py` | L2303 | `ARCHIVED` | inferred | unarchive (`infer_status_after_unarchive`) |
| `backend/app/dispatchers/in_process_insight.py` | L53 / L109 | `INSIGHT_GENERATING` | `INSIGHT_READY` | insight success `_transition_status` |
| `backend/app/dispatchers/in_process_insight.py` | L94 | `INSIGHT_GENERATING` | `INSIGHT_FAILED` | `_fail_insight_generation` |
| `backend/app/dispatchers/in_process_landing_page.py` | L70–L78, L93–L95, L149–L150, L185 | `LANDING_GENERATING` | `LANDING_DRAFT` or `LANDING_LIVE` (success); `RESEARCH_READY` or `LANDING_LIVE` (failure if `was_live`) | landing dispatcher |

Response-body literals that echo status without writing DB (e.g. `experiments.py` L663, L754, L918, L1017, L2267) are omitted from the “writes” table above.

### 1.3 Where transitions are validated

**Not centralized.** Guards are scattered:

- `backend/app/services/dispatch_service.py` L16–L41, L56–L61 — frozensets `_USER_CONFIRM_ALLOWED`, `_AUTO_FIRE_ALLOWED`, `_EVIDENCE_RERUN_ALLOWED`; raises `InvalidExperimentState`.
- `backend/app/routers/experiments.py` — endpoint-local sets for confirm (L597–L607), generate-insight (L847–L858), generate-landing-page (L974–L988), publish (L1854–L1858).
- `backend/app/services/experiment_service.py` — `regenerate_refinement` allowed `{REFINED, REFINING}` (L290–L295); `begin_refinement_from_spark` only from `SPARK` (L138–L139).
- `backend/app/services/chat_service.py` L544–L547 — refine chat requires `REFINING` (after reopen from `REFINED` or start from `SPARK`).
- `backend/app/services/refine_session_service.py` L64–L70 — finalize only *sets* `REFINED` when status is in early set; no raise if status is later.
- `backend/app/routers/launch_kit.py` L61–L67 — `_LAUNCH_KIT_ALLOWED_STATUSES`.

Research phase transitions inside `research_engine_service._set_status` have **no** allowed-from check — they write whatever the pipeline reaches next.

### 1.4 State machine module / ADR

- Dedicated transition-map module: **NOT FOUND** (grepped `docs/` + `backend/app` for `transition map`, `ALLOWED.*STATUS` patterns beyond the frozensets above).
- ADRs mentioning state machine / status (grep `docs/adr/` for “state machine” and “status”):
  - `docs/adr/0009-pluggable-research-dispatcher.md` — confirm → research status
  - `docs/adr/0019-chat-mode-refinement-and-auto-dispatch.md` — chat coexistence with status
  - `docs/adr/0020-cloud-function-http-dispatcher.md` — stuck `RESEARCHING` recovery
  - `docs/adr/0021-insight-generator-architecture.md` — insight status flow
  - `docs/adr/0022-landing-page-generator-pipeline.md` — landing status / failure → `RESEARCH_READY`
- Enum comment claims alignment with `ARCHITECTURE.md`; no single ADR enumerates all legal edges.

### 1.5 Unreachable / re-entered statuses

| Status | Observation |
|--------|-------------|
| `ANALYZING` | **No assignment site** in `backend/app`. Appears only in allowlists / act-mapping (`landing_page_public.py`, `experiment_project_context.py`, canvas helpers). |
| `COMPLETED` | **Never assigned in forward flow.** Only returned by `infer_status_after_unarchive` when `insight_report is not None` (`experiment_service.py` L360–L361). Insight success leaves status at `INSIGHT_READY`. |
| `DRAFT` | Assigned only on legacy create / failure rollback; new Spark creates use `SPARK`. |
| `RESEARCH_READY` | Terminal for research success; **re-entered** after evidence re-run (via `RESEARCHING`…), and after landing **failure** when `was_live=False`. Also forced on landing dispatch error (L1008). |
| `LANDING_LIVE` | Re-entered on landing regen success when `was_live=True`; also failure path keeps `LANDING_LIVE` when `was_live` (`in_process_landing_page.py` L75–L78). |
| `INSIGHT_READY` / `INSIGHT_FAILED` | Re-enterable via regen / retry from generate-insight allowed set. |
| `REFINED` | Re-entered via finalize; can move back to `REFINING` via chat reopen. |

---

## 2. Derivation map

### 2.1 `refined_idea` / `refined_idea_current` (JSONB on `experiments`)

**Created where**

- WIP write: `backend/app/services/refinement_service.py` L336–L338 (`refined_idea_current` + `refined_idea_updated_at` on chat turn).
- Promote to stable: `backend/app/services/refine_session_service.py` L47–L78 (`finalize_refinement` copies current → `refined_idea`).
- Legacy one-shot: `experiment_service.create_experiment_with_refinement` / `regenerate_refinement` write `refined_idea` directly (L235–L238, L336–L339).

**Reads what upstream**

- Chat refinement uses `experiment.raw_idea` (and prior refined idea / feedback) inside refinement LLM path.
- Research pipeline reads `experiment.refined_idea` only (`research_engine_service.py` L238–L250) — not `refined_idea_current`.

Quote (research read):

```python
if experiment.refined_idea is None:
    ...
refined_idea = RefinedIdea.model_validate(experiment.refined_idea)
```

**Provenance recorded**

- Spark linkage for Refine is on **`chat_threads.spark_version_id`**, stamped once via `stamp_chat_thread_spark_version` (`spark_version_service.py` L226–L238) — not a column on the refined_idea JSON itself.
- `refined_idea_updated_at` timestamps WIP updates only.
- **No hash / snapshot of raw_idea embedded in refined_idea JSON.**

**Update semantics**

- Chat continuously mutates `refined_idea_current` (WIP).
- Finalize overwrites `refined_idea` from WIP; does **not** distinguish “user edited fields” vs “LLM regenerated” inside the JSON.
- Reset clears WIP; clears stable `refined_idea` only if no validation report (`refine_session_service.py` L107–L113).

### 2.2 `ValidationReport`

**Created where**

- `backend/app/services/research_engine_service.py` `_write_validation_report` L143–L184; called on pipeline success ~L546–L551.

**Reads what upstream**

- Full pipeline: `experiment.refined_idea`, targeting fields on experiment, then planner→searcher→reader→reflector→voices→synthesizer outputs.
- Stamps `spark_version_id` from `get_latest_spark_version_id` at pipeline start (L255–L259, passed into upsert L171).

**Provenance recorded**

```python
spark_version_id: Mapped[UUID | None] = mapped_column(
    PG_UUID(as_uuid=True),
    ForeignKey("experiment_spark_versions.id"),
    nullable=True,
)
```

(`validation_report.py` L40–L44) plus `generated_at` (L56–L60). Upsert refreshes `raw_report`, scores, `generated_at`, `spark_version_id` — **does not clear `edited_doc` / `edited_at` / `edited_doc_version`** (conflict `set_` keys L175–L181).

**Update semantics**

- Regeneration: UPSERT overwrites `raw_report` (immutable-source semantics for new generation).
- Founder overlay: `PATCH …/validation-report/edited-doc` via `apply_edited_doc_patch` — separate `edited_doc` column; optimistic `edited_doc_version`; `is_stale_since_regeneration` compares `edited_at < generated_at`.

### 2.3 `LandingPage` (v1)

**Created where**

- `backend/app/services/landing_page_service.py` `generate_landing_page` L768+; persist `_persist_landing_page_row` L713–L765.

**Reads what upstream**

- `ValidationReport.raw_report` only (not `edited_doc`) — `_fetch_validation_report` L310–L321.
- `Experiment.refined_idea` via `_parse_refined_idea`.
- Request args: `page_goal`, `template_id`, optional `regeneration_hint`.

**Provenance recorded**

- `landing_pages.spark_version_id` set to latest Spark on insert/update (L738–L760).
- `page_json.meta.generated_at` / `generation_id` written in memory at L859–L863.
- **No pointer to validation_report id or edited_doc version.**

**Update semantics**

- Regen UPSERTs same 1:1 row (overwrites `copy_json` / `page_json`; keeps slug / `live_at` unless changed elsewhere).
- Founder PATCH landing fields (`experiments.py` ~L1800+) mutates copy without regenerating from Evidence.
- No “user edited vs regenerated” flag on the row.

### 2.4 `LandingPageV2Spec`

**Created where**

- `backend/app/services/landing_page_v2_service.py` `generate_landing_page_v2_spec` L272–L414; `_get_or_create_v2_row` ~L152+.

**Reads what upstream**

- `experiment.refined_idea`, validation report (loaded via `_load_validation_report`), optional existing `LandingPage` for uploaded assets (L290–L294).

**Provenance recorded**

- Table has `created_at` / `updated_at` / `generation_status` / `generation_phase` only (`landing_page_v2.py` L38–L58).
- **No `spark_version_id`.** Derivation is by-position only relative to Spark versions.

**Update semantics**

- Overwrites `spec_json` on regen; generation phase columns track pipeline; no user-edit vs regen distinction beyond regenerating the whole spec.

### 2.5 `InsightReport`

**Created where**

- `backend/app/services/insight_service.py` `generate_insight_report` L186–L299; `_persist_insight_row` L158–L183.
- On regen: **deletes** existing row then inserts (L273–L276).

**Reads what upstream**

- Parsed `ValidationReport` (`raw_report` path).
- `build_analytics_aggregate` (page views + waitlist + live_at timing).

**Provenance recorded**

- `spark_version_id` (L55–L58 model; set L278–L285).
- `generated_at` (L60–L64).
- **No `source_report_id` / validation_report FK / landing version pointer.**

**Update semantics**

- Full replace on regenerate. No founder overlay column on insight (founder decision lives on `experiments`).

---

## 3. Existing versioning and timestamps

### 3.1 Table `experiment_spark_versions`

**FOUND.** Model `backend/app/db/models/experiment_spark_version.py` L16–L53. Migration `backend/alembic/versions/20260710_1500_c6d7e8f9a0b1_add_spark_versions.py`.

Columns: `id`, `experiment_id`, `version_number`, `raw_idea`, `attachment_ids_snapshot`, `created_by`, `created_at`.

### 3.2 Columns on `experiments`

| Column | Status |
|--------|--------|
| `refined_idea_current` | FOUND — model L66; migration `20260711_1800_a0b1c2d3e4f5_refined_idea_current.py` |
| `refined_idea_updated_at` | FOUND — model L67–L69; same migration |
| `refinement_count` | FOUND — model L76–L81; migration `20260512_1649_c3d8a1f92b47_b1_add_refinement_count_and_nullable_slug.py` |
| `raw_idea_updated_at` | **NOT FOUND**, grepped: `raw_idea_updated_at` |
| Extra `*_at` beyond created/updated | FOUND: `spark_last_edited_at` (L119–L122), `refinement_started_at` (L123–L126), `founder_decision_at` (L193–L196). Migration for spark timestamps: `20260710_1330_a4b5c6d7e8f9_add_spark_and_attachments.py`. |

### 3.3 Columns on `validation_reports`

| Column | Status |
|--------|--------|
| `edited_doc` | FOUND — model L67; migration `20260716_2330_d2e3f4a5b6c7_validation_report_edited_doc.py` |
| `edited_doc_version` | FOUND — model L70–L75; same |
| `edited_at` | FOUND — model L78–L81; same |
| `raw_report` | FOUND — model L39; earlier B2.4 migration `20260514_0600_a9f3e21d84bc_…` |
| Generation timestamp | `generated_at` FOUND — model L56–L60 |

### 3.4 Landing page versioning

- `landing_pages`: `live_at`, `last_revalidated_at`, `spark_version_id` — **no revision counter / republish counter**.
- `landing_page_v2_specs`: `created_at`, `updated_at`, generation status/phase — **no spark_version_id, no revision number**.
- Republish counter: **NOT FOUND**, grepped: `republish`, `publish_count`, `revision`.

### 3.5 Insight report versioning

- `generated_at`, `spark_version_id` FOUND.
- `version` column / `source_report_id`: **NOT FOUND**, grepped: `source_report_id`, `InsightReport.version`.

### 3.6 Alembic migrations (filename or docstring mentions version / edit / stale / invalidat / provenance / snapshot)

Chronological by filename timestamp (most recent last). Content-grep also hits wallet “credits” files that mention unrelated “version” strings; listed here only when cascade-relevant by name/docstring:

1. `20260514_0600_a9f3e21d84bc_b2_4_validation_report_raw_payload_and_research_error_detail.py` — raw_report schema
2. `20260606_1600_a7b3e9c2f4d8_b4_insight_raw_output_column.py` — insight raw_output
3. `20260710_1330_a4b5c6d7e8f9_add_spark_and_attachments.py` — spark timestamps
4. `20260710_1500_c6d7e8f9a0b1_add_spark_versions.py` — **spark versions + phase FKs**
5. `20260711_1800_a0b1c2d3e4f5_refined_idea_current.py` — WIP refined idea (docstring: “user-owned finalize”)
6. `20260716_2330_d2e3f4a5b6c7_validation_report_edited_doc.py` — **edited_doc overlay**
7. `20260718_0030_c5d6e7f8a9b0_add_launch_kits.py` — launch kit includes `edited_doc` pattern
8. `20260724_2200_i5j6k7l8m9n0_add_founder_decision_columns.py` — founder_decision_version

(Also content-matched but not cascade-provenance: wallet/coupon credit migrations — omitted from cascade focus.)

### 3.7 Who writes / reads version columns

| Artifact | Writers | Readers / comparison |
|----------|---------|----------------------|
| `experiment_spark_versions` | `save_spark_version` | list endpoint; `fetch_spark_phase_version_info`; stamping helpers |
| `chat_threads.spark_version_id` | `stamp_chat_thread_spark_version` (**once only** if null) | `fetch_spark_phase_version_info` → `refine_is_stale` |
| `validation_reports.spark_version_id` | research upsert | phase staleness |
| `landing_pages.spark_version_id` | landing persist | phase staleness |
| `insight_reports.spark_version_id` | insight persist | phase staleness |
| `edited_doc_version` / `edited_at` | `apply_edited_doc_patch` | PATCH CAS; `is_stale_since_regeneration` |
| `generated_at` (VR) | research upsert | compare vs `edited_at` |
| `*_is_stale` API fields | computed in `fetch_spark_phase_version_info` | GET experiment detail → canvas |

Staleness predicate:

```python
def _is_stale(phase_version: int | None, current: int) -> bool:
    if phase_version is None or current <= 0:
        return False
    return phase_version < current
```

(`spark_version_service.py` L43–L46)

---

## 4. Current behavior on upstream edit

### 4a. Edit Spark `raw_idea` after `RESEARCH_READY`

**Two endpoints (wired differently):**

1. **Versioning path (canvas save):** `POST /experiments/{id}/spark/save` — `backend/app/routers/experiment_spark.py` L34–L58 → `save_spark_version`.
   - **No status check** (ownership only).
   - If content changed: new `experiment_spark_versions` row; bumps version; sets `experiments.raw_idea` + `spark_last_edited_at`.
   - Downstream rows **not cleared**. Staleness flags become true when phase `spark_version_id` lags current (`fetch_spark_phase_version_info`).
2. **Legacy PATCH:** `PATCH /experiments/{id}/spark` — `experiments.py` L2309–L2337 → `update_experiment_raw_idea`.
   - Updates `raw_idea` + `spark_last_edited_at` only (`experiment_service.py` L117–L130).
   - **Does not create a spark version row** → **does not flip `*_is_stale` flags**.

**UI:** Canvas Spark save button; warning copy in `SparkExpandedNode.tsx` L190–L195 when dirty and refine/evidence already stale. Act nodes show yellow “BASED ON vN · CURRENT IS vM” when GET returns `*_is_stale`. Unsaved close uses `window.confirm` (`useSparkManualSave.ts` L85–L92). Save itself has no confirm about cascade.

### 4b. Re-enter Refine after `RESEARCH_READY`

- Refine **chat** path: `chat_service._resolve_refinement_experiment` requires `SPARK` → begin, or `REFINED` → reopen to `REFINING`, else:

```python
if experiment.status != ExperimentStatus.REFINING:
    raise InvalidExperimentState(
        f"Experiment must be in REFINING status (current: {experiment.status})"
    )
```

(`chat_service.py` L544–L547)

So after `RESEARCH_READY`, **chat turns are rejected** (status is not `REFINING`/`REFINED`/`SPARK`).

- `POST …/refine/finalize` has **no status gate** beyond ownership + presence of `refined_idea_current`. If somehow WIP exists while status is `RESEARCH_READY`, finalize copies WIP → `refined_idea` but **does not change status** (only early statuses flip to `REFINED` — `refine_session_service.py` L64–L70). Existing `validation_report` is **left intact**.

- `stamp_chat_thread_spark_version` will **not** re-stamp if already set (L232–L233) — refine’s recorded spark version stays frozen at first stamp.

**UI:** Finalize confirm dialog exists in `LiveWorkspacePanel.tsx` (~L355) — about marking refined idea ready, not about invalidating Evidence.

### 4c. Edit Evidence `edited_doc` after landing exists

- Endpoint: `PATCH /experiments/{id}/validation-report/edited-doc` (`experiments.py` L1132–L1156).
- **No status check** beyond ownership + report exists (via `_load_owned_validation_report`).
- Writes overlay only; does **not** touch `landing_pages`, does **not** set `launch_is_stale` (that flag is Spark-version based only).
- Landing generator continues to read **`raw_report`**, not `edited_doc` — so Launch copy is not derived from the overlay the founder edits.

**UI:** `StalenessBanner` is for **regen-after-edit** (`is_stale_since_regeneration`), not for “landing out of date vs edited_doc”. No landing staleness signal from this edit.

### 4d. Republish / regenerate landing while analytics rows exist

- First publish: `POST …/landing-page/publish` requires `LANDING_DRAFT` → sets `live_at`, status `LANDING_LIVE`.
- Regen while live: `generate-landing-page` with `was_live=True` → success returns to `LANDING_LIVE`; failure **keeps** `LANDING_LIVE`.
- `page_views` / `waitlist_signups` keyed by **`experiment_id` only** — no landing_page version / publish id (`page_view.py` L28–L33; `waitlist_signup.py` L27–L32).
- Rows **carry forward and mix** with post-republish traffic. No reset on regenerate/publish.

**UI:** No banner about mixed analytics across publishes. ISR revalidation via `landing_page_revalidate.py` / frontend `app/api/revalidate/route.ts` (cache invalidation, not analytics reset).

---

## 5. Staleness infrastructure

### 5.1 `StalenessBanner`

- File: `frontend/components/research/StalenessBanner.tsx` L5–L17.
- **No props** — static copy about report regenerated after last edit.
- Imported by: `frontend/components/research/EvidenceStagePanel.tsx` L17, L120.
- Signal: frontend state `stale` lifted from `EvidenceReportEditor` → API field `is_stale_since_regeneration` (`EvidenceReportEditor.tsx` L257, L266, L298) — **backend-provided boolean**, not a client timestamp compare.

### 5.2 Other stale / invalidat / outdated occurrences (cascade-relevant)

| File | Line | Meaning |
|------|------|---------|
| `backend/app/services/spark_version_service.py` | L33–L36, L43–L46, L219–L222 | Spark-phase staleness flags |
| `backend/app/routers/experiments.py` | L361–L364, L413–L416 | API exposes `*_is_stale` |
| `frontend/lib/types.ts` | L290–L293 | TS fields |
| `frontend/components/experiment/ExperimentCanvas.tsx` | L464–L542 | Canvas maps flags → `isStale` / rerun |
| `frontend/components/experiment/nodes/ActNode.tsx` | L19, L94–L125 | Renders stale strip + Evidence rerun |
| `frontend/components/experiment/nodes/SparkExpandedNode.tsx` | L191–L195 | Save warning when downstream stale |
| `backend/app/services/validation_report_editor.py` | L205–L214 | `edited_at < generated_at` |
| `backend/app/schemas/validation_report_edited_doc.py` | L23–L33 | Response contract |
| `frontend/lib/api.ts` | L216 | `is_stale_since_regeneration` type |
| `backend/app/services/landing_page_revalidate.py` | L1+ | ISR cache invalidation (not cascade flag) |
| `frontend/app/api/revalidate/route.ts` | L11+ | ISR invalidation |
| Tests under `test_spark_version_service`, `test_validation_report_editor`, `test_validation_report_edited_doc`, `test_experiment_spark` | — | Unit/integration of above |

Many other hits are eval-copy “handbook staleness” or docs “stale baseline” — not product cascade infrastructure.

### 5.3 Downstream-newer-than-upstream comparison pattern

- **Spark cascade:** integer version compare `phase_version < current` (`_is_stale`).
- **Evidence overlay:** datetime compare `edited_at < generated_at`.
- **No** general “landing generated_at ≥ validation generated_at” or “insight ≥ landing” comparator found.

---

## 6. Canvas lock states

### 6.1 `getNodeLockState` (full)

File: `frontend/components/experiment/canvas-helpers.ts` L33–L102:

```typescript
export function getNodeLockState(
  nodeId: string,
  experiment: Experiment,
): NodeLockState {
  switch (nodeId) {
    case "spark":
    case "resources":
      return { isLocked: false };

    case "refine":
      if ((experiment.current_spark_version ?? 0) < 1) {
        return {
          isLocked: true,
          unlockRequirement:
            "Save your idea in Spark first to unlock Refine.",
        };
      }
      return { isLocked: false };

    case "evidence": {
      const unlocked =
        experiment.status === "REFINED" ||
        REFINED_OR_LATER.has(experiment.status) ||
        hasRefinedIdeaPayload(experiment);
      if (!unlocked) {
        return {
          isLocked: true,
          unlockRequirement:
            "Finalize your refinement to unlock Evidence.",
        };
      }
      return { isLocked: false };
    }

    case "launch": {
      const hasValidationReport =
        experiment.validation_report != null ||
        (experiment.evidence_atom_count ?? 0) > 0 ||
        RESEARCH_READY_OR_LATER.has(experiment.status);
      if (!hasValidationReport) {
        return {
          isLocked: true,
          unlockRequirement:
            "Complete Evidence research to unlock Launch.",
        };
      }
      return { isLocked: false };
    }

    case "signal": {
      const hasLandingPage = LANDING_PAGE_CREATED.has(experiment.status);
      if (!hasLandingPage) {
        return {
          isLocked: true,
          unlockRequirement:
            "Deploy your Launch page to unlock Signal.",
        };
      }
      return { isLocked: false };
    }

    default:
      return { isLocked: false };
  }
}
```

### 6.2 Distinct return values

Structurally only:

- `{ isLocked: false }`
- `{ isLocked: true, unlockRequirement: string }` (four distinct requirement strings)

`NodeLockState` type L3–L5. Separately, `isActRunning` returns boolean running-ness; canvas adds `isStale` as a **parallel** data field, not a lock-state enum value.

### 6.3 Per-node mapping

| Node | Lock logic |
|------|------------|
| spark | always unlocked |
| resources | always unlocked |
| refine | locked until `current_spark_version >= 1` |
| evidence | unlocked if status `REFINED` or later set, or refined idea payload present |
| launch | unlocked if validation summary / evidence atoms / `RESEARCH_READY+` status |
| signal | unlocked if status in `LANDING_PAGE_CREATED` set (draft/live/insight/analyzing/archived/completed) |
| core | not passed through `getNodeLockState` in buildNodes (coreShell) |

### 6.4 “Complete but stale”?

**No.** Lock state has no stale variant. Staleness is orthogonal (`isStale` on `ActNodeData`).

### 6.5 Consumption / visuals

- Built in `ExperimentCanvas.tsx` L522–L542; also gate clicks L100, L272, L378, L691.
- `ActNode.tsx`: locked → opacity 40%, “LOCKED”, lock icon; unlocked + `isStale` → yellow footer with version text; Evidence-only `canRerun` button.

---

## 7. Regeneration paths

| Act | Endpoint(s) | Preconditions | Credits | Downstream side effects | Frontend confirm |
|-----|-------------|---------------|---------|-------------------------|------------------|
| Spark save | `POST /spark/save`; also `PATCH /spark` | ownership; length caps | none | version bump (save only) → stale flags; no clears | close-unsaved confirm only |
| Refine re-finalize | `POST /refine/finalize` | ownership; `refined_idea_current` present | none | overwrites `refined_idea`; status→`REFINED` only from early statuses; VR untouched | confirm dialog in LiveWorkspacePanel |
| Refine chat reopen | chat send | status `REFINED`→`REFINING`; **blocked after `RESEARCH_READY`** | none | status only | n/a |
| Evidence re-run | `POST /evidence/rerun` | `_EVIDENCE_RERUN_ALLOWED` (includes live/insight states); not mid-research | `fullValidationFlow` = **50** credits (`pricing.py` L41; debit L700–L705) | status → `RESEARCHING`…→`RESEARCH_READY`; VR upsert (keeps edited_doc); **does not delete landing_page / page_views / waitlist**; status leaves `LANDING_LIVE` for `RESEARCH_READY` so public accessibility set no longer includes the page | **no confirm** — canvas button fires `rerunEvidence` directly (`ExperimentCanvas.tsx` L448–L459) |
| Launch regen | `POST /generate-landing-page` | `RESEARCH_READY`/`LANDING_DRAFT`/`LANDING_LIVE` | **no wallet debit in this route** | upserts landing row; stamps latest spark_version_id; analytics uncleared | editor regen flows exist; not a generic cascade confirm |
| Launch publish | `POST /landing-page/publish` | `LANDING_DRAFT` only | none | sets `live_at`, `LANDING_LIVE` | — |
| Signal insight | `POST /generate-insight` | `LANDING_LIVE`/`INSIGHT_READY`/`INSIGHT_FAILED`; min data threshold | `insightReport` = **20** credits | deletes+recreates insight; stamps spark_version_id | paywall gate helpers exist; no cascade confirm |

Also: legacy `POST /confirm` (REFINED/RESEARCH_FAILED only) and chat auto-fire path still use `fullValidationFlow` debit + `USER_CONFIRM`/`AUTO_FIRE` allowed sets.

---

## 8. Universal chat context

### 8.1 Builder

`backend/app/services/experiment_project_context.py` L105–L146 — `get_experiment_project_context`.

Returned dataclass L23–L36:

```python
@dataclass(frozen=True)
class ExperimentProjectContext:
    experiment_id: str
    status: str
    current_act: str
    name: str | None
    raw_idea: str | None
    refined_one_liner: str | None
    target_audience: str | None
    has_validation_report: bool
    has_landing_page: bool
    has_insight_report: bool
```

Prompt block via `to_prompt_block()` L38–L55 — presence flags + short idea fields only (module docstring L1–L5).

### 8.2 Stale / derivation signals

**None.** No `*_is_stale`, spark version numbers, or “derived from version N” fields.

Obvious slot: extend `ExperimentProjectContext` / `to_prompt_block` alongside the same `fetch_spark_phase_version_info` already used by GET experiment detail — **not present today**.

### 8.3 Consumers

- `backend/app/services/universal_chat_service.py` L249–L251 (builds prompt); L410 (`current_act`).
- Prompt assembly: `backend/app/llm/prompts/universal_chat.py` L78–L111 (`project_context` XML block).

---

## 9. Soft-fail contracts

### 9.1 Per dispatcher

| Dispatcher | Failure handling |
|------------|------------------|
| `in_process.py` (research) | Schedules pipeline; pipeline **internally** sets `RESEARCH_FAILED` + error detail; unexpected exceptions logged in done-callback, do not propagate to HTTP |
| `http.py` (research) | Dispatch mint/POST failures raise `DispatchError` to caller (route refunds + 502). Post-accept CF failures are out of process (ADR 0020 stuck-state note) |
| `in_process_insight.py` | Known + unknown errors → `_fail_insight_generation`: refund `insightReport`, status `INSIGHT_FAILED` |
| `in_process_landing_page.py` | Retries then `_transition_status` to `RESEARCH_READY` or keep `LANDING_LIVE` if `was_live`; launch-kit auto-dispatch failures **swallowed** (log warning L106–L112) |
| `launch_kit.py` | Failures log + rollback session; **no** Experiment.status change |

### 9.2 Forward-only / non-reset patterns

- Landing failure when `was_live=True` **does not** roll status back to `RESEARCH_READY` — stays `LANDING_LIVE` (`in_process_landing_page.py` L75–L78).
- Evidence re-run moves status forward into research even from `LANDING_LIVE` / insight states; success lands at `RESEARCH_READY` — **does not restore** prior landing/insight status.
- `stamp_chat_thread_spark_version` never updates an existing stamp.
- Research VR upsert does not null `edited_doc` on regen.

### 9.3 Soft-fail vs a future “downstream is stale” flag

**Unclear / tension points (findings only):**

1. Landing soft-fail that **preserves `LANDING_LIVE`** while content may be mid-failure / old — a stale flag on Launch could disagree with “still live” status.
2. Evidence re-run from live/insight states **changes status out of** public-live set without deleting analytics or landing rows — status and artifact presence diverge; a stale flag would coexist with orphaned live rows.
3. Insight failure → `INSIGHT_FAILED` with refund is hard-fail, not soft — different from landing’s soft live-preserve.
4. Spark `PATCH` path updates idea without version bump — a flag keyed only to spark versions would miss that path (already true for today’s `*_is_stale`).

---

## 10. Test coverage

### 10.1 Backend tests touching cascade / status / regen / staleness

**Spark / versions**

- `backend/tests/routers/test_experiment_spark.py` — save increments, short-circuit, GET stale flags false on fresh save
- `backend/tests/services/test_spark_version_service.py` — `_is_stale` / attachment id equality

**Refine**

- `backend/tests/routers/test_refine_session.py` — finalize/reset session
- `backend/tests/services/test_chat_service.py` — refine reopen, status guards
- `backend/tests/services/test_refinement_service.py` — refine LLM path / counts
- `backend/tests/routers/test_chat.py` — chat routes

**Evidence / research / status**

- `backend/tests/services/test_dispatch_service.py` — trigger allowed sets → RESEARCHING
- `backend/tests/routers/test_confirm_and_research_status.py` — confirm, phase labels, failed retry
- `backend/tests/services/test_research_engine_service.py` (+ reader/trends wiring variants) — pipeline status / report write
- `backend/tests/db/test_experiment_status_insight_states.py` — enum presence including ANALYZING/COMPLETED
- `backend/tests/services/test_validation_report_editor.py` — edited_doc + `is_stale_since_regeneration`
- `backend/tests/routers/test_validation_report_edited_doc.py` — PATCH CAS + stale flag after regen

**Launch**

- `backend/tests/routers/test_generate_landing_page_endpoint.py` — status guards / 202
- `backend/tests/dispatchers/test_in_process_landing_page.py` — success/failure status transitions
- `backend/tests/services/test_landing_page_service.py` — generation
- `backend/tests/services/test_landing_page_revalidate.py` — ISR invalidation
- `backend/tests/utils/test_landing_page_public.py` — public/editable status sets

**Signal / insight**

- `backend/tests/routers/test_generate_insight_endpoint.py` — guards / debit paths
- `backend/tests/dispatchers/test_in_process_insight_dispatcher.py` — READY/FAILED
- `backend/tests/services/test_insight_service.py` — generate + delete-on-regen

**Unarchive / infer**

- `backend/tests/services/test_infer_status_after_unarchive.py` — COMPLETED when insight exists

### 10.2 Tests asserting behavior on upstream edit after later acts

- Spark save → stale flags: partial (`test_experiment_spark` asserts flags **false** right after save with no downstream stamps).
- Evidence overlay vs regen: **yes** — `test_stale_flag_set_when_regeneration_after_edit` in `test_validation_report_edited_doc.py`.
- **Editing `raw_idea` after `RESEARCH_READY` produces X:** **NOT FOUND** as an explicit end-to-end assertion.
- **Finalize / refine chat after `RESEARCH_READY`:** **NOT FOUND** as dedicated case (chat tests cover `REFINED` reopen and reject non-REFINING, including a `RESEARCH_READY` expectation that status stays ready when chat blocked — `test_chat_service.py` ~L791–L811).

### 10.3 Frontend tests

Found (excluding snapshots):

- `frontend/components/refinement/__tests__/ClarifyingQuestionBlock.test.tsx` — clarifying Q regenerate UX (not canvas cascade)
- `frontend/lib/__tests__/launch-channel-intents.test.ts`
- `frontend/lib/__tests__/parse-citations.test.ts`
- `frontend/lib/__tests__/report-text.test.ts`

**Canvas lock states / StalenessBanner / ActNode stale UI:** **NOT FOUND** under `*.test.*` / `*.spec.*`.

---

## 11. Where the code diverges from the handoff snapshot

1. **Spark staleness already exists** — `experiment_spark_versions` + per-phase `spark_version_id` + GET `*_is_stale` + canvas yellow strips + Evidence-only rerun. The survey title implies designing invalidation from scratch; the codebase already has a Spark-version cascade (but only Spark→phases, not Evidence-edit→Launch or Refine-finalize→Evidence).

2. **Two Spark write paths diverge** — `POST /spark/save` versions; `PATCH /spark` mutates `raw_idea` **without** versioning, so it **silently skips** the only cascade signal the product has.

3. **Refine after Evidence is effectively blocked** — chat requires `REFINING`; reopen only from `REFINED`. After `RESEARCH_READY`, the derivation chain cannot be walked backward through chat, while finalize still won’t move status if somehow called.

4. **`stamp_chat_thread_spark_version` is write-once** — Refine stays permanently “stale” after any later Spark save; there is no re-stamp on re-finalize.

5. **Evidence `edited_doc` is not upstream of Launch** — landing generation reads `raw_report` only; editing Evidence never sets `launch_is_stale`.

6. **Evidence re-run from `LANDING_LIVE` / insight statuses demotes status to research** while **keeping** landing row + mixed analytics; public accessibility then fails (`PUBLIC_LANDING_PAGE_STATUSES` excludes `RESEARCH_READY`) without deleting the page.

7. **`ANALYZING` and forward-path `COMPLETED` are phantom enum members** — present in allowlists and unarchive inference, never assigned by insight success (`INSIGHT_READY` is the real terminal).

8. **Landing generation does not debit wallet credits** despite `landingPageGeneration: 15` in `SERVICE_PRICING`; only `fullValidationFlow` and `insightReport` are debited on these regen routes.

9. **`LandingPageV2Spec` is outside the spark-version provenance system** entirely.

10. **`StalenessBanner` ≠ canvas `isStale`** — banner = edited_doc vs research regen; canvas = spark version lag. Same word, two mechanisms.

11. **Universal chat context has presence flags only** — no awareness of the spark-version staleness the canvas already computes.

12. **Page views / waitlist are experiment-scoped forever** — no publish generation binding; republish mixes cohorts by design of the schema.
