# Eval calibration run `eval-20260528T061835Z`

Generated at (UTC): 2026-05-28T06:57:22.292436+00:00

## Configuration

- Ideas (6): `slack-hr-bot, fitness-accountability, mechanic-marketplace, tax-loss-harvesting, visa-deadline-tracker, vague-ai-productivity`
- Eval user_id (filter handle): `6c1369ad-e712-4c9d-8257-1603b6bb6bf4`
- Output directory: `D:/Fivvle/docs/calibration/runs/eval-20260528T061835Z`
- Heavy artifacts: none (raw ValidationReport JSON not written)

## Per-idea results

| idea_id | experiment_id | slug | terminal_status | latency_s | cost_usd | citations | error_detail |
| --- | --- | --- | --- | ---: | ---: | ---: | --- |
| slack-hr-bot | `1dde15e7-fb23-4e73-9c1a-e1b8558f4461` | `eval-slack-hr-bot-20260528T061835Z` | RESEARCH_READY | 345.3 | 1.5338 | 46 | — |
| fitness-accountability | `e1f5e2cc-551f-4f1f-a71f-643024ffac76` | `eval-fitness-accountability-20260528T061835Z` | RESEARCH_READY | 449.9 | 1.4548 | 35 | — |
| mechanic-marketplace | `08bb82d0-0ec1-427c-80e0-a340ea423f7d` | `eval-mechanic-marketplace-20260528T061835Z` | RESEARCH_READY | 368.1 | 1.0959 | 43 | — |
| tax-loss-harvesting | `74329f55-3cfb-4ab9-baa7-e18cf9781e78` | `eval-tax-loss-harvesting-20260528T061835Z` | RESEARCH_READY | 306.8 | 1.4045 | 42 | — |
| visa-deadline-tracker | `386fdda7-6811-40ab-bb56-551ae493ade3` | `eval-visa-deadline-tracker-20260528T061835Z` | RESEARCH_READY | 439.5 | 1.5437 | 38 | — |
| vague-ai-productivity | `b00090fc-3339-43e8-aa11-221ad0cf9bf1` | `eval-vague-ai-productivity-20260528T061835Z` | RESEARCH_READY | 416.7 | 1.0075 | 39 | — |

## Tier-3 aggregate metrics

- **RESEARCH_READY rate:** 6/6 = 100.0%
- **Citation hallucination rate:** not computed (needs evidence set — Tavily/Reader URLs are not persisted on audit rows for post-hoc URL allowlists)
- **Citation count (sum across reports):** 243 (6 report(s) with persisted citations)
- **Mean cost per run:** $1.3400
- **P90 cost per run:** $1.5387
- **Mean latency per run:** 387.7s
- **P90 latency per run:** 444.7s

## Launch gates (Tier-3)

| Gate | Threshold | Actual | Pass |
| --- | --- | --- | --- |
| RESEARCH_READY rate | ≥ 95% | 100.0% | PASS |
| Citation hallucination rate | 0% | not computed | SKIP |
| Mean cost per run | ≤ $1.80 | $1.3400 | PASS |

**Overall launch gate:** PASS (hallucination gate skipped until evidence set is reachable)
