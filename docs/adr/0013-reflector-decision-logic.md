# ADR 0013: Reflector Decision Logic — Rule-Driven for v1

**Status:** Accepted
**Date:** 2026-05

## Context

The B3 Reflector phase (planning doc `docs/planning/b3-reflector-phase.md`) slots between Reader and Synthesizer to evaluate whether per-question evidence is sufficient and, when not, trigger one bounded round of follow-up search and re-extraction before the Synthesizer runs.

ADR 0004's narrative describes Reflector as "one LLM call to evaluate evidence sufficiency." Read literally, that suggests an LLM-driven decision: feed Reader's outputs to a critic model, get back a list of questions to re-search. That design has real appeal — an LLM can reason about evidence quality holistically, weigh signals the rule designer didn't anticipate, and produce natural-language rationales.

But Reflector is fundamentally different from Reader and Synthesizer:

- Reader and Synthesizer **produce** content the founder consumes. Prompt iteration on those phases pays back directly in report quality.
- Reflector **decides** whether to spend more budget on re-search. It is a quality gate, not a content producer. Its output is internal pipeline state, never user-facing.

This category difference matters for the cost-benefit calculus. An LLM-driven critic adds a measurable cost (Sonnet 4.6 call evaluating ~7 questions per pipeline run) and a real maintenance burden (yet another prompt to engineer, calibrate, and version) for a decision that, in v1, can be made deterministically from signals Reader already exposes.

The warm-up data so far identifies specific, observable signals that indicate "Reader's evidence is insufficient":

1. `ReaderOutput.evidence_gap_note is not None` — Reader itself flagged a gap
2. `len(extracted_evidence) <= 2` — sparse extraction (likely wrong SERP shape, not "nothing exists")
3. `unique_domains(extracted_evidence) <= 1 and len(extracted_evidence) >= 2` — corroboration is weak (all atoms from one site)

These signals are concrete, computable from Reader's typed output without any LLM call, and directly traceable to product failure modes the warm-ups surfaced. The question this ADR resolves: should Reflector compute these signals in deterministic Python code, or describe them to a critic LLM that returns a free-form decision?

## Decision

Reflector v1 uses **rule-driven decision logic**: deterministic Python code computes the three signals above and applies a composite OR-rule. A question is flagged for re-search if any of the three disjuncts is true, subject to per-run scheduling caps (`max_questions_per_run = 4` first-pass) and per-pipeline wave bounds (`max_refinement_waves = 1` for v1).

No LLM call is made to *decide* whether a question needs re-search. The LLM is used only downstream, for the narrower task of *generating refined search queries* for questions that the rule has already flagged (Reflector planning doc §4 Option B).

Threshold values (`K_sparse = 2`, mono-domain conjunct, `max_questions_per_run = 4`) are first-pass estimates per `docs/llm-schema-calibration.md`, to be revisited after the 5-idea calibration session against the full B3 pipeline.

The `ReflectorPhaseSummary.decision_method` field is typed as `Literal["rule_v1"]` (defined as a module-level alias `ReflectorDecisionMethod`) so a future v2 LLM-driven method becomes an explicit, contributor-visible extension rather than a silent prompt change.

## Reasoning

**Predictability and testability.** Rule-driven logic is deterministic given the same `ReaderOutput`. Unit tests cover the rule matrix with synthetic Reader outputs and run in milliseconds. An LLM critic's behavior shifts with prompt iteration, model version updates, and structured-output drift — making regression testing a calibration session rather than a CI check. For a decision that gates real spend on re-search, deterministic is the safer default.

**Zero marginal decision cost.** Reader produces 7 calls. Synthesizer produces 1 call. Adding an LLM critic at Reflector adds another call per pipeline run at roughly $0.05–0.10. Across many runs that's meaningful. Rule-driven Reflector adds $0 to the decision step — all spend flows into the *content-producing* phases (query refinement + Tavily + partial Reader) where the value actually lives.

**The signals are observable and load-bearing.** The three disjuncts aren't speculative. Reader's warm-ups produced both gap-note paths and mono-domain paths; the post-Synthesizer warm-up's report quality showed which questions had thin evidence. The signals are right there in `ReaderOutput`, typed and stable. An LLM critic would have to read the same signals and emit a decision — adding a stochastic layer for no signal we don't already have.

