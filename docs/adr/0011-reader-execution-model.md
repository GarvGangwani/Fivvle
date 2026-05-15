# ADR 0011: Reader Execution Model — Per-Question Concurrent LLM Calls over Single Batched Call

**Status:** Accepted
**Date:** 2026-05

## Context

The B3 Reader phase reads raw Tavily search results and produces structured evidence the Synthesizer can ingest. A typical research run has 7 research questions, each with up to 10 Tavily results. Reader must turn that raw input (~70 snippets, up to ~140 KB of content after truncation) into structured `ReaderOutput` per question.

Two execution models are possible:

1. **Single batched LLM call.** Reader makes one LLM call that ingests all 7 questions and all 70 search results, emits all 7 `ReaderOutput` objects in one structured response. Fewer total API calls.

2. **Per-question LLM calls.** Reader makes 7 LLM calls, one per question. Each call ingests one question + ~10 search results. Runs concurrently via `asyncio.gather()`. More API calls, but each is smaller and independently retryable.

ADR 0004 commits the research engine to a multi-step *single-agent* workflow — not multi-agent. Both options above are single-agent (one logical agent, one set of prompts). The question is whether Reader's single agent makes one big LLM call or seven small concurrent ones.

The May 14 smoke run is directly relevant: the Synthesizer at 123k input tokens hallucinated a citation. Reader's whole purpose is to prevent that failure mode by giving the Synthesizer pre-extracted, pre-validated evidence. Replicating the same 123k-token-single-call shape inside the Reader would defeat the architectural purpose.

## Decision

Reader runs **one LLM call per research question, executed concurrently** via `asyncio.gather()`. Bounded by `settings.reader_concurrency_limit: int = 7` (default = number of questions, effectively unbounded for the typical run).

- Each per-question call ingests: the question text + that question's ~10 Tavily results (each truncated to 2 000 chars per planning doc §6.3) + the Reader system prompt
- Each call emits one `ReaderOutputDraft` (Pydantic model per ADR 0010)
- The reader service performs post-parse URL validation and quote-substring validation on each per-question output, then assembles the results into `dict[str, ReaderOutput]`
- Per-question failures degrade gracefully via the §8.1 sentinel path: a failed question emits an empty-evidence `ReaderOutput`, the run continues
- Total-pipeline failure (zero evidence across all questions) trips the §8.2 hard-fail to `RESEARCH_FAILED`

The concurrency limit is configurable via `settings.reader_concurrency_limit` to allow `=1` (fully sequential) for debugging without code changes.

## Reasoning

**Per-call token budget is small and predictable.**
A per-question call ingests ~15-20k chars of input (one question + ~10 truncated snippets). A batched call would ingest ~123k+ chars. The Synthesizer's 123k-token hallucination is the direct evidence that large-context structured extraction is unreliable at the current state of the art for our model. Reader's job is to *prevent* that failure mode; doing so requires keeping per-call contexts small.

**Error isolation.**
If one question's LLM call fails — schema validation error after Instructor retries, circuit breaker open, transient 429 — the other six questions are unaffected. The §8.1 sentinel path turns that one failure into an honest "no evidence for this question" signal, and the Synthesizer still gets six questions' worth of clean evidence. A single batched call that fails takes the whole Reader phase with it, forcing total retry of all 70 snippets.

**Concurrency reclaims most of the latency.**
The naive concern with per-question calls is wall-clock latency: 7 sequential calls would be 7× a single call. But the questions are independent — there's no data dependency between them — so `asyncio.gather()` runs all 7 concurrently. Anthropic Sonnet 4.6's Tier 1 rate limit is 50 RPM, well above 7 concurrent in-flight requests per pipeline. Real wall-clock cost of per-question concurrent is roughly the cost of the slowest single call, not 7×.

**Prompt focus produces better extraction.**
The Reader prompt asks the LLM to extract evidence from search results for *one* research question. A per-question prompt can be tightly focused: "here is question Q, here are the results for it, extract evidence specifically relevant to Q." A batched prompt would have to ask the LLM to track 7 questions simultaneously, decide which results go with which question, and emit a structured output keyed by question. That's harder for the LLM to do reliably and it's exactly the kind of cognitive load that produces hallucination at the edges.

**Schema output size is predictable per call.**
A per-question call emits one `ReaderOutput` with at most 10 `ExtractedEvidence` items. A batched call would emit 7 `ReaderOutput` objects in a single response — more total schema, more places for Instructor's structured output to drift or hit response length caps. Smaller schema outputs per call means lower retry-after-validation-error rates.

