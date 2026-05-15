# ADR 0010: Reader Output Schema — Per-Question Evidence Extraction over Reusing FindingDraft

**Status:** Accepted
**Date:** 2026-05

## Context

B3 introduces a Reader phase between the Searcher and Synthesizer (see `docs/planning/b3-reader-phase.md` for the full design). Reader's job is to read raw Tavily search results for each research question and produce a structured, citation-attached evidence package the Synthesizer can trust without re-reading the raw web content.

This raises a schema design question: should Reader emit `FindingDraft` objects (the existing schema the Synthesizer currently produces as the final output of the pipeline), or a new dedicated schema?

The two options:

1. **Reuse `FindingDraft`.** Reader emits Findings directly, the Synthesizer becomes a pass-through that merges per-question Findings into the final `ValidationReport`. Fewer schema types in the codebase, simpler downstream pipeline.

2. **New dedicated schema** (`ExtractedEvidence` + `ReaderOutput`). Reader emits intermediate evidence atoms; the Synthesizer takes those atoms and produces Findings from them. Two schema types, but cleaner conceptual separation.

The May 14 smoke run motivates this decision. The Synthesizer at 123k input tokens hallucinated a citation because it was asked to do two jobs at once: extract evidence from raw snippets AND synthesize that evidence into a narrative report with confidence calls and cross-question analysis. Reader exists to separate those jobs at the architectural level. The schema choice determines whether that separation is real or just cosmetic.

## Decision

Introduce a dedicated `ExtractedEvidence` / `ReaderOutput` schema in `backend/app/schemas/reader.py`. Do not reuse `FindingDraft`.

`ExtractedEvidence` (per Tavily result that contributes useful information):
- `source_url: str` — exact URL from the provided Tavily result
- `relevance: Literal["high", "medium", "low"]`
- `verbatim_quote: str | None` — exact substring of `TavilyResult.content`; null if no quotable phrase
- `paraphrase: str` — 1-3 sentence summary of what this source says about the question
- `named_entities: list[str]` — companies, products, numbers, subreddits found in this source

`ReaderOutput` (per research question):
- `question_id: str` — `"q1"`…`"q7"`
- `extracted_evidence: list[ExtractedEvidence]` — 0 to N items
- `evidence_gap_note: str | None` — 1-2 sentences if the question went unanswered

The Reader emits one `ReaderOutput` per question via per-question LLM calls (see ADR 0011). The orchestrator collects them into `dict[str, ReaderOutput]` before passing them to the Synthesizer.

Char-limit caps are first-pass estimates per `docs/llm-schema-calibration.md` and will be re-calibrated against observed-max + 10-15% after the first 20 real Reader runs.

Reader follows the same Draft-vs-Final pattern as the Synthesizer: the LLM emits a `ReaderOutputDraft` where `source_url` is a plain string, and the reader service produces the final `ReaderOutput` after URL validation against the provided Tavily results.

## Reasoning

**Reader and Synthesizer do different jobs, and the schema must reflect that.**
Reader extracts. Synthesizer analyzes. Reader operates on raw Tavily content for one question at a time, with no cross-question context, no knowledge of the `RefinedIdea`'s risks, no awareness of competitor extraction. Synthesizer operates over all questions' evidence at once, makes confidence calls, merges duplicate signals across questions, and produces narrative.

If Reader emitted `FindingDraft` objects, it would have to write `claim` and `confidence_rationale` fields — both of which require the cross-question context Reader doesn't have. The schema would force Reader to fabricate analytical judgments it isn't equipped to make, which is exactly the failure mode the smoke run surfaced at the Synthesizer.

**Schema as architectural contract.**
The schema isn't a serialization detail. It's the contract between phases. `FindingDraft` is the Synthesizer's *output* schema — it represents finalized analytical claims with citations and confidence. Reusing it as Reader's output would conflate "I read this source and it says X" with "the research concludes Y about the market with Z confidence." Those are categorically different statements. Keeping them in separate types makes the categorical difference enforceable at the type level.

**Verbatim-quote separation.**
`FindingDraft` doesn't have a verbatim-quote field, because Findings are analytical statements with paraphrased evidence summaries. Reader needs verbatim quotes because they're the substring-checkable anti-hallucination guard. Bolting a verbatim-quote field onto `FindingDraft` to make the reuse work would pollute the Synthesizer's output schema with an extraction-phase concern.

**Per-question structure matches per-question execution.**
ADR 0011 commits Reader to per-question LLM calls. `ReaderOutput` being per-question (one object per call) is the natural fit. `FindingDraft` is per-finding, not per-question — using it as the per-call output would create an awkward shape where one LLM call might emit zero, one, or many `FindingDraft` objects with no clean container.

**The cost of two schemas is small.**
Two schema files instead of one, ~80 lines of Pydantic. The Synthesizer refactor (separate planning task) already needs to change to ingest Reader's output; whether it ingests `ReaderOutput` or `FindingDraft` is roughly equal complexity for the Synthesizer side, and meaningfully less complex for the Reader side.

## Consequences

**What becomes easier:**
- Reader's prompt has a single clean job: extract evidence with verbatim quotes from raw snippets, no analytical reasoning required
- Synthesizer's input is structured, pre-validated, citation-attached, and per-question — the Synthesizer prompt can be tightly focused on synthesis without re-doing extraction
- Type signatures express the pipeline's phase boundaries: `dict[str, list[TavilyResult]] → dict[str, ReaderOutput] → ValidationReport`
- Adding new evidence-atom fields later (e.g., `sentiment: Literal["positive", "neutral", "negative"]` if we discover sentiment matters at extraction time) doesn't touch `FindingDraft`
- The `ReaderHallucinatedCitation` guard (per planning doc §8.4) has a clean target — every `ExtractedEvidence.source_url` validates against the provided Tavily URLs, with no cross-schema concerns

**What becomes harder:**
- Two Pydantic schemas to maintain (`reader.py` + the existing `validation_report.py`) instead of one
- The Synthesizer refactor (separate task) has to be written to ingest `ReaderOutput` rather than continuing to consume `TavilyResult`. This was going to happen either way once Reader landed, but the shape is now explicit.
- Future contributors who don't read this ADR may wonder why Reader doesn't just emit Findings directly. The planning doc §4.1 and this ADR exist to answer that question.

**What we accept:**
- The two-schema design is the right answer for the current pipeline shape and the current product scope. If a future architectural shift collapses the Reader and Synthesizer into a single phase (unlikely — they exist for the architectural reason in ADR 0004), the schemas can be merged then.
- The schema caps in `reader.py` will need to be re-calibrated after real runs, per `docs/llm-schema-calibration.md`. This is the standard discipline, not a special concession for this ADR.

## Related

- ADR 0004 (Multi-Step Single-Agent Research Engine — established the per-phase separation principle this ADR applies at the schema layer)
- ADR 0011 (Reader Execution Model — the per-question execution that the per-question schema is shaped for)
- `docs/planning/b3-reader-phase.md` §4 (full schema design with field-by-field rationale)
- `docs/llm-schema-calibration.md` (calibration discipline for the char-limit caps)
- `backend/app/schemas/validation_report.py` (the existing Draft-vs-Final pattern Reader follows)