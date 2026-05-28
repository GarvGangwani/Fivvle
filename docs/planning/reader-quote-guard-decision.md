# Reader Quote Guard — Over-Counting Decision

**Status:** Reference — decision input + greenlight request. Changes a non-negotiable (citation/quote integrity); needs co-founder sign-off + ADR before code.
**Date:** 2026-05
**Related:** ADR 0010 (Reader output schema), ADR 0011 (Reader execution model), ADR 0012 (Synthesizer input contract), `.cursorrules` (citations non-negotiable; Reader guard deterministic), `docs/calibration/runs/eval-20260528T061835Z/` (N=6), live diagnostic on `visa-deadline-tracker`.
**Next free ADR:** 0017.

---

## TL;DR

The N=6 eval flagged "quote hallucination" on 3/6 ideas, which looked like a beta blocker. A read-only diagnostic on the worst case (`visa-deadline-tracker`, 28.6%) shows the flagged quotes are **not fabricated** — they are real, near-verbatim quotes that fail the guard's **exact-substring** check because the LLM lightly normalized them (a dropped word, spacing, one character). The guard is **over-counting**: it nulls genuine quotes and inflates the hallucination metric.

**Decision sought:** relax the Reader quote guard from byte-exact substring to a calibrated high-confidence near-match, so real quotes survive while true fabrication is still caught. Record as ADR 0017.

---

## Evidence

Diagnostic captured each `unmatched` quote and its best-overlap source window (no fabrication possible — it compares against the real source the Reader saw):

| # | source | quote_len | finding |
|---|--------|-----------|---------|
| 1 | tracreports.org | 273 | norm_quote matches source **word-for-word** in the window ("licensed to practice in a particular jurisdiction (or before a particular agency) or by persons who are not attorneys..."). Real quote; a tiny edit in the 273-char span broke exact substring. |
| 2,4 | federalregister.gov | 221 | Same pattern — long quote, near-verbatim, broken by minor normalization. |
| 3 | fwd.us | 91 | Longest-common-substring **90 of 91 chars** — literally one character off. Unambiguously a real quote. |

Pattern: **the longer the quote, the more likely a one-token edit breaks exact-substring**, even when the quote is genuine. The guard treats "99% verbatim" identically to "invented."

## Why this matters for the product (user value)

Two ways this hurts a paying founder, in opposite directions:

1. **False alarms erode the metric we trust.** If "hallucination rate" counts near-verbatim quotes as fabrication, the number is not measuring what we think. We can't gate beta on a metric that cries wolf.
2. **Real quotes get nulled.** On guard failure the service nulls `verbatim_quote`. So genuine, citable quotes are being **discarded** — the founder loses real evidence. That is a direct quality loss.

Crucially: this is **not** the engine fabricating sources. URL hallucination (the worst failure) is separately guarded and held at 0% in the eval. The quote guard is a precision problem, not an integrity hole.

## What is NOT changing

- URL hallucination guard — stays hard 0%, untouched. Fabricated *sources* remain the red line.
- The principle that quotes must trace to real source content — unchanged. We are changing *how closely* "trace to" is measured, not whether.
- Deterministic, no-LLM guard — the fix stays deterministic (string/sequence math), per `.cursorrules` "Reader guard is deterministic; no fuzzy/similarity gating" — **note:** this rule is exactly what's being revisited; see Open Question 1.

## Proposed fix (for greenlight)

Relax `_classify_quote_guard` so a quote passes when it is a **high-confidence near match** of the source, not only an exact substring:

- Keep the existing fast path (exact substring → pass) and `normalization_recovered` / `boundary_overrun` classes.
- Add a calibrated near-match tier: e.g. `difflib` partial-ratio ≥ a threshold (candidate 0.95) OR token-subsequence coverage ≥ threshold, measured against the full source (not a fixed window — the diagnostic's 120-char window was a measurement artifact, not the guard's logic).
- Only below that threshold is a quote counted as `unmatched` / hallucination.
- Recalibrate `QUOTE_HALLUCINATION_THRESHOLD` (currently 0.10) against the new classifier on the eval set.

This keeps fabrication caught (a truly invented quote scores low) while genuine near-verbatim quotes survive.

## Open questions for co-founders

1. **Does relaxing exact-substring violate the "deterministic, no fuzzy gating" rule in `.cursorrules`?** A partial-ratio threshold is still deterministic (same input → same output), but it *is* similarity-based. This is the crux: the current rule was written to forbid fuzzy matching, and the evidence now suggests fuzzy-but-bounded matching is exactly what's needed. **Recommend:** amend the rule via ADR 0017 to permit a *deterministic, thresholded* near-match — not open-ended fuzzy similarity.
2. **Threshold value (0.95? 0.97?)** — set by calibration, not guess. Needs a calibration run measuring false-pass (fabrication slipping through) vs false-fail (real quotes nulled) at candidate thresholds.
3. **Should the Synthesizer surface near-matched quotes differently** (e.g. mark lightly-normalized vs exact)? Defer — not needed for the fix.

## Recommended sequence

1. Co-founder greenlight on the principle (relax to deterministic near-match) + ADR 0017.
2. Diagnostic-calibration: measure pass/fail at candidate thresholds on the eval set (cheap — reuse stored unmatched cases + a small synthetic-fabrication set).
3. Implement in `reader_service.py` as a calibrated commit + regression test (genuine near-verbatim passes; invented quote fails).
4. Re-run N=6 eval; confirm quote-hallucination drops to a true rate and no real quotes are nulled.

## Logged follow-ups

- Promote the eval's citation-hallucination gate from "not computed" — once the matcher is trustworthy, wire a real quote-integrity gate.
- A `Session is already flushing` SAWarning appeared once during the diagnostic re-search (reflector query refinement, q1) — unrelated to quotes, but log it: a failed-LLM-call audit write tried to `db.add` mid-flush. Separate bug; backlog.
