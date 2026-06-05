# Eval calibration run `eval-20260605T094240Z`

Generated at (UTC): 2026-06-05T09:50:05.057927+00:00

## Configuration

- Ideas (1): `tax-loss-harvesting`
- Eval user_id (filter handle): `de6b95d8-a385-40e3-b8a3-33ad70b8ef73`
- Output directory: `D:/Fivvle/docs/calibration/runs/eval-20260605T094240Z`
- Heavy artifacts: none (raw ValidationReport JSON not written)

## Per-idea results

| idea_id | experiment_id | slug | terminal_status | latency_s | cost_usd | citations | error_detail |
| --- | --- | --- | --- | ---: | ---: | ---: | --- |
| tax-loss-harvesting | `01b4f6da-4c61-49b4-9d95-3fa836e97a61` | `eval-tax-loss-harvesting-20260605T094240Z` | RESEARCH_READY | 444.8 | 0.6718 | 38 | — |

## Tier-3 aggregate metrics

- **RESEARCH_READY rate:** 1/1 = 100.0%
- **Citation hallucination rate:** not computed (needs evidence set — Tavily/Reader URLs are not persisted on audit rows for post-hoc URL allowlists)
- **Citation count (sum across reports):** 38 (1 report(s) with persisted citations)
- **Mean cost per run:** $0.6718
- **P90 cost per run:** $0.6718
- **Mean latency per run:** 444.8s
- **P90 latency per run:** 444.8s

## Launch gates (Tier-3)

| Gate | Threshold | Actual | Pass |
| --- | --- | --- | --- |
| RESEARCH_READY rate | ≥ 95% | 100.0% | PASS |
| Citation hallucination rate | 0% | not computed | SKIP |
| Mean cost per run | ≤ $1.80 | $0.6718 | PASS |

**Overall launch gate:** PASS (hallucination gate skipped until evidence set is reachable)
