# Business Construction Engine — Implementation Report

**Date:** 2026-07  
**Status:** Implemented (architecture evolution; deterministic Reasoning Engine v1)

---

## Files Modified

| File | Change |
|------|--------|
| `backend/app/schemas/reader.py` | Docstring: Reader owns evidence atoms only; points to `EvidenceAtom` adapter |
| `backend/app/schemas/reflector.py` | Added `evidence_analysis` on `ReflectorPhaseSummary` |
| `backend/app/schemas/validation_report.py` | Added optional `business_construction` field |
| `backend/app/services/reflector_service.py` | Attaches `EvidenceAnalysisResult` at end of every Reflector exit path |
| `backend/app/services/research_engine_service.py` | Wires Reasoning Engine before Synthesizer; passes analysis + reasoning into `SynthesizerInput` |
| `backend/app/services/research_engine.py` | Same wiring for in-process/eval orchestrator |
| `backend/app/services/synthesizer_input.py` | Extended with `evidence_analysis`, `reasoning_output`; builder accepts both |
| `backend/app/services/synthesizer_service.py` | Attaches `BusinessConstructionArtifact` to `ValidationReport` after LLM hydrate |
| `backend/app/llm/prompts/synthesizer.py` | Injects `<business_construction_intelligence>` block when reasoning present |

---

## New Components Added

### Schemas — `backend/app/schemas/business_construction.py`

| Model | Purpose |
|-------|---------|
| `EvidenceAtom` | Canonical evidence unit (observation, source, confidence, context, excerpt) |
| `EvidenceContradiction` | Opposing atoms on same theme |
| `EvidenceCluster` | Grouped observations |
| `EvidenceAnalysisResult` | Reflector-expanded evidence quality assessment |
| `Mechanism` | Explanatory model linking observations |
| `Hypothesis` | Competing explanation |
| `HypothesisDebate` | Support/contradict/challenge record per hypothesis |
| `Prediction` | Forward claim from mechanism |
| `FounderDecision` | Actionable business implication |
| `BusinessComponent` | Constructed startup building block |
| `ReasoningEngineOutput` | Full reasoning pipeline output |
| `BusinessConstructionArtifact` | Persisted bundle on `ValidationReport` |

### Services

| Module | Responsibility |
|--------|----------------|
| `backend/app/services/evidence_atoms.py` | Maps `ExtractedEvidence` → `EvidenceAtom`; `collect_evidence_atoms()` |
| `backend/app/services/evidence_analysis_service.py` | Deterministic contradictions, clusters, gaps, weak evidence |
| `backend/app/services/reasoning_engine_service.py` | Reasoning Engine: clustering → mechanisms → hypotheses → debate → predictions → decisions → business components |

### Tests

| File | Coverage |
|------|----------|
| `backend/tests/services/test_reasoning_engine.py` | Atom collection, evidence analysis, full reasoning output |

---

## Architectural Changes

### Reader

**Before:** Extract findings/evidence for Synthesizer consumption.  
**After:** Still emits `ExtractedEvidence` via LLM (unchanged contract). Semantically owns **evidence only**. Downstream adapter (`evidence_atoms.py`) normalizes to `EvidenceAtom`. No recommendations or summaries added at Reader layer.

### Reflector

**Before:** Rule-driven search refinement + partial re-read.  
**After:** Same re-search behavior preserved. **Added** deterministic `EvidenceAnalysisResult` at phase end:
- Contradictory evidence detection
- Missing / weak evidence identification
- Evidence clustering by theme
- Gap notes from Reader

Reflector still does **not** make business decisions.

### Reasoning Engine (new layer)

Inserted **after Reflector, before Synthesizer**. Deterministic v1 (`engine_version: v1`). Logical stages in `reasoning_engine_service.py`:

1. Observation clustering (from analysis)
2. Mechanism builder
3. Hypothesis generator (competing explanations per cluster)
4. Debate layer (support/contradict/predictions; selects best hypothesis per cluster)
5. Prediction engine
6. Founder decision engine
7. Business construction layer (10 component types)

