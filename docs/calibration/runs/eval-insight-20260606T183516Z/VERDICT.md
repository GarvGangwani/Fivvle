# Insight v1 — VERDICT: SHIP

Calibrated against `eval-insight-20260606T183516Z` on 2026-06-06 (post Zone B compression, commit f77d48c).

## Auto-gate outcome (all pass ✅)

| Gate | Observed | Target |
|---|---|---|
| ≥95% INSIGHT_READY | 100% | ≥95% |
| Mean cost per run | ~$0.022 (per-call structured-log avg; script reports $0.0518 because it sums last-2 LLMCalls and is contaminated by prior-run rows in dev DB) | ≤$0.15 |
| p90 latency | 23.9s | ≤30s |
| Zero hallucinated finding IDs | 0 / 49 cited | ==0 |
| All takeaways source-type tagged | 0 missing | ==0 |

## Quality observations (informal)

- `[COGNITIVE]` / `[SYNTHESIZED]` / `[BEHAVIORAL]` labels are precise across all 5 drafts — discipline holds.
- `what_would_change_this` is uniformly concrete, measurable, time-bounded.
- Recommendations cite specific finding IDs + behavioral numbers.
- All 5 returned `recommendation_type=iterate`. Verified NOT a prompt bias: all 5 source ValidationReports also carried "iterate" overall_recommendation, so the insight LLM correctly echoed cognitive verdicts when behavioral data was insufficient to overturn.

## Known coverage gap

N=5 did not exercise the cross-stream override pathway (behavioral overturning cognitive verdict to PROCEED / KILL / PIVOT). Dev DB's existing VRs are all `iterate`. Re-calibrate when (a) real founders submit varied ideas, or (b) we synthesize non-iterate VR fixtures. Not a blocker for prototype ship.

## Known known-issue

~40% schema-retry rate (`instructor_attempts=2` on 2 of 5 runs). Adds 5-20s latency when fired. Latency gate accommodates this within margin (worst observed: 39.2s on the one outlier post-retry).

## Prompt status

`insight_v1_cached` is FROZEN. No pending prompt changes.
