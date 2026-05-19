# ADR 0016: Synthesizer Five-Field Contract (`trends_signals`)

**Status:** Proposed  
**Date:** 2026-05  

## Context

ADR 0012 anticipated exactly this extension in its **Triggers for future migration** clause:

> We will reconsider this contract when one of these is true:
>
> - Production data shows the orchestrator's hydration-index build is a measurable bottleneck (currently negligible at expected volumes).
> - **The eventual Reflector phase requires the Synthesizer to receive structured signals beyond `ReaderOutput.evidence_gap_note` — for example, follow-up search trigger flags or per-question confidence priors. In that case, `SynthesizerInput` may grow a fifth field; the architectural principle stays the same (everything on `SynthesizerInput` becomes prompt input).**
> - Reader's output schema evolves in a future B3 iteration (e.g., adding `source_title` for unrelated reasons). At that point, the hydration index can be revisited.

`trends_signals` is the first cross-question structured signal the Synthesizer consumes that did not originate in the Reader.

## Decision

```python
class SynthesizerInput(BaseModel):
    refined_idea: RefinedIdea
    research_plan: ResearchPlan
    reader_outputs: dict[str, ReaderOutput]
    rubric_version: str
    trends_signals: dict[str, TrendsSeries] | None  # NEW
```

- `trends_signals=None` when Trends failed or was skipped; the prompt must handle this gracefully (Commit 3 obligation).
- `citation_hydration_index` remains a separate parameter, not a field — ADR 0012's *"everything on `SynthesizerInput` becomes prompt input"* principle is preserved for hydration metadata.
- Prompt version bump `synthesizer_v2_cached` → `synthesizer_v3_cached` is Commit 3. Semantic-equivalence regression test is mandatory (H-3 caching pattern).

## Reasoning

**Fifth field, not a richer fourth:** Reader's job is text-evidence extraction; Trends is numeric. Conflating them violates ADR 0010 schema-layer separation and ADR 0012 input-contract separation.

**Keyed by keyword (not `question_id`):** Trends queries are per-keyword; keywords come from Searcher adaptation over `RefinedIdea` + plan; Searcher runs Trends once per pipeline (not per question).

**| None, not empty dict:** makes Trends-absent vs Trends-empty distinguishable for the prompt's *"note in report"* obligation.

## Consequences

**Easier**

- Synthesizer can reason about demand trajectory when present.
- Absence is explicit (`None`).

**Harder**

- Synthesizer prompt must branch on `None`.
- Semantic-equivalence test in Commit 3 must verify `v2_cached` behavior preserved when `trends_signals` is `None`.

**Operational**

- Synthesizer cache Zone B grows when Trends is present; calibration deferred to Commit 4.

## Related

- ADR 0010 — Reader output schema
- ADR 0011 — Reader execution model
- ADR 0012 — four-field contract (first invocation of "fifth field" trigger)
- ADR 0014 — Anthropic prompt caching
- [`docs/planning/multi-source-searcher.md`](../planning/multi-source-searcher.md)
