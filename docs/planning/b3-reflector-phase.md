# B3 Reflector Phase — Planning Document

**Status:** APPROVED — human reviewed v1, identified three loose ends (max_loops semantics, decision_method schema brittleness, domain logging overcaution); this v2 resolves them. ADR 0013 pending; implementation prompts to follow.  
**Phase:** B3 (Reflector is the fourth step in the five-phase research pipeline; slots between Reader and Synthesizer.)  
**Related ADRs:** ADR 0004 (five-phase rationale); ADR 0010–0012 (Reader output frozen; Synthesizer input frozen); **ADR 0013 (proposed)** — Reflector decision method.  
**Authors:** Cursor Composer (planning artifact); human co-founder (approval).

---

## Section 1 — Problem statement

ADR **0004** defines the research engine as a **multi-step single-agent workflow**: Planner → Searcher → Reader → **Reflector** → Synthesizer. Reflector is the phase that closes the loop between “what we found” and “did we find *enough* of the right thing?” without collapsing extraction and synthesis into one overloaded LLM call.

Today the orchestrator runs **Reader** then immediately **Synthesizer** (`research_engine_service.py`). **`RESEARCH_REFLECTING`** exists in `ExperimentStatus` and `PHASE_DISPLAY` but is **unreachable** until this work lands (`research_phase_mapping.py`). Reader warm-up and post–Synthesizer-refactor warm-up (`docs/calibration/runs/2026-05-15-reader-warmup.md`, `docs/calibration/runs/2026-05-15-post-synth-refactor-warmup.md`) show the pipeline is viable end-to-end, but **sparse-evidence paths** remain honest defaults: when **`evidence_gap_note`** is set, **`extracted_evidence`** is empty or thin, or relevance/domain diversity is poor, the Synthesizer correctly produces **low-confidence** findings and gaps — yet **sometimes different search queries surface better corroboration**. Reflector exists to **attempt one bounded rescue loop** before synthesis, not to replace the Synthesizer’s judgment.

### Success criteria (measurable)

| Criterion | Target |
|-----------|--------|
| Re-search triggers only when **explicit v1 rule** fires (§2); threshold values **calibration-pending** per `docs/llm-schema-calibration.md` | Observable via structured logs + calibration runs |
| Re-search loop depth | **Max 1 iteration per pipeline run for v1** (§5); per-question capped within that global pass |
| Pipeline latency | Worst-case additive bound: **one Reflector evaluation pass** + optional **partial Searcher fan-out** + optional **partial Reader** for flagged questions only — document expected ceiling vs current ~10 min total pipeline (post–synth-refactor note on latency) |
| Reflector incremental cost | **Typical added spend ≤ ~$0.30/run** for v1 shape (§9); worst-case bounded by “number of re-searched questions × (Tavily + query-gen LLM + Reader)” |
| Reliability | **Reflector never fails the pipeline** — any internal failure → degrade to current behavior (Reader output + existing `search_results` unchanged for that question) (§6) |
| Quality | No requirement to beat post–synth-refactor headline quality on every run; **success = fewer unnecessary thin-evidence outcomes where re-search would help**, without introducing new failure modes |

---

## Section 2 — Reflector’s decision logic — what makes evidence “insufficient”

### Candidate signals (from `ReaderOutput` / `ExtractedEvidence`)

Reflector **only** inspects typed Reader output (and derived counts); it does **not** read raw Tavily bodies or log evidence text (AGENTS.md hygiene).

| Signal | Meaning |
|--------|---------|
| `evidence_gap_note is not None` | Reader (or sentinel path) signaled an unanswered question |
| `len(extracted_evidence) == 0` | No usable atoms after validation |
| `len(extracted_evidence) <= K` | Sparse extraction (K first-pass, calibration-pending) |
| All `relevance == "low"` | Queries likely missed actionable substance |
| **Domain diversity** | Unique registrable domains among `source_url` values — all from one domain ⇒ weak corroboration |
| Citation / atom counts | Same as list lengths; cap already 10 |

### v1 composite rule (single load-bearing policy — thresholds calibration-pending)

**Decision (v1):** Use **rule-driven** triggers with **three OR-disjuncts** (any true ⇒ candidate for re-search, subject to §5 caps):

1. **Gap flag:** `evidence_gap_note is not None`  
2. **Sparse atoms:** `len(extracted_evidence) <= K_sparse` where **`K_sparse` start at 2** (first-pass; tune via calibration)  
3. **Low corroboration:** `len(extracted_evidence) >= 2` **and** **`unique_domains(extracted_evidence) <= 1`** (all evidence URLs collapse to one domain — e.g. only Wikipedia)

