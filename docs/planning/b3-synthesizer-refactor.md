# B3 Synthesizer Refactor — Planning Document

**Status:** APPROVED — human reviewed v1, identified four loose ends (citation hydration, competitor guard, quote guard, §14 taxonomy questions); this v2 resolves them. ADR 0012 pending; implementation prompts to follow.  
**Output path:** `docs/planning/b3-synthesizer-refactor.md` (this file).  
**Scope:** Synthesizer input contract, prompt redesign blueprint, guards, service/orchestrator behavior, calibration hooks, and implementation roadmap. Does **not** cover Reflector, multi-source Searcher, eval-set discipline, or deployment.

---

## Section 1 — Problem statement

The B2/B3-transitional Synthesizer still ingests **raw Tavily snippets** (`search_results_by_question`), forcing a single LLM pass to do evidence extraction and cross-question synthesis together. That design caused:

- **May 14 smoke run — citation hallucination:** ~123k-token-class raw-snippet inputs overload the model; citation fabrication is a predictable failure mode when extraction and synthesis are fused.
- **May 15 Tier 1 rate-limit failure — hard operational blocker:** a mini-calibration attempt failed at the Synthesizer because **~47k input tokens** exceeded Anthropic Tier 1’s **30k input tokens/min** ceiling. Cost and latency compound the issue, but rate limits make the old shape **non-viable** on the current tier.

**ADR 0004** intended a **five-phase** pipeline: Planner → Searcher → **Reader/Extractor** → Reflector → Synthesizer. Reader is now implemented; the Synthesizer must complete the intended hand-off: **consume structured, per-question `ReaderOutput`**, matching the phase boundary ADR 0010 describes as an architectural contract, not a cosmetic split.

### Success criteria (measurable)

| Criterion | Target |
|-----------|--------|
| Synthesizer **input** token count | Drop from **~47k** (pre-refactor, rate-limit failure) toward **≤25k** typical |
| Synthesizer **cost** per run | Drop from **~$0.30** toward **≤$0.20** (calibration will confirm) |
| **ValidationReport** quality | No regression: real URLs, real competitors, coherent `Finding`s / `QuestionFindings` |
| **Tier 1 reliability** | Synthesizer runs without systematic input-token rate-limit failures |

---

## Section 2 — Input contract: the new SynthesizerInput

### Decisions

- **`refined_idea: RefinedIdea`** — **unchanged** (founder context, risks, recommendation anchoring).
- **`research_plan: ResearchPlan`** — **unchanged** (question ids/text, `notes_for_synthesizer`, structural template for `QuestionFindings`).
- **`reader_outputs: dict[str, ReaderOutput]`** — **NEW**, keyed by `question_id` (`"q1"`…`"q7"`), one `ReaderOutput` per plan question after the Reader phase. This is the **single** evidence surface for the Synthesizer LLM prompt.
- **`search_results_by_question: dict[str, list[TavilyResultForPrompt]]`** — **REMOVE**. **No fallback.** The Synthesizer does not consume raw Tavily snippets in any mode.

### SynthesizerInput: four fields only (locked)

**`SynthesizerInput` contains exactly these four fields:** `refined_idea`, `research_plan`, `reader_outputs`, `rubric_version`. It does **not** contain citation-hydration metadata, URL indices, or any Searcher payload. That keeps the persisted/transport shape identical to “what the prompt is built from.”

### Why remove raw Tavily entirely (no fallback)

Per **Reader planning doc §15 Decision 1** and the **Q1 framing** for this refactor: a raw-snippet fallback would force **two prompt modes** (pre-Reader vs post-Reader), double maintenance, and let the system “cheat” past the architectural split ADR 0010 encodes as a **schema-level contract** between extraction and synthesis. Single-source input on `ReaderOutput` keeps the pipeline honest: if Reader output is sparse, the Synthesizer must reflect that in **low-confidence findings and `evidence_gap`**, not by re-opening 70+ snippets. It also **forces** the orchestrator and cost profile to match the B3 design—Reader’s compression is load-bearing for both **capex** and **rate limits**.

