# Eval calibration run `eval-20260601T095235Z`

Generated at (UTC): 2026-06-01T10:39:15.465195+00:00

## Configuration

- Ideas (6): `slack-hr-bot, fitness-accountability, mechanic-marketplace, tax-loss-harvesting, visa-deadline-tracker, vague-ai-productivity`
- Eval user_id (filter handle): `de6b95d8-a385-40e3-b8a3-33ad70b8ef73`
- Output directory: `D:/Fivvle/docs/calibration/runs/eval-20260601T095235Z`
- Heavy artifacts: none (raw ValidationReport JSON not written)

## Per-idea results

| idea_id | experiment_id | slug | terminal_status | latency_s | cost_usd | citations | error_detail |
| --- | --- | --- | --- | ---: | ---: | ---: | --- |
| slack-hr-bot | `077f27c2-d882-4dde-9461-926d5606fb8b` | `eval-slack-hr-bot-20260601T095235Z` | RESEARCH_READY | 506.9 | 0.6085 | 30 | — |
| fitness-accountability | `b1952f95-0ba8-48f5-a02e-b3ca3d5a298f` | `eval-fitness-accountability-20260601T095235Z` | RESEARCH_READY | 358.0 | 0.5254 | 33 | — |
| mechanic-marketplace | `fd237ba2-1f03-49c8-bc9e-0e44b41758af` | `eval-mechanic-marketplace-20260601T095235Z` | RESEARCH_READY | 654.2 | 0.8108 | 37 | — |
| tax-loss-harvesting | `bf187beb-e287-43b7-8cf8-cea9eed042ed` | `eval-tax-loss-harvesting-20260601T095235Z` | RESEARCH_READY | 474.5 | 0.5659 | 34 | — |
| visa-deadline-tracker | `d10311c5-2b2f-42a6-958d-a7c0ea8ee83b` | `eval-visa-deadline-tracker-20260601T095235Z` | RESEARCH_READY | 510.8 | 0.5842 | 30 | — |
| vague-ai-productivity | `69fd291d-adf9-4fc6-a64a-9f2ec1cbb44d` | `eval-vague-ai-productivity-20260601T095235Z` | RESEARCH_READY | 295.0 | 0.4467 | 28 | — |

## Tier-3 aggregate metrics

- **RESEARCH_READY rate:** 6/6 = 100.0%
- **Citation hallucination rate:** not computed (needs evidence set — Tavily/Reader URLs are not persisted on audit rows for post-hoc URL allowlists)
- **Citation count (sum across reports):** 192 (6 report(s) with persisted citations)
- **Mean cost per run:** $0.5902
- **P90 cost per run:** $0.7097
- **Mean latency per run:** 466.6s
- **P90 latency per run:** 582.5s

## Launch gates (Tier-3)

| Gate | Threshold | Actual | Pass |
| --- | --- | --- | --- |
| RESEARCH_READY rate | ≥ 95% | 100.0% | PASS |
| Citation hallucination rate | 0% | not computed | SKIP |
| Mean cost per run | ≤ $1.80 | $0.5902 | PASS |

**Overall launch gate:** PASS (hallucination gate skipped until evidence set is reachable)
