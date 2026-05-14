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