### Orchestrator scope at `synthesize_report()` (today)

At the call site, the orchestrator already has in scope: **`refined_idea`**, **`research_plan`**, **`search_results`** (from Searcher), and **`reader_outputs`** (from `execute_reader()`). Post-refactor, **`build_synthesizer_input(...)`** fills only the four-field `SynthesizerInput`. **`search_results`** stays in scope for building **`citation_hydration_index`** (below)—**never** placed on `SynthesizerInput`.

### Approach B — Citation hydration via orchestrator-built index (separate parameter)

**Decision (v2):** **`Citation`** requires **`title`** (min 1, max 300) and **`source_domain`** (max 100) per `backend/app/schemas/validation_report.py`. **`ExtractedEvidence`** has **`source_url` only**; **Reader schema stays frozen**—no `source_title` or Reader changes.

The orchestrator builds a **server-side** map from Searcher Tavily URLs to display metadata:

- **Built from:** `search_results` (`dict[str, list[TavilyResult]]`) after Reader completes, **before** `synthesize_report()`.
- **Mechanical join:** iterate every `TavilyResult` in every question’s list; for each result, take **`url`**, **`title`**, and **`source_domain`** derived the same way as today’s synthesizer (`_extract_domain(url)` or equivalent). **Deduplicate by URL** (last-writer-wins or first-wins—implementation must be deterministic); produce **`dict[str, CitationHydrationEntry]`**.
- **Passed to:** `synthesize_report(..., citation_hydration_index=...)` as a **separate keyword argument** — **not** a field on `SynthesizerInput`.
- **Never serialized** into the LLM user prompt. Used **only** inside **`_hydrate_draft()`** in `synthesizer_service.py` to populate **`Citation.title`** and **`Citation.source_domain`** for final persistence.

**Architectural rationale:** The Reader/Synthesizer **LLM** contract stays clean (prompt sees **Reader output only**). Hydration is a **mechanical server-side join** between (a) LLM-emitted citation URLs allowed by the evidence set and (b) Tavily metadata the orchestrator already holds. Separating **`SynthesizerInput`** from **`citation_hydration_index`** matches the mental model: *LLM input* vs *post-parse plumbing*.

**Implementation note:** `CitationHydrationEntry` may use looser upper bounds than `Citation` for the raw Tavily row; when constructing a **`Citation`**, values must satisfy `validation_report.py` (truncate or normalize if needed—first-pass).

Draft shape:

```python
class CitationHydrationEntry(BaseModel):
    """Server-side URL → metadata map for Citation hydration.

    Built by the orchestrator from Searcher's TavilyResults. Passed to
    synthesize_report() as a separate parameter (NOT a field on SynthesizerInput).
    NEVER serialized into the LLM user prompt. Used only by _hydrate_draft()
    to resolve URL → title/source_domain for the final Citation objects.
    """

    model_config = ConfigDict(extra="forbid")

    title: str = Field(..., max_length=500, description="Tavily result title")
    source_domain: str = Field(..., max_length=255, description="Parsed domain")
```

### How `SynthesizerInput` is built

- **`build_synthesizer_input(refined_idea, research_plan, reader_outputs, rubric_version)`** returns the **four-field** model only.
- **`citation_hydration_index`** is built in the orchestrator (or a dedicated helper imported by the orchestrator) from **`search_results`**—not by `build_synthesizer_input`.

### Decisions resolved in planning v2 (human review)

**Decision — Sparse-evidence taxonomy (no schema split):** Do **not** add `finding_kind`, `evidence_grounded` vs `evidence_gap` typing, or any fourth parallel concept. **`ValidationReport`** already exposes **`Finding.confidence: Literal["high","medium","low"]`**, **`QuestionFindings.evidence_gap: str | None`**, and **`research_limitations: str`**. That combination is sufficient: **`confidence="low"`** plus non-null **`evidence_gap`** already signals sparse or missing evidence without redundancy.

