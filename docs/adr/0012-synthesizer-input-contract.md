# ADR 0012: Synthesizer Input Contract — Reader Output Only, No Raw Tavily Fallback

**Status:** Accepted
**Date:** 2026-05

## Context

The B3 Reader phase landed in commits 348c130, 38e58b7, 93a7973, and 4e763d1. Reader produces `dict[str, ReaderOutput]` — structured, per-question, citation-attached evidence extracted from raw Tavily results. Per planning doc `docs/planning/b3-reader-phase.md` §10.1, Reader output is currently produced but unused: the Synthesizer continues to consume raw Tavily snippets via `SynthesizerInput.search_results_by_question`.

This intermediate state is not sustainable. Two failures during the May 14-15 validation runs make this explicit:

1. **May 14 smoke run — citation hallucination.** Synthesizer was asked to read ~70 raw Tavily snippets (~123k tokens), extract evidence, attribute citations, and synthesize a coherent report in a single LLM pass. It fabricated a URL not present in any search result. `SynthesizerHallucinatedCitation` caught it and transitioned to `RESEARCH_FAILED`, but the root cause is architectural: extraction and synthesis in one prompt overloads the model.

2. **May 15 mini-calibration — Tier 1 rate-limit failure.** The Synthesizer's ~47k-token input exceeded Anthropic Tier 1's 30,000 input tokens/minute ceiling. The pipeline failed twice in succession on the same idea, each time at the Synthesizer phase. Reducing input is not a cost optimization — it is a hard operational requirement on the current tier.

The architectural fix is the one ADR 0004 originally specified and ADR 0010 encoded as a schema-level contract: the Synthesizer consumes Reader's pre-extracted evidence, not raw Tavily snippets. This ADR records the input contract that makes that fix concrete.

A secondary question this ADR resolves: `Citation` requires a `title` field (max 300 chars) and `source_domain` field. `ExtractedEvidence` has neither — only `source_url`. So Reader output alone is insufficient to hydrate `Citation` objects. The ADR records how the title/domain metadata reaches the Synthesizer service without polluting the LLM prompt with raw Tavily data.

## Decision

The refactored Synthesizer consumes `dict[str, ReaderOutput]` as its sole evidence surface in the LLM prompt. The Synthesizer does not consume raw Tavily snippets in any mode — there is no fallback.

The new `SynthesizerInput` contains exactly four fields:

```python
class SynthesizerInput(BaseModel):
    refined_idea: RefinedIdea
    research_plan: ResearchPlan
    reader_outputs: dict[str, ReaderOutput]
    rubric_version: str
```

The `search_results_by_question` field is removed. The model is locked at four fields; hydration metadata does not belong on it.

To populate `Citation.title` and `Citation.source_domain` for the final report, the orchestrator builds a `citation_hydration_index: dict[str, CitationHydrationEntry]` from `search_results` (a URL → metadata map derived from Tavily). This index is passed to `synthesize_report()` as a separate keyword parameter, NOT as a field on `SynthesizerInput`. The index is consumed only by `_hydrate_draft()` inside `synthesizer_service.py` after the LLM has emitted its draft. It is never serialized into the user prompt.

```python
async def synthesize_report(
    db: AsyncSession,
    synth_input: SynthesizerInput,
    citation_hydration_index: dict[str, CitationHydrationEntry],
    experiment_id: UUID | None = None,
) -> ValidationReport:
    ...
```

The `SynthesizerHallucinatedCitation` guard's allowed-URL set updates to `{ev.source_url for ro in synth_input.reader_outputs.values() for ev in ro.extracted_evidence}`. Hard-fail behavior is preserved — fabricated citations in the final report are the worst possible failure, and Synthesizer is the last LLM phase.

The Reader schema (`backend/app/schemas/reader.py`) is explicitly NOT modified by this refactor. `ExtractedEvidence` does not gain a `source_title` field. The architectural split between extraction (Reader) and hydration (orchestrator + `_hydrate_draft`) stays clean.

