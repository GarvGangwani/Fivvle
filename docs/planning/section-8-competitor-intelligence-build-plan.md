# §8 Competitor Intelligence — Vertical-Slice Build Plan

**Status:** Reference — scoping artifact for greenlight, not a build commitment.
**Date:** 2026-05
**Audience:** Co-founders (greenlight decision) + build session.
**Related:** `docs/planning/master-index-gap-map.md` §8 + build-sequence step 2; ADR 0012 / 0016 (Synthesizer contract); `b3-synthesizer-refactor.md` (CompetitorMention structure); ADR 0010/0011 (Reader); MASTER_INDEX §8.

---

## Why §8 first

The gap-map recommends §8 as the first vertical slice for three reasons that still hold after the Trends investigation:

1. **It builds on data the engine already produces** — `competitors` is emitted today (not greenfield).
2. **Its headline chart is genuinely Sourced, not Inference** — the positioning map rests on competitor existence/positioning from cited web evidence, *not* on a flaky scraper. Unlike §5 (now known to depend on unreliable Trends), §8 can deliver a defensible chart **now**.
3. **It proves the full pattern** — research → schema → synthesis → quant → chart — end-to-end, and becomes the replication template for every later section.

This makes §8 the highest-value next build for paid-user trust: a real, sourced, useful chart a founder can act on.

---

## What exists today (ground truth from code)

`CompetitorMention` (current contract, per `b3-synthesizer-refactor.md` §160–163):

| Field | Type | Stance |
|-------|------|--------|
| `name` | str | Sourced (must trace to `named_entities` + cited URLs) |
| `description` | str | Sourced |
| `positioning_vs_idea` | str (cap 400) | Sourced narrative |
| `citations` | list | Sourced |

So today the engine knows **who** the competitors are and a **one-line positioning narrative**, all citation-backed. Anti-hallucination is prompt-discipline only (no post-parse competitor guard; v3 trigger is >5% invention rate — `b3-synthesizer-refactor.md` §217–230).

## What §8's vision needs (MASTER_INDEX §8.4)

| Vision element | Needs | Stance | Tier |
|----------------|-------|--------|------|
| Competitor matrix (pricing / features / funding / geography / weakness) | New structured fields per competitor | Sourced where retrievable; **labeled-Inference fallback** where not | T2 (T3 if pricing/funding need a new source) |
| **Positioning map (2-axis scatter)** ★ | Two numeric axes per competitor | Sourced if axes derive from cited facts; Inference if reasoned | T2 |
| Feature-gap heatmap | Feature presence matrix | Sourced (feature lists from web) | T2 |
| White-space / moat / saturation score | Reasoned synthesis | **Inference — Appendix-E confidence label mandatory** | T1 |

---

## The gap, precisely

The slice is **mostly schema + synthesis work on existing research**, not new data acquisition — which is why it's T2 and a good first slice. The honest hard parts:

1. **The positioning scatter needs two numeric axes.** A scatter requires each competitor to have an (x, y). Competitor *existence* is Sourced, but the *axes* (e.g. price tier × feature-richness, or market-focus × maturity) are mostly **Inference**. **This means the headline chart is partly Inference and MUST carry confidence/assumption labels** — consistent with the gap-map rule "charts cannot precede data; Inference visuals must carry confidence." The "cleanest sourced chart" framing needs this caveat: the *points exist* because competitors are sourced, but their *coordinates* are reasoned.

2. **Pricing/funding may not be retrievable from Tavily alone.** Per gap-map, these may need a new source (T3) or a labeled-inference fallback (T2). Recommend **T2 labeled-inference fallback for the slice**, defer the T3 source.

3. **Appendix E (confidence labels) is a prerequisite.** The gap-map's build sequence puts cross-cutting contracts (Appendix A provenance, Appendix E confidence) *before* §8. Any Inference field in §8 (axes, moat, saturation) needs the confidence-label schema to exist first, or §8 ships unlabeled Inference — exactly the trust risk we're trying to avoid. **This is the real sequencing dependency to decide on (see Open Questions).**

---

## Proposed build steps (for greenlight, not yet committed)

1. **Appendix-E confidence label** as a reusable schema field (minimal version: a `confidence` enum + optional `assumptions` on Inference-bearing fields). Prerequisite for honest §8 Inference.
2. **Extend `CompetitorMention`** with the matrix fields (pricing, features, funding, geography, weakness) — Sourced where cited, else labeled Inference.
3. **Add positioning axes** (two numeric fields + axis definitions), each carrying a confidence label.
4. **Synthesizer prompt update** to populate the new fields from existing Reader `ExtractedEvidence` (no new research call). Semantic-equivalence + calibration commit per `.cursorrules` prompt-restructuring rule.
5. **Chart**: positioning scatter rendered with visible confidence/assumption treatment.
6. **Calibration** on the 5-idea protocol (`eval-set-discipline.md`) — competitor invention rate, field-fill rate, cost.

Each step is a separate calibrated commit (no big-bang).

---

## Open questions for co-founders

1. **Appendix E first, or inline-minimal with §8?** Gap-map says contracts first. Cheaper path: build a *minimal* confidence label *as part of* §8 and generalize later. Tradeoff: clean contract vs. faster slice. **Recommend minimal-inline, generalize after** — proves the pattern without a multi-week contract project blocking the slice.
2. **Pricing/funding: T2 labeled-inference fallback now, or wait for a T3 source?** Recommend **T2 fallback now** — keeps the slice moving; T3 source becomes a later gated build (same pattern as the Trends paid-API deferral).
3. **Positioning axes: which two?** A real product decision (price × features? maturity × focus?). Needs a founder call — the axes define what the chart *says*.

---

## What this slice does NOT do

- No new external data source (stays T2; pricing/funding use labeled-inference fallback).
- No agent framework (ADR 0004).
- Does not touch Trends/§5 (separate deferred decision).
- Does not promote ADR 0015/0016.

**Next ADR if needed:** 0017 (e.g. if the confidence-label contract or competitor-matrix schema warrants one).