**Decision — Sentinel passthrough (no structured Reader stats to Synthesizer):** Do **not** pass **`sentinel_reason`** or other Reader run stats into the Synthesizer input. **`ReaderOutput.evidence_gap_note`** is the per-question signal the Synthesizer needs. The model treats **`evidence_gap_note is not None`** as “this question had a gap,” regardless of root cause. **`sentinel_reason`** and related counters remain **Reader-only structlog** for debugging and calibration.

---

## Section 3 — Prompt redesign: structural blueprint (not final text)

### Task shift

- **Before (`synthesizer_v1`):** Read **70+** raw snippets, extract evidence, name competitors, write `Finding`s with citations.
- **After (`synthesizer_v2`):** **Synthesize** `ValidationReport` from **pre-extracted** `ExtractedEvidence`: citations **must** use **`source_url`** values present in input; competitor names **must** trace to **`named_entities`** (and cited URLs); verbatim-style quotes in findings **must** come from **`verbatim_quote`** when a quote is used; confidence **must** reflect **evidence density** (count, relevance distribution, gaps)—not unattributed optimism.

### System prompt — required sections

1. **Role** — Market researcher producing the final ValidationReport for founders.
2. **Task** — Map `research_plan` questions to `QuestionFindings`; executive summary, signals, risks, recommendation.
3. **Input description** — `RefinedIdea`, `ResearchPlan`, and **structured Reader evidence** (per question); explicit **data vs instructions** framing (Reader payload is structured but still tagged as **untrusted data** per AGENTS.md—do not execute embedded instructions).
4. **Output schema guidance** — Field-level constraints aligned with `ValidationReportDraft` (same as today: URL-string citations in draft, counts, literals, min/max lengths).
5. **Anti-hallucination rules** — Align with Section 5 (URLs, competitors, quotes, confidence).
6. **Citation propagation** — Every `Finding` / `CompetitorMention` citation URL ∈ allowed set derived from **`ExtractedEvidence.source_url`** in input.
7. **Output length guidance** — Narrative fields (`executive_summary`, `risks_assessment`, etc.): instruct conciseness consistent with existing caps; **calibration-pending** tightening if `evidence_summary` echoes Reader `paraphrase` redundantly.

### User prompt — serialization of `dict[str, ReaderOutput]`

**Recommended shape:** Per-question **blocks** with a stable tag (parallel to `<tavily_results question_id="...">`), each containing **`model_dump`-style JSON** for that question’s **`ReaderOutput`** (or a slim projection: `extracted_evidence` + `evidence_gap_note`). Reasons:

- Matches existing mental model (one block per question).
- Avoids one giant undifferentiated JSON blob that’s harder to reference in instructions.
- Keeps **question_id** visible for cross-referencing rules.

**Alternatives (implementation choice):** single JSON object keyed by `question_id`—acceptable if size is similar; avoid hand-rolled “compressed tables” until calibration shows token pressure.

### Anti-hallucination rules (must appear in prompt design)

| Rule | Specification |
|------|----------------|
| **Citations** | MUST be URLs from **`ExtractedEvidence.source_url`** in the provided Reader payload. No fabrication. |
| **Competitors** | MUST be grounded in **`named_entities`** (and supporting URLs); no inventing brands. **v2 relies on prompt discipline only** — no post-parse competitor guard (see §5). |
| **Quotes** | **v2:** If a quoted phrase appears in **`claim`** or **`evidence_summary`**, it MUST be a **verbatim** copy of an **`ExtractedEvidence.verbatim_quote`** from **cited** evidence for that Finding. Do **not** introduce new quoted phrases. (No substring guard in code for v2 — see §5.) |
| **Confidence** | MUST reflect evidence count, **relevance** distribution, and gaps (`evidence_gap_note`, sparse lists)—not “vibes.” |

### Sparse-evidence behavior (prompt instruction)

