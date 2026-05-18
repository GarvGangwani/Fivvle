# LLM Schema Calibration

Empirical observations of LLM output length distributions, used to set
Pydantic schema max_length caps for prompt+schema pairs.

## Why this file exists

Schemas in this codebase were initially designed by Opus 4.7 reasoning
about "reasonable output sizes" without empirical data from the actual
runtime prompts (written separately by Sonnet 4.6). This decoupling
caused repeated `InstructorRetryException` failures when Sonnet 4.6 (the
runtime model) produced output that exceeded the guessed caps.

Going forward:
- When designing or changing a schema that pairs with an LLM prompt,
  consult the empirical data here
- When changing a prompt in a way that affects output shape, add new
  observations here
- Schema caps should be set at observed-max + 10-15% margin, not at
  "what feels reasonable"

## RefinedIdea (refinement_v1 prompt, Sonnet 4.6, temperature=0.4)

Sample: 4 calls against the abandoned-checkout-recovery raw idea
(2026-05-14). Three failed validation, one succeeded.

| Field | Cap before fix | Observed range (chars) | Cap after fix |
|---|---|---|---|
| risks[*] | 200 | 161, 166, 175, 176, 178, 210, 218, 246, 260 | 250 |
| subheadline | 160 | 138, 153, 165, 175 | 190 |
| refined_one_liner | 200 | 192-200 | 200 (no change, at ceiling) |
| target_audience | 300 | 230-265 | 300 (no change) |
| value_proposition | 400 | 290-298 | 400 (no change) |
| headline | 80 | 54-60 | 80 (no change) |
| cta_text | 30 | 24-26 | 30 (no change) |

### Notes

- `risks[*]` longest observations correlated with naming multiple
  specific competitors (e.g., Klaviyo + Omnisend in one risk) or
  multiple regulatory regimes (GDPR + TCPA + WhatsApp Business Policy).
  Truncating below 250 loses specificity. Specificity is product value
  (`.cursorrules` Quality Discipline). Cap raised to 250.
- `subheadline` range narrow but consistently exceeded 160. Cap raised
  to 190.
- `refined_one_liner` is brushing the cap — flag for re-calibration
  if any future refinement fails on this field.
- Other fields well within cap. No change needed.

## To re-calibrate a field

1. Run 10-20 refinements against varied raw ideas (not just one).
2. Record observed max + median per field.
3. Set new cap at `max(observed) + 10-15%`.
4. Update this table.
5. If a field repeatedly produces output that requires raising the cap
   past 1.5× the original design, that's a signal the prompt needs a
   length guidance instruction, not just a higher cap.

## Schemas pending calibration

Reader prompt restructured from `reader_v1` to `reader_v1_cached` (commit H-2) for Anthropic prompt caching. This is layout-only: instructions and schema guidance are unchanged relative to `reader_v1`, with experiment context (refined idea + research plan JSON) moved into a dedicated cache zone. Calibration after deployment should confirm output shape remains statistically equivalent to the pre-cache baseline (e.g. `extracted_evidence_count`, URL hallucination rate, quote substring guard trip rate).

### ResearchPlan.notes_for_synthesizer (planner_v1)

- **Status:** pending — instrumentation added 2026-05, awaiting ≥10 production runs with non-null values
- **Current cap:** 600
- **Observed failures:** One `InstructorRetryException` at unknown length against the 600 cap — no recoverable measurement (LLMCall stores audit metadata only; past runs cannot be measured retroactively)
- **Recalibration trigger:** Re-run `backend/scripts/calibrate_planner_notes_cap.py` once a JSON output column or length-log harvester is added, **or** scrape Cloud Logging for `planner_field_lengths` events (DEBUG) and aggregate offline

- `ResearchQuestion` (planner_v1) — was already recalibrated in B2.2
  (`question` max_length 300 → 500). No further data yet.
- `Finding` (synthesizer_v1) — B2.3, no failure data yet
- `ValidationReport` top-level (synthesizer_v1) — B2.3, no failure data
- Landing page generation schemas — not yet built (Phase 3 FE5)

Add observations to this file as they accumulate.
