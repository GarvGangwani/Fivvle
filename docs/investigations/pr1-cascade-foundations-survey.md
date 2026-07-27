# PR-1 Cascade Foundations Survey

**Date:** 2026-07-26 · Read-only · Complements `docs/investigations/cascade-integrity-survey.md`

---

### 1. PATCH `/spark` callers

Grep `frontend/` for `PATCH.*spark`, `/spark`, `patchExperimentSpark`.

| Site | Finding |
|------|---------|
| `frontend/lib/experiment-api.ts` L111–L118 | **Defines** `patchExperimentSpark` → `PATCH /experiments/{id}/spark` with `{ raw_idea }` |
| Any component/hook import or call | **ZERO callers** |

Live Spark UI uses only `saveSparkVersion` → `POST …/spark/save` (`useSparkManualSave.ts` L71).

**Verdict:** frontend has no live caller of the legacy PATCH route (dead wrapper only). Backend route still exists.

---

### 2. POST `/spark/save` vs PATCH `/spark` shapes

**PATCH** — `backend/app/routers/experiments.py` L2309–L2337:

```python
@router.patch(
    "/{experiment_id}/spark",
    response_model=GetExperimentDetailResponse,
    status_code=status.HTTP_200_OK,
)
async def patch_experiment_spark(..., body: PatchSparkRequest, ...) -> GetExperimentDetailResponse:
```

Request (`PatchSparkRequest`, `schemas/experiment.py` L42–L48): `{ raw_idea: str }` (max 2000).  
Response: full `GetExperimentDetailResponse` (experiment detail + `*_is_stale`, etc.).

**POST save** — `backend/app/routers/experiment_spark.py` L34–L58:

```python
@router.post(
    "/experiments/{experiment_id}/spark/save",
    response_model=SparkVersionOut,
)
async def save_spark_version_endpoint(..., payload: SparkSaveIn, ...) -> SparkVersionOut:
```

Request (`SparkSaveIn`, `schemas/spark_version.py` L11–L14): `{ raw_idea: str }` (max 2000) — **payload-compatible**.  
Response: `SparkVersionOut` (`id`, `version_number`, `raw_idea`, `attachment_ids_snapshot`, `created_at`) — **not** experiment detail.

To route PATCH through save: same body field; caller must either re-GET experiment or change response contract from `SparkVersionOut` → detail (or compose both).

---

### 3. Refine reopen call sites

**`_resolve_refinement_experiment`** (`chat_service.py` L501–L548) called from:

- `_handle_deep_research_turn` L923–L925 (only production call site of the resolver itself).

**`_handle_deep_research_turn` callers:**

- `handle_turn` when `deep_research=True` (~L715)
- `retry_assistant_message` when status in `{REFINING, REFINED}` (L1073–L1088)
- another path ~L1159 (same module)

**Status guards in refine path:**

- L520–L532: `SPARK` → begin + stamp
- L533–L543: `REFINED` → reopen to `REFINING`
- L544–L547: else if `!= REFINING` → `InvalidExperimentState`
- L445: `_uses_discussion_mode` treats any non-`REFINING` as discuss mode
- `refine_session_service.finalize_refinement` L64–L70: only sets `REFINED` from `{SPARK,REFINING,DRAFT,REFINED}`

**`finalize_refinement` callers:** `experiment_refine.py` L92–L102 (`POST …/refine/finalize`) only.

**UI trigger for reopen today:** not a dedicated “reopen” button. Flow = canvas Refine node click → `openRefinePanel` (`ExperimentCanvas.tsx` L377–L390, L704–L705) → chat send with `deep_research: true` (`useRefineChat.ts` L240–L250) → backend reopen only if status was `REFINED`. After `RESEARCH_READY`, same send hits the L544 guard.

---

### 4. Thread stamp write sites

**Sole caller:** `chat_service.py` L522–L531 (inside `SPARK` branch of `_resolve_refinement_experiment`).

Write-once guard (`spark_version_service.py` L226–L233):

```python
async def stamp_chat_thread_spark_version(...):
    """Stamp Refine's chat thread with the current Spark version (once)."""
    if thread.spark_version_id is not None:
        return
```

**Reads of `chat_threads.spark_version_id` for staleness:** `fetch_spark_phase_version_info` L174–L182 (`select(ChatThread.spark_version_id)` → `refine_spark_version` / `refine_is_stale`).

---

### 5. `refined_idea_version`

Grep `refined_idea_version|refined_version|refinement_version` under `backend/`: **NOT FOUND**.

Existing nearby: `refined_idea`, `refined_idea_current`, `refined_idea_updated_at`, `refinement_count` on `experiments` — no integer provenance counter for finalize.

**Tables that already carry `spark_version_id` (natural stamp targets for a second dimension):**

| Table | Has `spark_version_id` today |
|-------|------------------------------|
| `validation_reports` | yes |
| `landing_pages` | yes |
| `insight_reports` | yes |
| `chat_threads` | yes (refine) |
| `landing_page_v2_specs` | **no** |
| `launch_kits` | **no** |

Counter itself would live on `experiments` (not present today).

---

### 6. Universal chat context extension points

Dataclass + `to_prompt_block`: `experiment_project_context.py` L23–L55 (fields: id/status/current_act/name/raw_idea/refined_one_liner/target_audience/has_* flags only).

Caller: `universal_chat_service.py` L249–L254:

```python
project_context = await get_experiment_project_context(db, experiment)
user_prompt = build_universal_chat_user_prompt(
    project_context=project_context.to_prompt_block(),
    ...
)
```

Staleness compute: `fetch_spark_phase_version_info` in `spark_version_service.py` L166–L223; used by `_build_experiment_detail_response` (`experiments.py` L383). Takes `(db, experiment)` → `SparkPhaseVersionInfo`. **Reusable as-is** from the context builder (same args/async session); no shared import today — context builder does not call it.

---

### 7. Test files that will break / need updates

| File | One-line |
|------|----------|
| `backend/tests/services/test_chat_service.py` | `test_dr_experiment_refined_reopens_to_refining` (L595+) asserts reopen only from `REFINED`; `RESEARCH_READY` covered via `deep_research=False` discuss path (L780+) — reopen-after-research tests absent |
| `backend/tests/routers/test_refine_session.py` | finalize/reset HTTP against early statuses |
| `backend/tests/services/test_spark_version_service.py` | `_is_stale` unit truth table (spark-only) |
| `backend/tests/routers/test_experiment_spark.py` | `/spark/save` + GET `refine_is_stale` false; no PATCH coverage |
| `backend/tests/services/test_universal_chat_service.py` | `get_experiment_project_context` shape (~L893) |
| `backend/tests/services/test_experiment_service.py` | regen status guard `{REFINED,REFINING}` (adjacent, not reopen) |

**NOT FOUND:** tests for `PATCH /spark`, `stamp_chat_thread_spark_version`, or assert of `must be in REFINING` string.