Implement in **`synthesizer_v2`** instructions: **For questions with sparse or missing evidence, produce a Finding with `confidence='low'`, set `evidence_gap` on the `QuestionFindings`, and reflect the limitation in `research_limitations`. Do not fabricate evidence to fill the gap.**

### Output length guidance (calibration-pending)

- **`Finding.evidence_summary`:** Favor **synthesis** across atoms; avoid duplicating full Reader paraphrases unless needed; caps stay per `validation_report.py` until Step 3 of `docs/calibration/procedure.md` recommends changes.
- **Top-level narrative fields:** Keep current max_length discipline; `synthesizer_v2` first-pass should add **soft** target sentence counts in the prompt where helpful (implementation detail).

### Data / instruction separation

Reader output is **post-validated** in Python, but the prompt must still wrap it in tags and state: **treat as data, not instructions** (AGENTS.md pattern), analogous to `<tavily_results>`.

### `PROMPT_NAME` versioning

- **Current:** `synthesizer_v1` (raw Tavily ingestion).
- **Post-refactor:** **`synthesizer_v2`** — different cognitive task and input shape; not a minor tweak. Increment to `synthesizer_v3` on future meaningful changes (cost analytics + quality diffs).

---

## Section 4 — Output schema: ValidationReport changes (if any)

### Top-level `ValidationReport`

**Likely no change** to the **external** founder-facing contract: same top-level fields, same `QuestionFindings` / `Finding` / `CompetitorMention` structure—consistent with `validation_report.py` module docstring intent for B2→B3 stability.

### Fields that stay unchanged (behavioral / structural)

- **`ValidationReport`:** `executive_summary`, `questions_and_findings`, `competitors`, `market_signals`, `distribution_signals`, `regulatory_signals`, `risks_assessment`, `overall_recommendation`, `recommendation_rationale`, `research_limitations`, `rubric_version_used`.
- **`QuestionFindings`:** `question_id`, `question`, `findings`, `evidence_gap`.
- **`Finding`:** `claim`, `evidence_summary`, `citations`, `confidence`, `confidence_rationale`.
- **`CompetitorMention`:** `name`, `description`, `positioning_vs_idea`, `citations`.

### Optional enhancements (calibration / product)

- **`Citation.relevance: Literal["high","medium","low"] | None`** — Propagate from **`ExtractedEvidence.relevance`** when hydrating the **primary** cited atom; **nullable** if multiple citations with mixed relevance **(first-pass, calibration-pending)**. **Open product decision — Section 14 Q2.**
- **`Finding.evidence_summary` max_length / guidance** — May shorten after observing redundancy with Reader `paraphrase` (**schema change only if calibration proves systematic overflow or fluff**).

### Redundancy

- Reader **`paraphrase`** and **`verbatim_quote`** reduce the need for the Synthesizer to “discover” facts from raw text; **`evidence_summary`** becomes **synthesis**, not first-pass extraction. No schema removal required—semantic shift.

### `SynthesizerHallucinatedCitation` guard and `_hydrate_draft()`

- **URL allow-list (LLM output validation):**  
  **`allowed_urls = {ev.source_url for ro in synth_input.reader_outputs.values() for ev in ro.extracted_evidence}`**  
  Any draft citation URL **not** in **`allowed_urls`** → **`SynthesizerHallucinatedCitation`** (hard-fail). **`allowed_urls`** is a subset of URLs that appeared in Searcher results (Reader guarantees each **`source_url`** came from provided Tavily rows).

- **Designated hydration site:** **`_hydrate_draft(draft, synth_input, citation_hydration_index)`** (signature to be wired in implementation) resolves each allowed URL to **`Citation.title`** and **`Citation.source_domain`** using **`citation_hydration_index[url]`**. **`accessed_at`** remains synthesis-time UTC (current service behavior) unless a future change threads searcher time through the index.

