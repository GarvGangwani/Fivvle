# Insight calibration — eval-insight-20260606T180458Z

Prompt: `insight_v1_cached` (insight_v1_cached, pre-N=5 calibration)
Runs: 5

## Auto-gates

| Gate | Observed | Target | Pass |
|---|---|---|---|
| ≥95% INSIGHT_READY | 100.0 | >= 95.0% | ✅ |
| Mean cost ≤ $0.15 | 0.030555 | <= 0.15 | ✅ |
| p90 latency ≤ 30s | 58.75852959998883 | <= 30.0s | ❌ |
| Zero hallucinated IDs | 0 | == 0 | ✅ |
| All takeaways tagged with source_type | 0 | == 0 | ✅ |

## Per-run summary

| Label | Scenario | Success | Recommendation | Latency (s) | Cost ($) | Cited IDs | Invalid IDs | Missing source_type | WWCT chars |
|---|---|---|---|---|---|---|---|---|---|
| toddler-box | warm_only_low_volume | ✅ | iterate | 21.0 | 0.0218 | 10 | 0 | 0 | 493 |
| vet-scribe | cold_high_volume_no_conversion | ✅ | iterate | 58.8 | 0.0240 | 8 | 0 | 0 | 599 |
| auto-marketplace | insufficient_data | ✅ | iterate | 28.0 | 0.0394 | 5 | 0 | 0 | 476 |
| cart-recovery | bimodal_engagement | ✅ | iterate | 57.0 | 0.0225 | 6 | 0 | 0 | 525 |
| freelancer-loneliness | high_warm_high_conversion | ✅ | iterate | 88.2 | 0.0450 | 8 | 0 | 0 | 146 |

## Aggregates (success runs only)
- Mean cost: $0.0306
- Total cost: $0.1528
- Mean latency: 50.6s
- p90 latency: 58.8s

## Rubric — fill manually after reading each draft JSON

Per planning doc §10. Score each dimension 1-5. Median ≥ 4 across all five
dimensions and all five runs is the gate.

| Label | Non-obvious | Useful | Synthesis accuracy | Justification | Forward-looking |
|---|---|---|---|---|---|
| toddler-box | _ | _ | _ | _ | _ |
| vet-scribe | _ | _ | _ | _ | _ |
| auto-marketplace | _ | _ | _ | _ | _ |
| cart-recovery | _ | _ | _ | _ | _ |
| freelancer-loneliness | _ | _ | _ | _ | _ |

### Dimension definitions

- **Non-obvious (1-5)** — Does the report surface something the founder couldn't have figured out from raw numbers? 1 = restates obvious facts. 5 = genuine insight.
- **Useful (1-5)** — Does the report enable a concrete decision? 1 = vague. 5 = pointed action.
- **Synthesis accuracy (1-5)** — Are [SYNTHESIZED] takeaways genuine cross-stream claims? 1 = label is decorative. 5 = labels are precise; [BEHAVIORAL]/[COGNITIVE]/[SYNTHESIZED] are used correctly.
- **Justification quality (1-5)** — Are confidence_rationale fields meaningful? 1 = generic. 5 = each rationale references specific data.
- **Forward-looking (1-5)** — Is what_would_change_this concrete and measurable? 1 = generic. 5 = specific threshold, specific data type, reachable.

## Errors

None.