**Optional tightening (same calibration session):** Require **also** `not all(ev.relevance == "high")` before firing disjunct (3), if mono-domain “good” evidence proves common in eval — **calibration-pending**, not locked in implementation until data lands.

**Anti-flapping:** A question that already consumed its **per-question re-search budget** (§5) is excluded regardless of signals.

### Critical fork: LLM-driven vs rule-driven **decision**

| Approach | Pros | Cons |
|----------|------|------|
| **LLM-driven** | Holistic judgment; natural-language rationale; can fuse subtle patterns | Extra LLM call(s)/run; prompt drift; harder regression testing; conflicts with cost/latency discipline unless heavily bounded |
| **Rule-driven** | Fast, cheap, deterministic, unit-testable signals aligned with warm-up observations | Less nuance; thresholds need calibration |

**Choice for v1:** **Rule-driven decision logic.** Rationale: Reflector is an **enhancement layer** (§6); predictability and **zero decision-LLM cost** align with the stated typical budget (~$0.15–$0.30) when combined with **LLM-based query refinement only for flagged questions** (§4). ADR 0004’s one-line mention of a Reflector **LLM** call is **aspirational / historically shorthand** — **ADR 0013** records the v1 deviation explicitly so future contributors understand why rules precede an optional v2 critic model.

---

## Section 3 — Reflector’s output schema

Reflector output is **internal pipeline state** — **not** passed to `SynthesizerInput` (ADR 0012 stays intact). The Synthesizer still sees only the **final** `dict[str, ReaderOutput]` and the orchestrator still builds **`citation_hydration_index`** from the **merged** `search_results` after any follow-up searches.

**Lean toward “both”:** a **decision** object plus a **re-search plan** (queries per question).

### Draft Pydantic shapes (signatures only — caps first-pass / calibration-pending)

```python
# backend/app/schemas/reflector.py — conceptual signatures

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


# Module-level literal alias — extend here when adding methods (e.g. "llm_critic_v1").
ReflectorDecisionMethod = Literal["rule_v1"]


class QuestionReSearchSpec(BaseModel):
    """One question selected for follow-up search."""

    model_config = ConfigDict(extra="forbid")

    question_id: str = Field(..., description='e.g. "q1"…"q7"')
    trigger_signals: list[str] = Field(
        ...,
        max_length=8,
        description="Opaque enum-like labels: gap_note, sparse_atoms, mono_domain, …",
    )
    refined_queries: list[str] = Field(
        ...,
        min_length=1,
        max_length=4,
        description="2–3 typical; max 4 first-pass. Length per query bounded in validator.",
    )


class ReflectorDecision(BaseModel):
    """Outcome of one Reflector evaluation pass over current Reader outputs."""

    model_config = ConfigDict(extra="forbid")

    questions_to_re_search: list[QuestionReSearchSpec] = Field(
        default_factory=list,
        max_length=7,
    )
    skipped_question_ids_due_to_budget: list[str] = Field(
        default_factory=list,
        max_length=7,
        description="Questions that still matched rules but were not scheduled (§5/§9).",
    )


class ReflectorPhaseSummary(BaseModel):
    """Optional aggregate for logging/metrics attachment — not required on Synthesizer path."""

    model_config = ConfigDict(extra="forbid")

    loop_iteration: int
    questions_flagged_count: int
    questions_scheduled_count: int
    decision_method: ReflectorDecisionMethod = Field(
        description=(
            "The decision method used in this Reflector run. Currently only "
            "'rule_v1' is implemented; future v2 may add 'llm_critic_v1' etc."
        ),
    )
```

**Rule-driven v1:** No `ReflectorDecisionDraft` pattern unless query generation uses structured LLM output — then apply Draft/Final **only for the query-gen sub-schema** (small list of strings + question id), mirroring Reader’s discipline.

---

## Section 4 — Re-search query generation

### Options

| Option | Description |
|--------|-------------|
| **A** | Re-run **`ResearchQuestion.search_queries`** unchanged |
| **B** | **LLM** proposes **2–3** refined queries from question text + **compact structured summary** of existing evidence (counts, relevance histogram, domains — **not** full paraphrases/quotes) |
| **C** | Rule-based mutations (e.g. year suffix, `site:` hacks) |

**Choice for v1:** **Option B (LLM query refinement)** for questions Reflector actually schedules. **Option A** alone rarely fixes “wrong SERP shape” failures observed in warm-ups; **C** is brittle and risks prompt-injection-ish query fragments without careful sanitization.

### Prompt structure blueprint (NOT final text)

