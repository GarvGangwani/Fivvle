# Eval calibration run `eval-20260601T083939Z`

Generated at (UTC): 2026-06-01T08:39:44.091633+00:00

## Configuration

- Ideas (1): `slack-hr-bot`
- Eval user_id (filter handle): `de6b95d8-a385-40e3-b8a3-33ad70b8ef73`
- Output directory: `D:/Fivvle/docs/calibration/runs/eval-20260601T083939Z`
- Heavy artifacts: none (raw ValidationReport JSON not written)

## Per-idea results

| idea_id | experiment_id | slug | terminal_status | latency_s | cost_usd | citations | error_detail |
| --- | --- | --- | --- | ---: | ---: | ---: | --- |
| slack-hr-bot | `3c552ba1-d9d5-4b88-8310-c97209235d3e` | `eval-slack-hr-bot-20260601T083939Z` | RESEARCH_FAILED | 4.1 | 0.0000 | — | planner:InstructorRetryException: <failed_attempts>  <generation number="1"> <exception>     Error code: 400 - {'erro... |

## Tier-3 aggregate metrics

- **RESEARCH_READY rate:** 0/1 = 0.0%
- **Citation hallucination rate:** not computed (needs evidence set — Tavily/Reader URLs are not persisted on audit rows for post-hoc URL allowlists)
- **Citation count (sum across reports):** 0 (0 report(s) with persisted citations)
- **Mean cost per run:** $0.0000
- **P90 cost per run:** $0.0000
- **Mean latency per run:** 4.1s
- **P90 latency per run:** 4.1s

## Launch gates (Tier-3)

| Gate | Threshold | Actual | Pass |
| --- | --- | --- | --- |
| RESEARCH_READY rate | ≥ 95% | 0.0% | FAIL |
| Citation hallucination rate | 0% | not computed | SKIP |
| Mean cost per run | ≤ $1.80 | $0.0000 | PASS |

**Overall launch gate:** FAIL (hallucination gate skipped until evidence set is reachable)
