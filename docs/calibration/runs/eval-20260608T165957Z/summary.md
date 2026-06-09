# Eval calibration run `eval-20260608T165957Z`

Generated at (UTC): 2026-06-08T17:02:42.924618+00:00

## Configuration

- Ideas (1): `slack-hr-bot`
- Eval user_id (filter handle): `de6b95d8-a385-40e3-b8a3-33ad70b8ef73`
- Output directory: `D:/Fivvle/docs/calibration/runs/eval-20260608T165957Z`
- Heavy artifacts: none (raw ValidationReport JSON not written)

## Per-idea results

| idea_id | experiment_id | slug | terminal_status | latency_s | cost_usd | citations | error_detail |
| --- | --- | --- | --- | ---: | ---: | ---: | --- |
| slack-hr-bot | `bef5fc81-4f0e-43b9-8c58-ae9d138d271d` | `eval-slack-hr-bot-20260608T165957Z` | RESEARCH_READY | 165.0 | 0.6183 | 35 | — |

## Tier-3 aggregate metrics

- **RESEARCH_READY rate:** 1/1 = 100.0%
- **Citation hallucination rate:** not computed (needs evidence set — Tavily/Reader URLs are not persisted on audit rows for post-hoc URL allowlists)
- **Citation count (sum across reports):** 35 (1 report(s) with persisted citations)
- **Mean cost per run:** $0.6183
- **P90 cost per run:** $0.6183
- **Mean latency per run:** 165.0s
- **P90 latency per run:** 165.0s

## Launch gates (Tier-3)

| Gate | Threshold | Actual | Pass |
| --- | --- | --- | --- |
| RESEARCH_READY rate | ≥ 95% | 100.0% | PASS |
| Citation hallucination rate | 0% | not computed | SKIP |
| Mean cost per run | ≤ $1.80 | $0.6183 | PASS |

**Overall launch gate:** PASS (hallucination gate skipped until evidence set is reachable)