- **Consistency:** The orchestrator builds **`citation_hydration_index`** from **all** `search_results` URLs, so every URL Reader could lawfully emit should have an entry. If a URL passes **`allowed_urls`** but is missing from the index, treat as an **implementation bug** or **hard-fail** consistent with quality (same class as hallucination—never ship a half-hydrated citation).

### Draft Pydantic changes (only if relevance propagation is adopted)

```python
# In Citation (final only; Draft stays URL strings)
relevance: Literal["high", "medium", "low"] | None = Field(
    default=None,
    description=(
        "Optional: propagated from ExtractedEvidence.relevance for the primary "
        "evidence atom when hydrating citations; calibration-pending."
    ),
)
```

If the team prefers **no** surface relevance in the API, **omit** this field and keep relevance only in internal logs.

---

## Section 5 — Hallucination guards: updated logic

### URL guard (hard-fail)

- **Allowed set:** `{ev.source_url for ro in reader_outputs.values() for ev in ro.extracted_evidence}` (equivalently from `synth_input.reader_outputs`).
- **Behavior:** If the LLM emits a URL **not** in this set → **`SynthesizerHallucinatedCitation`**. **Rationale:** Synthesizer is the **last** LLM step; a fake URL in the shipped report is the worst failure (Reader planning doc §8.4 contrast).
- **Hydration:** After URL validation, **`_hydrate_draft()`** uses **`citation_hydration_index`** (Section 2 / Section 6). The allow-list is a **subset** of URLs present in **`search_results`**; the index is built from **full** `search_results`, so keys cover all lawful evidence URLs.

### Quote guard — **v2: prompt-only** (named escalation to v3)

**Decision:** For **`synthesizer_v2`**, there is **no** post-parse quote substring guard. Enforcement is:

1. **Prompt instruction:** If the model includes a **quoted phrase** in **`claim`** or **`evidence_summary`**, it MUST be a **verbatim** copy of an **`ExtractedEvidence.verbatim_quote`** value from the **cited** evidence for that Finding. Do **not** introduce new quoted phrases.
2. **Reader precedent:** Reader already nulls **`verbatim_quote`** when substring validation fails; the Synthesizer sees a **clean** quote set from validated evidence.
3. **Calibration gate (first-pass, per `docs/llm-schema-calibration.md`):** During the **first** `synthesizer_v2` calibration session, audit **≥5** completed reports. If **quote-fabrication rate** (Findings that contain quotes not traceable to **`verbatim_quote`**, as a share of Findings that contain quotes) **exceeds 5%**, escalate to a **v3** post-parse substring guard in a follow-up implementation. **5%** is first-pass and subject to the same calibration discipline as other thresholds.

### Competitor guard — **v2: none (Option B)**

**Decision:** **No** post-parse competitor-name guard in **`synthesizer_v2`**. Rely on:

- **Prompt discipline:** `CompetitorMention.name` MUST trace to **`named_entities`** (and citations) in the Reader evidence; do not invent brands.
- **Calibration review:** **`named_entities`** is already the extraction-phase source of truth.

**v3 trigger (documentary only):** If a future calibration session shows **competitor invention rate > 5%** (defined as competitor names in the final report not supported by cited evidence / named entities), add a **token-intersection** or other guard in a later version—**not** in this refactor. **Rationale:** Legitimate naming variance (“Salesforce” vs “Salesforce.com” vs “SFDC”) makes token guards false-positive-prone without calibration data; URL fabrication is already covered by the hard-fail URL guard.

| Guard | v2 behavior | Rationale |
|-------|-------------|-----------|
| URL | **Hard-fail** | Last phase; founder trust; citation fabrication |
| Quote | **Prompt-only**; v3 guard if calibration > **5%** quote drift | Reader cleaned quotes; avoid brittle parsing in v2 |
| Competitor | **None**; prompt + calibration; v3 if invention > **5%** | Naming variance; no calibration baseline yet |

---

## Section 6 — Service refactor (`synthesizer_service.py`)

### Signature

