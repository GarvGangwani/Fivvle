# Eval calibration run `eval-20260604T175622Z`

Generated at (UTC): 2026-06-04T18:18:27.612328+00:00

## Configuration

- Ideas (6): `slack-hr-bot, fitness-accountability, mechanic-marketplace, tax-loss-harvesting, visa-deadline-tracker, vague-ai-productivity`
- Eval user_id (filter handle): `de6b95d8-a385-40e3-b8a3-33ad70b8ef73`
- Output directory: `D:/Fivvle/docs/calibration/runs/eval-20260604T175622Z`
- Heavy artifacts: none (raw ValidationReport JSON not written)

## Per-idea results

| idea_id | experiment_id | slug | terminal_status | latency_s | cost_usd | citations | error_detail |
| --- | --- | --- | --- | ---: | ---: | ---: | --- |
| slack-hr-bot | `92b40feb-223d-4825-93cb-177aed480580` | `eval-slack-hr-bot-20260604T175622Z` | RESEARCH_READY | 130.4 | 0.6643 | 35 | — |
| fitness-accountability | `fe93c972-6812-4d26-a7be-9af81fd1e381` | `eval-fitness-accountability-20260604T175622Z` | RESEARCH_READY | 165.0 | 0.7292 | 28 | — |
| mechanic-marketplace | `9fb49b4b-9411-4b44-8ffc-532ae626d09f` | `eval-mechanic-marketplace-20260604T175622Z` | RESEARCH_READY | 168.8 | 0.6798 | 37 | — |
| tax-loss-harvesting | `82859fb0-72b3-4762-b4de-ddefe68471f5` | `eval-tax-loss-harvesting-20260604T175622Z` | RESEARCH_FAILED | 388.6 | 0.6419 | — | synthesizer:SynthesizerHallucinatedCitation: Hallucinated citation URL 'https://www.plaid.com/' in questions_and_find... |
| visa-deadline-tracker | `1bff3906-8125-460b-83cb-752c1eb4a1bc` | `eval-visa-deadline-tracker-20260604T175622Z` | RESEARCH_READY | 313.6 | 0.7084 | 36 | — |
| vague-ai-productivity | `ad815809-2f81-4c0b-9bd5-ca3ab9c9cc55` | `eval-vague-ai-productivity-20260604T175622Z` | RESEARCH_READY | 158.9 | 0.4537 | 21 | — |

## Tier-3 aggregate metrics

- **RESEARCH_READY rate:** 5/6 = 83.3%
- **Citation hallucination rate:** not computed (needs evidence set — Tavily/Reader URLs are not persisted on audit rows for post-hoc URL allowlists)
- **Citation count (sum across reports):** 157 (5 report(s) with persisted citations)
- **Mean cost per run:** $0.6462
- **P90 cost per run:** $0.7188
- **Mean latency per run:** 220.9s
- **P90 latency per run:** 351.1s

## Launch gates (Tier-3)

| Gate | Threshold | Actual | Pass |
| --- | --- | --- | --- |
| RESEARCH_READY rate | ≥ 95% | 83.3% | FAIL |
| Citation hallucination rate | 0% | not computed | SKIP |
| Mean cost per run | ≤ $1.80 | $0.6462 | PASS |

**Overall launch gate:** FAIL (hallucination gate skipped until evidence set is reachable)
