# Insight calibration â€” eval-insight-20260606T183516Z

Prompt: `insight_v1_cached` (insight_v1_cached, pre-N=5 calibration)
Runs: 5

## Auto-gates

| Gate | Observed | Target | Pass |
|---|---|---|---|
| â‰¥95% INSIGHT_READY | 100.0 | >= 95.0% | âœ… |
| Mean cost â‰¤ $0.15 | 0.051786 | <= 0.15 | âœ… |
| p90 latency â‰¤ 30s | 23.936829200014472 | <= 30.0s | âœ… |
| Zero hallucinated IDs | 0 | == 0 | âœ… |
| All takeaways tagged with source_type | 0 | == 0 | âœ… |

## Per-run summary

| Label | Scenario | Success | Recommendation | Latency (s) | Cost ($) | Cited IDs | Invalid IDs | Missing source_type | WWCT chars |
|---|---|---|---|---|---|---|---|---|---|
| toddler-box | warm_only_low_volume | âœ… | iterate | 19.6 | 0.0370 | 12 | 0 | 0 | 430 |
| vet-scribe | cold_high_volume_no_conversion | âœ… | iterate | 17.3 | 0.0393 | 9 | 0 | 0 | 554 |
| auto-marketplace | insufficient_data | âœ… | iterate | 23.9 | 0.0652 | 9 | 0 | 0 | 437 |
| cart-recovery | bimodal_engagement | âœ… | iterate | 39.2 | 0.0584 | 11 | 0 | 0 | 436 |
| freelancer-loneliness | high_warm_high_conversion | âœ… | iterate | 16.3 | 0.0590 | 8 | 0 | 0 | 385 |

## Aggregates (success runs only)
- Mean cost: $0.0518
- Total cost: $0.2589
- Mean latency: 23.3s
- p90 latency: 23.9s

## Rubric â€” fill manually after reading each draft JSON

Per planning doc Â§10. Score each dimension 1-5. Median â‰¥ 4 across all five
dimensions and all five runs is the gate.

| Label | Non-obvious | Useful | Synthesis accuracy | Justification | Forward-looking |
|---|---|---|---|---|---|
| toddler-box | _ | _ | _ | _ | _ |
| vet-scribe | _ | _ | _ | _ | _ |
| auto-marketplace | _ | _ | _ | _ | _ |
| cart-recovery | _ | _ | _ | _ | _ |
| freelancer-loneliness | _ | _ | _ | _ | _ |

### Dimension definitions

- **Non-obvious (1-5)** â€” Does the report surface something the founder couldn't have figured out from raw numbers? 1 = restates obvious facts. 5 = genuine insight.
- **Useful (1-5)** â€” Does the report enable a concrete decision? 1 = vague. 5 = pointed action.
- **Synthesis accuracy (1-5)** â€” Are [SYNTHESIZED] takeaways genuine cross-stream claims? 1 = label is decorative. 5 = labels are precise; [BEHAVIORAL]/[COGNITIVE]/[SYNTHESIZED] are used correctly.
- **Justification quality (1-5)** â€” Are confidence_rationale fields meaningful? 1 = generic. 5 = each rationale references specific data.
- **Forward-looking (1-5)** â€” Is what_would_change_this concrete and measurable? 1 = generic. 5 = specific threshold, specific data type, reachable.

## Errors

None.