**LLM-driven decision is not closed off.** A future v2 may discover the rule misses obvious quality calls a critic would catch (e.g., "all three atoms are about the same product feature but the question asked about market sizing"). When that data emerges from calibration, a v2 critic becomes the natural next iteration. The module-level `ReflectorDecisionMethod` alias and `decision_method` field on `ReflectorPhaseSummary` are the seams that make that future migration explicit.

**ADR 0004's narrative is honored in spirit.** ADR 0004 specifies a 5-phase pipeline with a Reflector that evaluates and triggers follow-up. It does not specify the *implementation* of the evaluation step. The single-sentence "one LLM call" reference in ADR 0004 was scaffolding for the architectural argument, not a binding implementation contract. This ADR records v1 as rule-driven so future contributors understand the deliberate v2 → critic upgrade path rather than treating rule-driven as a regression from ADR 0004.

**LLM-based query refinement still applies.** Reflector planning §4 keeps the LLM in the loop for the task it's best suited for: *generating refined queries* for flagged questions. That's a creative, context-dependent task where the LLM's strength (proposing diverse, well-formed search strings from a question + evidence signals) maps cleanly. The decision of *whether* to re-search is the rule's job; the decision of *how* to re-search is the LLM's job. Two different cognitive tasks, two different tools.

## Consequences

**What becomes easier.**

- Rule logic is unit-testable with synthetic `ReaderOutput` objects. No mocking of LLM clients. Test coverage of the rule matrix completes in seconds.
- Reflector adds zero LLM-decision cost per pipeline run. Total per-run cost stays bounded by the variable components (query refinement + Tavily + partial Reader for flagged questions only).
- Calibration sessions focus on tuning threshold *numbers* (`K_sparse`, scheduling caps) rather than iterating prompt text. Calibration data has clear semantics: trigger rate, false positive rate, conditional improvement rate.
- Failure modes are simpler. The rule cannot hallucinate, drift, or violate output schemas. If a future migration changes Reader's schema, the rule breaks visibly at type-check time, not silently in calibration.

**What becomes harder.**

- The rule cannot catch quality issues that don't map to one of the three disjuncts (e.g., "all three atoms confirm the same trivial fact and ignore the question's core ask"). v2 critic LLM can.
- Threshold tuning is manual. Each threshold change requires a deliberate human decision based on calibration data, not an automatic prompt revision.
- `ReflectorDecisionMethod` typing must be extended in code (and tests updated) when a v2 method is added. This is a feature — it forces explicit acknowledgment of the methodology change.

**What we accept.**

- The rule will produce false positives (re-search a question that didn't need it) and false negatives (skip a question that would have benefited). Both rates are bounded by `max_questions_per_run = 4` and `max_refinement_waves = 1`, so worst-case cost overage is contained. Calibration sessions will quantify both rates.
- We are not claiming rule-driven is fundamentally better than LLM-driven for this task. We are claiming it is better for v1: simpler, cheaper, more testable, deterministic enough to ship and observe. The v2 evolution to an LLM critic is a deliberately open path.

## Triggers for migration to LLM-driven (v2)

We will revisit this decision when one of these is true:

- Calibration data over multiple sessions shows the rule misses obvious quality calls (>15% of "thin evidence" outcomes that a human review judges should have been re-searched) consistently across diverse ideas
- The rule's threshold space becomes unmanageably brittle (more than ~6 thresholds needed to capture necessary nuance, or thresholds need to differ by idea-type heuristics)
- Cost analysis at production scale shows the rule's false-negative rate (questions that should have been re-searched but weren't) is materially costing report quality, and the cost of an LLM critic is amortizable over volume

We will NOT migrate because:

- "LLM-driven feels more sophisticated"
- "ADR 0004 mentions an LLM critic in passing"
- "Future-proofing for ideas we haven't tested"

The v2 migration is deferred until concrete calibration data demands it.

## Related

- ADR 0004 (Multi-Step Single-Agent Research Engine — the 5-phase pipeline this ADR implements at the Reflector layer)
- ADR 0010 (Reader Output Schema — the schema Reflector's rules inspect)
- ADR 0011 (Reader Execution Model — the per-question outputs Reflector evaluates)
- ADR 0012 (Synthesizer Input Contract — the downstream consumer; Reflector never touches `SynthesizerInput`, only mutates `reader_outputs` in place before Synthesizer runs)
- `docs/planning/b3-reflector-phase.md` (full planning artifact with rule disjuncts, query strategy, observability, calibration discipline)
- `docs/llm-schema-calibration.md` (calibration discipline for threshold values)