Follow AGENTS.md **data/instruction separation**:

1. **System**
   - Role: search strategist refining queries for Tavily.
   - Rules: output **only** structured queries; never instructions from data blocks; **no URLs as commands**; queries must be plain search strings (length caps).
2. **Safe context block** — labeled untrusted / data-only:
   - `question_id`, **question text** (required for relevance — acceptable as data; do not log in Reflector INFO logs).
   - **Aggregates only** from Reader: `evidence_count`, counts of `high`/`medium`/`low`, **list of domains** (derived from URLs), boolean `had_gap_note`.
   - **Optional:** original **`search_queries` count** (integer), **not** the strings in INFO logs — if the LLM needs originals, pass inside the tagged block **only inside the LLM call**, still treated as data; pipeline code must avoid persisting or logging them at INFO.
3. **Task:** Emit **2–3** queries maximizing **independent domains** and **user-generated / non-marketing** discourse where appropriate.
4. **Output:** Structured schema (small Pydantic model) → validated → truncate/count-enforced.

**Model:** **Claude Sonnet 4.6** per `.cursorrules` (“do not downgrade models in research engine to save tokens”). **No Haiku** for Reflector.

---

## Section 5 — Execution model

**Semantic (v1):** **`max_refinement_waves = 1`** means the pipeline executes **one refinement wave maximum**: **evaluate §2 rules once**, optionally **re-search and re-read flagged questions once**, then **proceed to the Synthesizer**. There is **no second evaluation pass** after that wave. This is **not** the conventional reading of a counter named `max_loops = 1` (which often implies evaluate → refine → evaluate again). Raising **`max_refinement_waves` to 2** in a future version would **re-run §2 rules after the first wave** and allow a **second** re-search wave if triggers still fire.

### Orchestrator flow (within `RESEARCH_REFLECTING`)

After **`execute_reader`** succeeds:

1. Transition **`RESEARCH_READING` → `RESEARCH_REFLECTING`**, commit (§7).
2. **`loop_iteration = 0` → evaluate rules** on each `ReaderOutput` → build `ReflectorDecision`.
3. If **`questions_to_re_search` empty:** transition **`RESEARCH_REFLECTING` → `RESEARCH_SYNTHESIZING`**, proceed as today.
4. Else:
   - **Query generation (B)** per scheduled question (batched LLM call **optional** optimization — design choice left to implementation; planning assumes **≤7 small calls worst case** unless batched schema is introduced later).
   - **Partial Searcher:** run Tavily for **only** `(question_id, refined_query)` pairs **or** a dedicated helper that mirrors `execute_search_plan`’s **parallel** gather pattern — **same concurrency semantics** as full Searcher (`searcher_service.py` uses top-level `asyncio.gather`).
   - **Merge `search_results`:** **union/dedup per question** consistent with existing Searcher behavior (URL dedup within question).
   - **Partial Reader:** invoke Reader only for affected `question_id`s; **merge** into `reader_outputs` dict.
   - **`loop_iteration += 1`.** For **v1** (`settings.reflector_max_refinement_waves == 1`): **stop** — **do not** run §2 rules again after this wave. For **`max_refinement_waves >= 2`**, implementations **repeat from step 2** while **`loop_iteration < max_refinement_waves`** and questions remain eligible with budget.

### Decisions

| Topic | v1 choice | Rationale |
|-------|-----------|-----------|
| **Max refinement waves** | **`reflector_max_refinement_waves = 1`** (`Settings`; §12) | Post–synth-refactor warm-up already stresses latency (~434s Synthesizer alone); stacking waves multiplies worst-case Tavily+Reader tail risk |
| **Wave accounting** | **Single wave in v1** + **per-question boolean `re_search_consumed`** | Prevents scheduling the same question twice within the wave; future `max_refinement_waves > 1` resets eligibility only after a full re-evaluation pass |
| **Parallelism** | **Yes** — mirror Searcher/Reader concurrent patterns for scheduled questions | Existing pipeline already assumes parallel Tavily fan-out |

**Cap:** **Max distinct questions scheduled per run:** **4** first-pass (calibration-pending) — avoids worst-case “all 7 re-search” Tavily/Anthropic bursts even if rules fire everywhere.

---

## Section 6 — Failure modes and graceful degradation