**Cost trade-off is acceptable.**
Per-question Reader runs 7 LLM calls instead of 1 — 7× the per-call overhead. But each call's input is ~6-8× smaller, so total input tokens are roughly equivalent or modestly lower. Output tokens are roughly equivalent. The dominant cost driver after Reader lands is the Synthesizer's input size, which drops from ~123k chars to a projected ~20-30k chars (pre-extracted evidence, no raw snippets). Total per-run cost after B3 is projected to drop from the current $1.10 toward `.cursorrules`'s $0.25-$0.70 target despite Reader's 7-call overhead.

**Configurable concurrency limit.**
Default is 7 (effectively unbounded for the standard run). Setting it to 1 forces sequential execution, useful for: debugging single-question issues without parallel noise in logs, reducing peak rate-limit pressure if early production runs show 429 patterns, and running diagnostic eval-set ideas where deterministic ordering matters. The `retry_async()` decorator and the Anthropic circuit breaker (`get_breaker("anthropic")`) already absorb transient 429s, so the concurrency limit isn't load-bearing — it's a debug knob.

## Consequences

**What becomes easier:**
- Per-question prompt is tight, focused, and easier to iterate during the prompt-engineering phase (`.cursorrules` Quality Discipline calls out 1+ week each on Planner, Reader, and Synthesizer prompts)
- Failure modes are per-question and recoverable, matching the §8.1 sentinel design in the planning doc
- Wall-clock latency stays close to single-call latency thanks to `asyncio.gather()`
- The `ReaderHallucinatedCitation` and quote-substring guards have a clean per-question target — provided URLs come from one question's Tavily results, not a global set
- Cost stays bounded per call; if one question's call accidentally explodes in tokens, it doesn't cascade

**What becomes harder:**
- Seven LLM calls instead of one means seven `LLMCall` rows per Reader phase, per pipeline run. Cost-ledger and admin dashboards will see Reader as a higher row-count phase than Synthesizer. This is mechanical, not problematic.
- Anthropic API rate limits could theoretically be hit faster at scale (more concurrent in-flight requests). At friends-and-circle volume this is irrelevant; at higher scale, the `reader_concurrency_limit` knob and existing retry/circuit-breaker infrastructure absorb it.
- Per-question structured logging emits 7 entries per pipeline run instead of 1. The structlog field shape is defined in planning doc §9; log volume is acceptable.

**What we accept:**
- 7 LLM calls per Reader phase is the cost of clean separation. If usage data later shows the per-call overhead dominates, we can revisit (e.g., batched calls for 2-3 questions at a time as a hybrid). We will not pre-optimize.
- The `reader_concurrency_limit` default of 7 assumes the standard Planner output of 5-7 research questions. If Planner ever emits substantially more questions, the limit can be raised; if it emits fewer, the limit isn't binding.
- The `asyncio.gather()` approach assumes per-question calls are truly independent. They are — no shared state, no inter-question data dependencies. If a future change introduces such a dependency, this ADR's assumption breaks and the execution model needs revisiting.

## Triggers for future migration

We will consider revising Reader's execution model when one of these is true:

- Production data shows per-question prompt quality is *worse* than batched (unlikely given the smoke run evidence, but possible if Sonnet 4.6's batched-extraction capability improves substantially)
- Anthropic concurrent request limits become a binding constraint at production volume that can't be absorbed by the `reader_concurrency_limit` knob
- A future Reflector loop introduces per-question follow-up calls and the resulting 14+ Reader calls per pipeline run become operationally expensive in a measurable way
- Cost data shows per-question overhead is the dominant cost driver of B3, not Synthesizer input size

We will NOT revise because:
- "Batched calls feel more efficient"
- "Seven LLM calls per phase looks like a lot in the cost ledger"
- "We might want to consolidate the pipeline someday"

## Related

- ADR 0004 (Multi-Step Single-Agent Research Engine — the multi-step single-agent constraint Reader inherits)
- ADR 0010 (Reader Output Schema — the per-question schema this execution model is shaped for)
- `docs/planning/b3-reader-phase.md` §5 (execution model rationale, concurrency strategy, sequential fallback)
- `docs/planning/b3-reader-phase.md` §8 (failure handling, including the §8.1 sentinel path that enables graceful degradation of one question's call without affecting the others)
- `.cursorrules` "Research Engine" conventions (`asyncio` + Pydantic, no agent frameworks)