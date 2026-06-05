# Eval calibration run `eval-20260604T174528Z`

Generated at (UTC): 2026-06-04T17:48:02.909482+00:00

## Configuration

- Ideas (1): `tax-loss-harvesting`
- Eval user_id (filter handle): `de6b95d8-a385-40e3-b8a3-33ad70b8ef73`
- Output directory: `D:/Fivvle/docs/calibration/runs/eval-20260604T174528Z`
- Heavy artifacts: none (raw ValidationReport JSON not written)

## Per-idea results

| idea_id | experiment_id | slug | terminal_status | latency_s | cost_usd | citations | error_detail |
| --- | --- | --- | --- | ---: | ---: | ---: | --- |
| tax-loss-harvesting | `5f78dd4f-cead-496d-a304-c165c9144f72` | `eval-tax-loss-harvesting-20260604T174528Z` | RESEARCH_READY | 154.3 | 0.6059 | 25 | — |

## Tier-3 aggregate metrics

- **RESEARCH_READY rate:** 1/1 = 100.0%
- **Citation hallucination rate:** not computed (needs evidence set — Tavily/Reader URLs are not persisted on audit rows for post-hoc URL allowlists)
- **Citation count (sum across reports):** 25 (1 report(s) with persisted citations)
- **Mean cost per run:** $0.6059
- **P90 cost per run:** $0.6059
- **Mean latency per run:** 154.3s
- **P90 latency per run:** 154.3s

## Launch gates (Tier-3)

| Gate | Threshold | Actual | Pass |
| --- | --- | --- | --- |
| RESEARCH_READY rate | ≥ 95% | 100.0% | PASS |
| Citation hallucination rate | 0% | not computed | SKIP |
| Mean cost per run | ≤ $1.80 | $0.6059 | PASS |

**Overall launch gate:** PASS (hallucination gate skipped until evidence set is reachable)