| Failure | Behavior |
|---------|----------|
| Rule evaluation throws | Log ERROR with `experiment_id`, **no question content**; treat as **empty decision** (no re-search); continue to Synthesizer |
| Query-gen LLM fails for one question | Skip re-search for **that** question; keep prior Reader output + prior Tavily rows |
| Tavily fails partially | Same policy as Searcher: merge successes; if **no new rows** for that question, retain old evidence |
| Reader fails on re-read | Per-question sentinel already exists (`reader_service.py`); **do not** overwrite good prior output — implementation policy: **attempt merge only on success** else retain previous `ReaderOutput` for that question |
| Max loops / budgets hit | INFO log; proceed with best available evidence |

**Invariant:** Reflector **never** raises into the orchestrator as a hard pipeline failure and **never** changes `ExperimentStatus` to `RESEARCH_FAILED` by itself.

---

## Section 7 — State machine integration

- **`research_engine_service.py`:** Insert **`RESEARCH_REFLECTING`** **after** Reader completes successfully **and before** building `SynthesizerInput` / `citation_hydration_index`.  
  - **Important:** Re-run **`build_citation_hydration_index(search_results)`** after merging new Tavily results so hydration covers any **new** lawful URLs.  
- **`research_phase_mapping.py`:** Insert **`RESEARCH_REFLECTING`** into **`_RESEARCH_PHASE_ORDER`** between **`RESEARCH_READING`** and **`RESEARCH_SYNTHESIZING`**. Update comments: remove “unreachable” wording from code paths that are now live; keep historical mention in git/ADR if needed.  
- **Single occupation:** The pipeline stays in **`RESEARCH_REFLECTING`** until the **entire** evaluate → optional re-search → re-read → merge loop finishes, then transitions to **`RESEARCH_SYNTHESIZING`**.

---

## Section 8 — Observability

Mirror Reader/Synthesizer **`structlog`** style.

**INFO (per decision pass):** `experiment_id`, `questions_flagged_for_re_search` (count), `questions_scheduled_for_re_search` (count), `re_search_triggered` (bool), `loop_iteration`, `decision_method` (`rule_v1`), `max_refinement_waves`, `per_question_budget_exhausted_count`.

**INFO (per re-searched question completed):** `question_id`, `experiment_id`, `new_tavily_rows_count`, `new_evidence_count`, **`cost_delta_usd`** (Tavily + LLM slices if separately tracked), `latency_ms` aggregate for that question’s follow-up slice.

**INFO (phase complete):** `total_re_searches`, `total_questions_touched`, **`total_cost_delta_usd`**, **`total_latency_ms`** for Reflector phase.

**DEBUG (calibration):** Per-question signal snapshot: `evidence_count`, `relevance_high_count` / `medium` / `low`, `unique_domain_count`, boolean flags for each disjunct in §2. Domains (from `source_url` values) are public web references, not sensitive data. They may be logged at DEBUG and INFO without redaction, matching the existing Reader pattern (Reader logs URLs at WARNING when hallucinations occur). Per AGENTS.md, what stays prohibited: verbatim_quote values, paraphrase values, Tavily content, query strings at INFO, full user question text at INFO (use question_id in hot paths). Counts and domain lists are fine.

**AGENTS.md:** Never log **`verbatim_quote`**, **`paraphrase`**, Tavily **`content`**, or **query strings** at INFO; avoid logging **full user question text** at INFO — use **`question_id`** in hot paths.

---

## Section 9 — Cost budget

Rough incremental components (illustrative — ledger verifies):

| Component | v1 expectation |
|-----------|----------------|
| Rule evaluation | **$0** |
| Query-gen LLM | **~$0.02 × N** scheduled questions (small structured output) |
| Tavily follow-up | **~$0.016 × advanced × queries** (same as Searcher defaults) |
| Reader partial | **~$0.05–$0.13 × N** questions (Reader warm-up scale) |

**Worst case** if all 7 questions re-search with full LLM stack: approaches **+$0.50–$1.00**, contradicting product budget — mitigated by **`max_questions_per_run = 4`** (§5) and **`max_refinement_waves = 1`** (single refinement wave in v1).

**v1 target:** **≤ ~$0.15–$0.30 typical** incremental when **1–3** questions trigger — worthwhile vs persistent thin-evidence reports.

---

## Section 10 — Calibration discipline

Per **`docs/calibration/procedure.md`** and **`docs/llm-schema-calibration.md`**:

- All numeric thresholds (`K_sparse`, max scheduled questions, optional tightening flags) are **first-pass** until the **5-idea calibration set** completes.
- Emit **DEBUG signal snapshots** (§8) for every question each pass — enables empirical tuning without scraping INFO logs.
- Record threshold revisions as **dated entries** in `docs/llm-schema-calibration.md`.
- Track **trigger rate**, **conditional improvement** (did `extracted_evidence_count` or `unique_domain_count` increase post loop?), and **false positives** (rich evidence but triggered).