The Synthesizer prompt version increments from `synthesizer_v1` to `synthesizer_v2`. This is a fundamentally different cognitive task, not a minor tweak — versioning preserves cost-analytics history and enables calibration diffs.

## Reasoning

**Why Reader output is the right input surface.**
Reader's job is extraction: per-question, structured, citation-attached, hallucination-guarded. Synthesizer's job is synthesis: cross-question reasoning, narrative, recommendation, confidence assessment. ADR 0010 encoded this split at the schema layer. ADR 0011 encoded it at the execution layer (per-question Reader calls). This ADR completes the chain: at the input contract layer, the Synthesizer consumes Reader output, not raw Tavily. The architectural integrity holds top-to-bottom.

**Why no fallback to raw Tavily.**
A fallback path would require the Synthesizer to maintain two prompt modes (pre-Reader and post-Reader). Two prompt modes means double the prompt-engineering iteration burden, double the calibration sessions, double the test coverage. It also tempts shortcuts: future changes that "just turn off Reader for this case" defeat the architectural split. The May 15 rate-limit failure makes fallback affirmatively harmful — it would let production fall back to a path that doesn't fit on Tier 1. The cleaner outcome is: if Reader fails entirely (zero evidence across all questions), Reader's existing `ReaderTotalFailure` exception trips and the pipeline transitions to `RESEARCH_FAILED`. The Synthesizer is never asked to synthesize from nothing.

**Why the hydration index is separate from `SynthesizerInput`.**
The architectural contract is "the Synthesizer LLM prompt sees Reader output only." That's the value-bearing constraint. Hydration is a server-side mechanical join — populating `Citation.title` from URL after the LLM has produced its draft. Putting the hydration map on `SynthesizerInput` would create a misleading shape: the model would look like it accepts Tavily metadata as input, when in fact only the orchestrator and `_hydrate_draft` ever touch it. Separating the hydration index from `SynthesizerInput` makes the boundary visible at the function signature: `SynthesizerInput` is what becomes the prompt; `citation_hydration_index` is server-side plumbing.

**Why not extend `ExtractedEvidence` with `source_title` instead.**
That option was considered. It would let the Synthesizer skip the hydration index entirely. But it would force a Reader schema change — touching `ExtractedEvidence`, updating the Reader prompt to populate the new field, re-calibrating Reader's caps, re-running Reader's tests. Reader is committed and stable. The hydration index achieves the same outcome without touching Reader. The Reader schema staying frozen is a feature, not a constraint.

**Why hard-fail on hallucinated URLs (and not on hallucinated quotes or competitors in v2).**
URL hallucination in the final report is the worst possible failure mode — a founder reads a report with a fake citation, loses trust in the product, and the architectural integrity of the entire research engine is compromised. Hard-fail is the only acceptable response. Quote and competitor hallucination are softer failures: a misattributed quote or fabricated competitor name degrades quality but doesn't fabricate a source. For v2, both rely on prompt discipline alone; if calibration shows fabrication rates >5%, v3 adds post-parse guards. This staged approach avoids brittle guards built without data.

**Why `synthesizer_v2`, not `synthesizer_v1.1`.**
The task changes fundamentally. v1's prompt asks "read 70+ raw snippets, extract evidence, identify competitors, write Findings." v2's prompt asks "synthesize Findings from pre-extracted evidence." Different inputs, different cognitive load, different output expectations. Calling it a minor version would hide the change in cost-analytics rollups and make calibration diffs incoherent.

## Consequences

**What becomes easier.**

