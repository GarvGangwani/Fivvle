# ADR 0015: Multi-Source Search Inputs

**Status:** Proposed  
**Date:** 2026-05  

## Context

Searcher today returns Tavily-only results, keyed by `q1`..`qN`. `ARCHITECTURE.md` sequence 8b (lines 631, 654–655) already shows Trends as a Searcher input — this ADR activates a documented-but-unimplemented integration.

F-1 (`53724f06`) and H-4 (`f810fec6`) produced strong institutional reports because Tavily indexes institutional sources well. Consumer, community, and niche ideas need a demand-signal axis Tavily cannot provide.

`.cursorrules` Reliability already specifies *"Trends flaky: retry 3x then continue without; note in report"* — this ADR encodes that at the contract level.

Reddit is deferred per [Reddit Responsible Builder Policy](https://support.reddithelp.com/hc/en-us/articles/42728983564564). Pursuit of approval is a separate effort.

## Decision

New `MergedSearchResults` schema keyed by source:

```python
class MergedSearchResults(BaseModel):
    tavily: dict[str, list[TavilyResult]]
    trends: dict[str, TrendsSeries] | None
```

New `TrendsSeries` + `TrendsPoint` schemas (Pydantic v2, in `backend/app/schemas/search.py`, matching conventions of the module hosting `TavilyResult`).

New `backend/app/integrations/trends.py` mirroring the Tavily wrapper: circuit breaker (5 → 60s), 15s timeout, max 3 retries with exponential backoff + jitter, `ExternalAPICall` logging on every invocation with `cost_usd=0.0`.

**Graceful-skip:** Trends failure returns `None` for `MergedSearchResults.trends`; does **not** raise into the orchestrator.

**Trust boundary:** Trends keyword strings are supplied by the Searcher from `RefinedIdea` fields and `ResearchPlan` questions (Searcher-owned adaptation per `docs/planning/multi-source-searcher.md` §3–§4; not raw user idea text). Trends returned numeric points are non-textual data — they do **not** require XML-wrapping when reaching the Synthesizer (contrast Tavily `content_excerpt`).

pytrends needs no credentials. `.env` is unchanged.

## Reasoning

**Per-source-keyed top-level dict** (not a flat list) preserves provenance and lets future sources slot in without renaming.

**Trends bypasses Reader:** Trends output is numeric time-series; Reader's job is verbatim-quote extraction from prose. Trends feeds the Synthesizer directly via the new fifth field (ADR 0016).

**Graceful-skip rather than fail-pipeline:** Trends is a quality lever, not a correctness requirement. F-1 and H-4 succeeded with zero Trends data.

**Reddit deferred** (not skipped temporarily): re-litigation requires written approval — separate effort.

## Consequences

**Easier**

- Consumer, community, and niche ideas gain a demand-signal axis.
- Future sources slot in by adding a key.
- Wrapper testing is mocked-pytrends-only.

**Harder**

- One more failure mode per pipeline run.
- Cost-ledger gains rows with `cost_usd=0` that must not be silently filtered (cite ADR 0014 §15.1 `COALESCE` pattern).

**Operational**

- `ExternalAPICall.provider="pytrends"`.
- Per-provider circuit-breaker state (`get_breaker("pytrends")`).
- `structlog` field `integration=pytrends`.

Commit 1.5 retires the legacy `app/integrations/google_trends.py` wrapper introduced in an earlier build step. The legacy wrapper's re-raise-on-failure contract is incompatible with this ADR's graceful-skip semantics, and a two-wrapper codebase violates `.cursorrules` "all integration calls through one module." `trends.py` is the single source of truth for pytrends going forward.

## Related

- ADR 0004 — multi-step research engine (Searcher step)
- ADR 0009 — pluggable dispatcher parity
- ADR 0011 — Reader unchanged for Trends
- ADR 0014 — prompt caching (Zone B deferred to Commit 3)
- [`docs/planning/multi-source-searcher.md`](../planning/multi-source-searcher.md)
- `.cursorrules` Reliability