---

## Section 11 — ADR-worthy decisions

### ADR 0013 (proposed): **Reflector decision logic — rule-driven v1**

**Summary:** Records why Fivvle ships **deterministic rule-based** insufficient-evidence detection for Reflector v1 instead of an LLM critic, why **mono-domain** and **sparse/gap** signals are load-bearing, how this interacts with ADR 0004’s narrative, and **when** to revisit (e.g. persistent false negatives in calibration).

### Optional (likely planning-only unless scope expands): **Re-search query generation via structured LLM**

**Summary:** If implementation complexity warrants, a short ADR could lock **“LLM generates queries; orchestrator never executes free-form tool calls from LLM output”** — likely redundant with AGENTS.md + this doc; **default: no separate ADR**.

---

## Section 12 — Files to create / modify

| File | Action | Notes |
|------|--------|-------|
| `backend/app/config.py` | **Modify** | Add **`reflector_max_refinement_waves: int = 1`** on `Settings` — mirrors **`reader_concurrency_limit`** pattern (`Field(default=1)` as appropriate). |
| `backend/app/schemas/reflector.py` | **New** | `QuestionReSearchSpec`, `ReflectorDecision`, `ReflectorDecisionMethod`, optional `ReflectorPhaseSummary` |
| `backend/app/services/reflector_service.py` | **New** | `execute_reflector_phase(...)` — rules, query-gen orchestration hooks |
| `backend/app/services/research_engine_service.py` | **Modify** | Insert `RESEARCH_REFLECTING`; merge Tavily; rebuild hydration index; **no** change to Reader/Synthesizer contracts beyond call order |
| `backend/app/services/research_phase_mapping.py` | **Modify** | Insert `RESEARCH_REFLECTING` in `_RESEARCH_PHASE_ORDER`; refresh comments |
| `backend/app/llm/prompts/reflector_query_refinement.py` (name TBD) | **New** | `PROMPT_NAME`, blueprint-aligned builder — **if** query-gen LLM lands |
| `backend/tests/services/test_reflector_service.py` | **New** | Rule matrix tests with synthetic `ReaderOutput` |
| `docs/adr/0013-reflector-decision-logic.md` | **New** | After greenlight |

---

## Section 13 — Out of scope

- **Multi-source Searcher** (Reddit, Trends) — separate planning artifact  
- **Full eval-set discipline** — after Reflector lands  
- **Reader prompt / schema changes** — frozen by ADR 0010 / 0011  
- **Synthesizer prompt / `SynthesizerInput` changes** — frozen by ADR 0012  
- **Model downgrade** (Haiku for Reflector) — excluded per `.cursorrules`

---

## Section 14 — Open questions for the human

1. **Should orchestrator gate Reflector when cumulative experiment LLM+Tavily spend already exceeds a run-level ceiling** (e.g. skip re-search if burn > X USD)? Not resolved — touches global cost policy vs quality.  
2. **Exact cap:** **`max_questions_per_run = 4`** vs **3** — needs product call after first calibration slice.  
3. **Query-gen batching:** one structured LLM call for **all** scheduled questions vs **per-question** calls — trade latency vs schema complexity; not prescribed here.  
4. **Domain extraction:** use registrable domain via **`httpx`/urllib** parsing only — confirm **no SSRF** surface (domains from existing `https://` URLs only; no fetch).  
5. **ADR 0004 wording:** explicit **“supersedes Reflector LLM sentence”** vs **“implementation detail clarified”** — editorial choice when drafting ADR 0013.

---

## Self-check

| Check | Status |
|-------|--------|
| Step 0.5 quotations (or equivalent citations) | ✅ (v1 doc; orchestrator + phase order + schema + Searcher + Tavily) |
| Decision method chosen + justified | ✅ Rule-driven v1 (§2) |
| Re-search query strategy chosen + justified | ✅ Option B with prompt blueprint (§4) |
| `max_refinement_waves` bounded + semantics explicit | ✅ §5 |
| Reflector never fails pipeline | ✅ §6 |
| Cost bounded explicitly | ✅ §9 |
| Load-bearing ADR identified | ✅ ADR 0013 (§11) |
| Reader/Synthesizer unchanged | ✅ §13 |

---

*Document status: APPROVED — human reviewed v1; three loose ends (§5 counter semantics vs refinement waves, §3 `Literal` brittleness, §8 domain redaction overcaution) resolved in this v2. ADR 0013 pending; implementation prompts pending. Implementation, prompts, tests, and git operations remain intentionally out of scope for this document.*