- Synthesizer input drops from ~47k to projected ~20-25k tokens. Fits comfortably under Tier 1's 30k/min cap.
- Cost-per-run drops materially. Projected total pipeline cost: $0.50-0.80 (down from $1.15 warm-up), confirming after first calibration.
- Citation hallucination at the architectural level is harder, not just guarded post-hoc — the LLM is given a finite, pre-validated set of `ExtractedEvidence.source_url` values and instructed to cite only from that set. The hard-fail guard remains as the safety net, but the architectural shape reduces the surface area for hallucination.
- Synthesizer prompt becomes tighter and more focused, easier to iterate during the prompt-engineering phase.
- Test isolation improves. Synthesizer tests can mock `dict[str, ReaderOutput]` directly; they no longer need to construct fake Tavily payloads.
- Future contributors reading `SynthesizerInput` see exactly what becomes the prompt — no hidden inputs, no implicit fallback paths.

**What becomes harder.**

- Orchestrator complexity increases marginally. `research_engine_service.py` now builds both `SynthesizerInput` and `citation_hydration_index`, and passes both to `synthesize_report()`. Two arguments where one was sufficient. The tradeoff is worth it — the alternative was either a fragile Reader schema change or a leaky `SynthesizerInput`.
- `_hydrate_draft()` signature changes. Existing tests for hydration must be updated.
- Synthesizer's failure modes around sparse Reader evidence need explicit prompt instructions (covered in planning doc §3 and §9). The model must produce honest "evidence-gap" Findings rather than fabricating to fill gaps.

**What we accept.**

- The hydration index is built fresh from `search_results` on every Synthesizer call. There's no caching layer. At the volumes the friends-and-circle launch will see, this is fine; if it becomes a bottleneck at scale, the index can move to a request-scoped cache.
- `CitationHydrationEntry`'s field caps (`title: max 500`, `source_domain: max 255`) are slightly looser than `Citation`'s caps (`title: max 300`, `source_domain: max 100`). The implementation must truncate or normalize during the `Citation` construction in `_hydrate_draft`. Marked as a first-pass implementation note in planning doc §2.
- `accessed_at` on `Citation` continues to be set to synthesis-time UTC, matching current behavior. If a future change requires propagating Searcher-time accessed_at through the index, that's a separate enhancement.
- The competitor and quote guards rely on prompt discipline alone in v2. If calibration shows fabrication rates above 5% in either, v3 adds post-parse guards. This is deliberate — building guards without calibration data produces false-positive-prone thresholds.

## Triggers for future migration

We will reconsider this contract when one of these is true:

- Production data shows the orchestrator's hydration-index build is a measurable bottleneck (currently negligible at expected volumes).
- The eventual Reflector phase requires the Synthesizer to receive structured signals beyond `ReaderOutput.evidence_gap_note` — for example, follow-up search trigger flags or per-question confidence priors. In that case, `SynthesizerInput` may grow a fifth field; the architectural principle stays the same (everything on `SynthesizerInput` becomes prompt input).
- Reader's output schema evolves in a future B3 iteration (e.g., adding `source_title` for unrelated reasons). At that point, the hydration index can be revisited.

We will NOT reconsider because:

- "Two arguments to `synthesize_report` is ugly."
- "It would be simpler to put everything on `SynthesizerInput`."
- "Why doesn't the Synthesizer just see Tavily too?"

The architectural split is the entire point.

## Related

- ADR 0004 (Multi-Step Single-Agent Research Engine — the 5-phase pipeline this ADR completes)
- ADR 0010 (Reader Output Schema — the schema-level contract this ADR enforces at the input layer)
- ADR 0011 (Reader Execution Model — per-question per-call execution that produces the input this ADR specifies)
- `docs/planning/b3-synthesizer-refactor.md` (full planning artifact with prompt blueprint, hydration mechanics, calibration discipline, file list)
- `docs/planning/b3-reader-phase.md` §15 Decision 1 (the precedent for "single source of truth, no fallback" reasoning)
- `backend/app/schemas/reader.py` (the Reader schema this refactor consumes; frozen by this ADR)
- `backend/app/schemas/validation_report.py` (the `Citation` schema whose `title` field drives the hydration index design)