**`synthesize_report()`** gains **`citation_hydration_index`** as an explicit parameter (not on `SynthesizerInput`):

```python
async def synthesize_report(
    db: AsyncSession,
    synth_input: SynthesizerInput,
    citation_hydration_index: dict[str, CitationHydrationEntry],
    experiment_id: UUID | None = None,
) -> ValidationReport:
```

**`_hydrate_draft()`** is the **designated** function that consumes **`citation_hydration_index`** to populate **`Citation.title`** and **`Citation.source_domain`** (and **`accessed_at`** as today). It does **not** read raw Tavily snippets.

### Control flow

1. **Log** aggregates: `question_count`, **`total_extracted_evidence`**, questions with **`evidence_gap_note`**, **`rubric_version`**, **`experiment_id`** (no verbatim content).
2. **`build_synthesizer_user_prompt(synth_input)`** — uses **`reader_outputs`**, **not** Tavily excerpts.
3. **`complete_structured(..., response_model=ValidationReportDraft, prompt_name=synthesizer_v2, phase="synthesizer")`** — same client path; **`max_retries`** stays aligned with production (currently **2** in code—do not change silently without noting in ADR/calibration).
4. **URL guard** on draft citations against **`allowed_urls`** from **`synth_input.reader_outputs`**.
5. **`_hydrate_draft(draft, synth_input, citation_hydration_index)`** — build **`Citation`** objects from index lookups.
6. **Return** `ValidationReport`.

### Failure modes

| Condition | Behavior |
|-----------|----------|
| **Empty Reader evidence across all questions** | **Should not occur** if orchestrator keeps **`ReaderTotalFailure`** (total_extractions == 0). **Defense-in-depth:** treat as **`ValueError`** or explicit orchestrator guard; do not call Synthesizer. |
| **LLM failure / Instructor retries exhausted** | Propagate (**`InstructorRetryException`** / provider errors); orchestrator → `RESEARCH_FAILED`. |
| **Hallucinated URL** | **`SynthesizerHallucinatedCitation`** → orchestrator **`RESEARCH_FAILED`**. |

### Calibration logging (`docs/calibration/procedure.md` Step 2)

**DEBUG:** `len()` for every **`max_length`/`min_length`**-bounded **Synthesizer-emitted** field in the **parsed draft** path (mirror Reader pattern): e.g. `executive_summary`, each `Finding` field, `questions_and_findings` counts, **`competitors`** fields, signals, **`research_limitations`**, etc.—**without logging content**.

### Structured observability (Reader §9 analog)

Single **INFO** completion event with (non-exhaustive): `experiment_id`, `phase="synthesizer"`, **`prompt_name`**, **`total_extracted_evidence_in_input`**, **`questions_with_gap_note`**, **`sentinel_question_count`** (e.g. infer from empty evidence + non-null gap note when useful for dashboards), **`finding_count`**, **`competitor_count`**, **`total_citation_count`**, **`cost_usd`**, **`prompt_tokens`**, **`completion_tokens`**, **`latency_ms`**; **`recommendation`**.

### Cost tracking

- **`complete_structured`** continues to write **`LLMCall`** via `app.llm.client` — **no change** to “one row per call” expectation; **`prompt_name`** becomes **`synthesizer_v2`**.

---

## Section 7 — Orchestrator wiring (`research_engine_service.py`)

- **Today:** After Reader, `build_synthesizer_input(..., tavily_results=search_results)` and `synthesize_report(...)` — **Reader output unused** (comment acknowledges pending refactor).
- **After:**
  1. `synth_input = build_synthesizer_input(refined_idea, research_plan, reader_outputs, rubric_version)` — **four fields only**.
  2. `citation_hydration_index = build_citation_hydration_index(search_results)` — iterate all questions’ **`TavilyResult`** lists, for each `(url, title)` compute **`source_domain`** (same rules as synthesizer `_extract_domain`), **dedupe by `url`**, produce **`dict[str, CitationHydrationEntry]`**.
  3. `await synthesize_report(db=session, synth_input=synth_input, citation_hydration_index=citation_hydration_index, experiment_id=experiment_id)`.

