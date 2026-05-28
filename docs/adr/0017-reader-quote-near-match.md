# ADR 0017: Reader Quote Guard — Deterministic Near-Match Tier

**Status:** Accepted  
**Date:** 2026-05  

## Context

The Reader quote guard validates `verbatim_quote` fields by checking that each quote is an exact substring of the corresponding Tavily source content (with deterministic normalization for curly quotes and whitespace). Quotes that fail exact and normalized substring checks are classified as hallucinations: the quote is nulled and counted toward `quote_hallucination_rate`.

Calibration on the visa-deadline-tracker eval set showed this guard was too strict for genuine near-verbatim extractions. Three of six ideas flagged real quotes as hallucinations; one case differed by a single character in a 90/91-character quote (partial-ratio ≈ 0.99). The LLM occasionally introduces minor transcription errors — dropped punctuation, one-character typos, or whitespace drift — while still quoting substantively correct text from the source.

The `.cursorrules` Research Engine conventions state "no fuzzy gating" for quote validation. That rule exists to prevent open-ended similarity scoring that would let fabricated quotes pass. A bounded, deterministic near-match tier with a calibrated threshold is a different mechanism: it is not fuzzy gating in the open-ended sense; it is a fixed floor on a reproducible partial-ratio metric.

The URL hallucination guard (hard 0% — any hallucinated URL drops the item) is unchanged by this ADR.

## Decision

Add a **near-match recovered** classification to `_classify_quote_guard` in `backend/app/services/reader_service.py`:

1. After exact match, normalized excerpt match, and boundary-overrun checks fail, compute `_partial_ratio(norm_quote, norm_full)` using `difflib.SequenceMatcher` over a sliding same-length window of the normalized full source.
2. If `partial >= QUOTE_NEAR_MATCH_THRESHOLD` (0.85), return `"near_match_recovered"`.
3. Otherwise return `"unmatched"` (hallucination).

**Calibration (visa-deadline-tracker eval + 8 synthetic fabrications):**

| Class | Partial-ratio range |
|-------|---------------------|
| Genuine near-verbatim quotes | 0.85–0.99 |
| Fabrications | ≤ 0.39 |

Threshold **0.85** sits in the gap between the two distributions.

**Behavior in the validation loop:**

- `"near_match_recovered"` — quote is **kept**; `quote_hallucination_count` is **not** incremented (same as `normalization_recovered` and `boundary_overrun`).
- `"unmatched"` — quote is nulled; count is incremented.

`QUOTE_HALLUCINATION_THRESHOLD` (0.10 rate ceiling) is unchanged. URL guard logic is unchanged.

This ADR amends the `.cursorrules` "no fuzzy gating" rule to permit **deterministic, bounded near-match** (fixed threshold on a reproducible metric). It does **not** permit open-ended similarity scoring or model-dependent fuzzy matching.

## Reasoning

**Exact substring is necessary but insufficient.** Reader prompts ask for verbatim quotes; models sometimes return quotes that are substantively correct but not byte-identical. Treating every such quote as a hallucination inflates the hallucination metric and discards evidence the Synthesizer could use.

**Partial-ratio on normalized text is deterministic.** Given the same quote and source, `_partial_ratio` always returns the same score. The threshold is a fixed constant, not a runtime-tuned or model-dependent gate.

**The check runs only on the rare path.** Quotes that pass exact or normalized substring checks never invoke `_partial_ratio`. The O(n·m) sliding window is acceptable because it applies only to quotes already classified as non-matching.

**Calibration is preliminary.** The 0.85 threshold is validated on one eval idea plus synthetic fabrications. Wider N calibration may adjust the constant; the mechanism (deterministic partial-ratio floor) is stable.

## Consequences

**What becomes easier:**

- Quote hallucination metrics reflect genuine fabrication, not minor transcription drift.
- Real near-verbatim quotes are preserved for the Synthesizer.
- Operators can trust `quote_hallucination_rate` as a signal for prompt or model issues rather than guard false positives.

**What becomes harder:**

- A new failure class (`near_match_recovered`) appears in structured logs; dashboards and runbooks should treat it as a recovered pass, not a hallucination.
- Threshold maintenance: if model behavior shifts, recalibration may be needed (documented as calibration-pending wider N).

**What we accept:**

- A fabricated quote with ≥85% partial overlap against some window of the source could theoretically pass. Calibration shows fabrications score ≤0.39 on the measured set; the gap to 0.85 is large enough for MVP.
- Near-match does not validate semantic correctness — only textual proximity. That is the same contract as exact substring, relaxed by one calibrated character-level tier.

## Related

- ADR 0010 (Reader Output Schema — `verbatim_quote` field and substring contract)
- ADR 0011 (Reader Execution Model — per-question quote guard)
- `docs/planning/b3-reader-phase.md` §4.2 (quote hallucination threshold)
- `.cursorrules` Research Engine conventions (quote validation; near-match exception per this ADR)