No new LLM calls in v1 — architecture hook for future LLM-backed reasoning stages.

### Synthesizer

**Before:** Evidence → reasoning + narrative report in one LLM pass.  
**After:** **Communication only** for strategy. Receives `reasoning_output` in prompt via `<business_construction_intelligence>`. Still produces legacy `ValidationReport` fields for frontend compatibility. `business_construction` artifact attached server-side from Reasoning Engine output (not LLM-derived).

---

## Data Model Changes

### New internal models

All in `backend/app/schemas/business_construction.py` (see table above).

### Persisted changes

`ValidationReport.business_construction: BusinessConstructionArtifact | None`

- `null` for legacy reports
- Populated on all new pipeline runs after this change

### Unchanged

- `ExtractedEvidence`, `ReaderOutput` field shapes
- `ExperimentStatus` enum (Reasoning runs inside `RESEARCH_SYNTHESIZING` boundary before LLM call)
- Public API response shape (additive optional field only)
- Planner, Searcher implementations

---

## Pipeline Changes

### Old pipeline

```
Refinement
  → Planner
  → Searcher
  → Reader
  → Reflector
  → Synthesizer (reasoning + report)
  → Validation Report
```

### New pipeline

```
Refinement
  → Planner
  → Searcher
  → Reader (evidence atoms only)
  → Reflector (search refinement + evidence analysis)
  → Reasoning Engine (deterministic v1)
       ├─ Clustering
       ├─ Mechanisms
       ├─ Hypotheses
       ├─ Debate
       ├─ Predictions
       ├─ Founder decisions
       └─ Business components
  → Synthesizer (communication → Cognitive Validation Report)
  → Validation Report (+ business_construction artifact)
```

Effective data flow:

```
Evidence → Analysis → Reasoning → Mechanisms → Predictions
         → Founder Decisions → Business Construction → Report
```

---

## Backwards Compatibility

| Area | Compatible? | Notes |
|------|-------------|-------|
| Existing `ValidationReport` fields | Yes | All required fields unchanged |
| Frontend report viewer | Yes | Ignores unknown `business_construction` until UI built |
| `GET /experiments/{id}/validation-report` | Yes | Returns extra optional JSON field |
| Reader LLM prompt/schema | Yes | No changes |
| Reflector re-search behavior | Yes | Preserved |
| Eval scripts using `run_research_engine()` | Yes | Automatically get reasoning + artifact |
| Legacy reports in DB | Yes | `business_construction` is `null` |

### Breaking changes

**None.** All changes are additive.

---

## Future Extension Points

### Market Intelligence

Integrate after **Searcher** or as a Reasoning Engine sub-stage:
- Feed structured market signals into `EvidenceAnalysisResult.clusters`
- Enrich `Mechanism` statements with TAM/SAM proxies

### Distribution Engine

Hook into **Founder Decision Engine** and `BusinessComponentType.distribution_strategy`:
- Replace template actions with channel-specific playbooks
- Score distribution hypotheses in debate layer

### Founder Growth Network

Attach after **Business Construction Layer**:
- Map `validation_experiments` components to mentor/network intros
- Persist experiment outcomes back into `EvidenceAtom` for iterative runs

### LLM-backed Reasoning (v2)

Replace deterministic stages incrementally:
- Keep Pydantic contracts (`ReasoningEngineOutput`)
- Add prompts under `backend/app/llm/prompts/reasoning/`
- Route through `app.llm.client.complete_structured()` with phase=`reasoning_*`

### Optional `RESEARCH_REASONING` status

If frontend stepper should show reasoning explicitly, add enum + `research_phase_mapping` entry without changing service boundaries.

---

## Verification

```bash
cd backend
uv run pytest tests/services/test_reasoning_engine.py -q
uv run pytest tests/services/test_research_engine.py -q
```