**`search_results`** remains in orchestrator scope at the call site (confirmed in v1 Step 0.5(d))—no new fetches.

- **State machine:** **No change** — `RESEARCH_READING` → `RESEARCH_SYNTHESIZING` already exists.

---

## Section 8 — Token budget and cost projections

### Warm-up data (`docs/calibration/runs/2026-05-15-reader-warmup.md`)

- **Synthesizer (successful run):** **$0.304** (1 call), **latency ~226 s**. Token breakdown for that call is **not recorded** in the artifact.
- **Mini-calibration (failed):** Synthesizer **~47k input tokens** → Tier 1 **30k input tokens/min** limit hit.
- **Reader (same warm-up):** **7 calls**, sum of **`completion_tokens`** from table =
  **1,075 + 1,331 + 1,483 + 1,519 + 2,054 + 1,644 + 4,112 = **13,218** output tokens**.

### Projection — Synthesizer input

- Remove **raw Tavily JSON** (~70 × large `content_excerpt`) from user prompt.
- Replace with **structured Reader JSON**: bounded by **`≤10`** evidence atoms × (**`paraphrase` ≤600** + **`verbatim_quote` ≤600** + **`named_entities`**) × 7 questions, plus **`RefinedIdea` + `ResearchPlan` JSON**.
- **Order-of-magnitude:** Reader **completion** totals ~13k tokens in one observed run; **input** to Synthesizer is dominated by serialized evidence **plus** idea/plan. **Rough ceiling** in mid–high tens of kb **before** refactor was ~47k; **after**, expect **~20–25k** typical (explicitly **calibration-pending**).

### Projection — cost

- **Current:** ~**$0.304** per Synthesizer call (warm-up) with huge input.
- **Post-refactor:** Input tokens drop materially → **roughly proportional** Anthropic billed input reduction on that call; combined with unchanged **output** (~large structured report), **target ~$0.12–0.18** per Synthesizer call is plausible — **confirm on first calibration run**.
- **Pipeline:** Warm-up **total ~$1.15** with Reader **$0.454** + Synthesizer **$0.304**. Post-refactor, Synthesizer cost falls; **total** toward **~$0.50–0.80** per run absent new failures — **calibration verifies**.

### Rate limit

**~47k → ~≤25k** input puts the main Synthesizer call **below** Tier 1 **30k/min** for a **single** burst, improving headroom (still subject to **Reader** concurrent calls and **multi-idea** sessions—documented as residual risk in warm-up).

---

## Section 9 — Failure modes and graceful degradation

Aligned with **Reader planning doc §8**:

| Scenario | Expected Synthesizer behavior |
|----------|-------------------------------|
| **Mostly sentinel / gap outputs** (many questions: empty `extracted_evidence`, non-null `evidence_gap_note`) | Produce **low-confidence** `Finding`s; use **`evidence_gap`** and **`research_limitations`** explicitly; **do not** fabricate evidence. |
| **One or two sparse questions, rest strong** | **Per-question** honest gaps; other questions **normal** synthesis. |
| **Total evidence count “low” but >0** (e.g. &lt;5 atoms across all questions) | **No hard-fail** in Synthesizer **if** orchestrator allowed the run (Reader total-fail already requires &gt;0 extractions). Synthesizer should treat as **thin evidence**: lower confidence, strong limitations language. **Threshold for orchestrator pre-check** optional **defense-in-depth**—if added, mark **first-pass** and calibrate. |
| **All questions empty** | **Orchestrator** should already **`ReaderTotalFailure`**; Synthesizer should not run. |

---

## Section 10 — Calibration discipline

Per **`docs/calibration/procedure.md`**:

- **DEBUG `len()` logging** for all capped **Synthesizer output** fields (service code, post-parse).
- **Structured observability** row for each run (Section 6 table—mirror Reader §9 intent).
- **`synthesizer_v2`:** Treat as **meaningful prompt change** → **full calibration session** (Step 1–8) before treating caps/thresholds as locked; add observations to **`docs/llm-schema-calibration.md`** per **“To re-calibrate a field”**.
- Any **new** `max_length` or guard threshold → **first-pass**, document in calibration run file.

---

## Section 11 — ADR-worthy decisions

1. **ADR 0012 (proposed title):** *Synthesizer Input Contract — Reader Output Only, No Raw Tavily Fallback*  
   **Summary:** The Synthesizer consumes **`dict[str, ReaderOutput]`** only for evidence in the LLM prompt; raw Tavily snippets are not a fallback. This encodes the ADR 0010/0011 phase boundary, fixes Tier 1 rate-limit and cost drivers, and prevents dual prompt modes.

2. **Optional ADR (if shipped):** *Citation `relevance` Propagation from Reader to ValidationReport*  
   **Summary:** Whether founders see **per-citation relevance** or it stays internal affects API and UI; record the decision if `Citation.relevance` is added.

---

## Section 12 — Files to create / modify (implementation roadmap)

| File | Action | Notes |
|------|--------|------|
| `backend/app/services/synthesizer_input.py` | Modify | Remove `search_results_by_question` from **`SynthesizerInput`**; add **`reader_outputs`**; add **`CitationHydrationEntry`** model (or split to `citation_hydration.py` — implementation choice); **`build_synthesizer_input`** four-arg only |
| `backend/app/services/synthesizer_service.py` | Modify | **`synthesize_report(..., citation_hydration_index)`**; **`_hydrate_draft`** uses index; URL allow-list from **`reader_outputs`**; calibration DEBUG logs; observability |
| `backend/app/llm/prompts/synthesizer.py` | Modify | **`PROMPT_NAME = "synthesizer_v2"`**; Reader-shaped user/system prompts; sparse-evidence + quote discipline instructions |
| `backend/app/services/research_engine_service.py` | Modify | Build **`citation_hydration_index`** from **`search_results`**; pass **`reader_outputs`** into **`build_synthesizer_input`**; pass index into **`synthesize_report`** |
| New helper (optional) | New | e.g. `build_citation_hydration_index(search_results)` next to synthesizer input or orchestrator-private |
| `backend/app/schemas/validation_report.py` | Modify (optional) | `Citation.relevance` + docstrings if product agrees (Q2) |
| `docs/adr/0012-synthesizer-input-contract.md` | New | Load-bearing ADR (include Approach B: index separate from `SynthesizerInput`) |
| `docs/adr/0013-…` | New (optional) | Citation relevance if separated |
| `docs/llm-schema-calibration.md` | Modify (post-cal) | Append `synthesizer_v2` observations |
| `backend/tests/services/test_synthesizer_service.py` | Modify | Fixtures: `reader_outputs`, `citation_hydration_index`; URL guard; hydration |
| Other tests referencing `build_synthesizer_input` / synthesizer mocks | Modify | Router/integration tests if any |

**Explicit non-change:** **`backend/app/schemas/reader.py`** — **frozen** for this refactor; no `source_title` or other Reader schema edits.

---

## Section 13 — Out of scope

- **Reflector** phase design and prompts  
- **Parallel multi-source Searcher** (Reddit, Trends, etc.)  
- **Eval-set discipline** / gold-standard reports beyond noting `.cursorrules` expectation  
- **Production deployment / Cloud Functions** (ADR 0009)  
- **Anthropic tier upgrade** business decision  
- **Model downgrade** — **Sonnet 4.6 remains** per `.cursorrules`

---

## Section 14 — Open questions for the human

1. **`Citation.relevance`:** Expose on **`Citation`** for API/frontend, or keep internal-only (no schema field)?

---

*End of planning document v2. ADR 0012 (Synthesizer Input Contract) drafted next; implementation prompts follow ADR commit.*
