# Eval calibration run `eval-20260605T063518Z`

Generated at (UTC): 2026-06-05T07:32:28.374837+00:00

## Configuration

- Ideas (6): `slack-hr-bot, fitness-accountability, mechanic-marketplace, tax-loss-harvesting, visa-deadline-tracker, vague-ai-productivity`
- Eval user_id (filter handle): `de6b95d8-a385-40e3-b8a3-33ad70b8ef73`
- Output directory: `D:/Fivvle/docs/calibration/runs/eval-20260605T063518Z`
- Heavy artifacts: none (raw ValidationReport JSON not written)

## Per-idea results

| idea_id | experiment_id | slug | terminal_status | latency_s | cost_usd | citations | error_detail |
| --- | --- | --- | --- | ---: | ---: | ---: | --- |
| slack-hr-bot | `a182d3db-7800-4656-84e2-606b7cacb823` | `eval-slack-hr-bot-20260605T063518Z` | RESEARCH_READY | 313.9 | 0.5695 | 27 | — |
| fitness-accountability | `b4bd9c25-8448-4d2f-8147-add2838e85a3` | `eval-fitness-accountability-20260605T063518Z` | RESEARCH_READY | 888.3 | 0.7922 | 50 | — |
| mechanic-marketplace | `323c30b7-9010-4177-b346-0b84687763c4` | `eval-mechanic-marketplace-20260605T063518Z` | RESEARCH_READY | 881.6 | 0.7406 | 39 | — |
| tax-loss-harvesting | `2356a8ae-21da-4ce1-950a-702774421ff1` | `eval-tax-loss-harvesting-20260605T063518Z` | RESEARCH_READY | 417.4 | 0.5863 | 36 | — |
| visa-deadline-tracker | `e745da6d-4f5e-4a8d-a466-5caded90efdb` | `eval-visa-deadline-tracker-20260605T063518Z` | RESEARCH_FAILED | 927.0 | 0.5038 | — | synthesizer:InstructorRetryException: <failed_attempts>  <generation number="1"> <exception>     Connection error. </... |
| vague-ai-productivity | `69aeaee4-9284-49cb-9de0-3ef5b9115593` | `eval-vague-ai-productivity-20260605T063518Z` | RESEARCH_FAILED | 1.4 | 0.0000 | — | planner:InstructorRetryException: <failed_attempts>  <generation number="1"> <exception>     Connection error. </exce... |

## Tier-3 aggregate metrics

- **RESEARCH_READY rate:** 4/6 = 66.7%
- **Citation hallucination rate:** not computed (needs evidence set — Tavily/Reader URLs are not persisted on audit rows for post-hoc URL allowlists)
- **Citation count (sum across reports):** 152 (4 report(s) with persisted citations)
- **Mean cost per run:** $0.5321
- **P90 cost per run:** $0.7664
- **Mean latency per run:** 571.6s
- **P90 latency per run:** 907.7s

## Launch gates (Tier-3)

| Gate | Threshold | Actual | Pass |
| --- | --- | --- | --- |
| RESEARCH_READY rate | ≥ 95% | 66.7% | FAIL |
| Citation hallucination rate | 0% | not computed | SKIP |
| Mean cost per run | ≤ $1.80 | $0.5321 | PASS |

**Overall launch gate:** FAIL (hallucination gate skipped until evidence set is reachable)
