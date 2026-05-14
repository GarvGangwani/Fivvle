# Fivvle API Cost Ledger

Tracks all real-API spend incurred during development and testing.
Production spend tracked separately in Cloud Billing.

**Format:** Date (UTC) | Session | Provider | Call type | Reason | Est. cost (USD)

> Estimates use provider list pricing at time of call. Mark accidental/unintended
> calls with ⚠️. Intended end-to-end test runs with ✅.

---

## Log

| Date (UTC) | Session | Provider | Call type | Reason | Est. cost |
|---|---|---|---|---|---|
| 2026-05-14 | B2.4 smoke test | Anthropic | Planner input tokens (~1,400 tok, Claude Haiku) | ⚠️ Smoke test killed mid-planner; kill should have fired before `planner started` log line. Input tokens billed on request receipt. No output received. No Tavily calls (searcher never started). | ~$0.001 |

---

## Running total

| Provider | Total est. spend |
|---|---|
| Anthropic | ~$0.001 |
| Tavily | $0.00 |
| Groq | $0.00 |
| Reddit API | $0.00 (free tier) |
| **Grand total** | **~$0.001** |

---

## Balance checkpoints

| Date | Balance | Source |
|---|---|---|
| 2026-05-14 | $0.65 (Anthropic) | Noted in B2.4 prompt — real-API run gated on top-up |

## 2026-05-14 — B2.4 smoke + refinement calibration

| Date | Activity | Anthropic | Tavily | Notes |
|---|---|---|---|---|
| 2026-05-14 | Batch 2 smoke (killed during planner) | $0.001 | $0 | accidental, see B2.4 |
| 2026-05-14 | Refinement diagnostic (success) | ~$0.012 | $0 | 3129 in + 570 out, Sonnet 4.6 |
| 2026-05-14 | Failed smoke /experiments call | ~$0.018 | $0 | ValidationError on risks[4] |
| 2026-05-14 | 3 calibration diagnostics (all failed) | ~$0.054 | $0 | confirmed risks[*] / subheadline overflow pattern |

Running total: ~$0.085 of $10.65 budget.

### Projected marginal cost of graceful-retry path

After schema raise (250/190) + prompt length guidance, projected
ValidationError rate per refinement: ~5-15% (vs. observed 75% before
fix). Each retry adds ~$0.018. Projected per-1000-refinements cost
addition: ~$1-3. Acceptable.

If retry rate exceeds 20% sustained over a week, that's a signal to
re-calibrate `risks[*]` or `subheadline` per
`docs/llm-schema-calibration.md`.