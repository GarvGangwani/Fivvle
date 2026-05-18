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

## 2026-05-17 — Cost Ledger Audit (Task E)

This audit was run with `backend/scripts/cost_ledger_audit.py` against Postgres (`llm_calls` + `external_api_calls`). It reconciles roughly **$7.78** in Anthropic spend that earlier ledger entries did not itemize (the pre-audit narrative totaled on the order of **$0.085** for 2026-05-14 work; DB-backed Anthropic lifetime is **$7.863**). **Treat this section and the audit script output as the source of truth for recorded API spend** until superseded by a later audit; older narrative lines remain for history but are not additive with these totals.

| Date (UTC) | Experiment ID (last 8) | Phases touched | Anthropic $ | LLM call count |
|---|---|---|---|---|
| 2026-05-12 | `35811c04` | refinement | $0.060 | 2 |
| 2026-05-14 | `53d5a911` | planner, refinement, synthesizer | $0.769 | 4 |
| 2026-05-15 | `8bbe7016` | planner, reader, refinement, synthesizer | $0.811 | 10 |
| 2026-05-15 | `b3f82f44` | planner, reader, refinement, synthesizer | $1.016 | 19 |
| 2026-05-15 | `0b050940` | planner, reader, refinement, synthesizer | $0.964 | 10 |
| 2026-05-16 | `9cda9528` | planner, refinement | $0.018 | 2 |
| 2026-05-16 | `7fa34d6f` | planner, reader, refinement, reflector, synthesizer | $0.516 | 14 |
| 2026-05-16 | `83f6d00e` | planner, refinement | $0.056 | 2 |

**Orphan / NULL `experiment_id` bucket (not tied to an Experiment row)**

| Span (UTC) | Anthropic $ | Groq $ | LLM rows | Notes |
|---|---|---|---|---|
| 2026-05-12 through 2026-05-17 | $3.653 | ~$0.120 | 98 | Untracked warm-up / script invocations not bound to an Experiment row — process gap for future tracking. |

**Aggregate summary (audit snapshot)**

- Lifetime Anthropic LLM spend: **$7.863**
- Lifetime Groq LLM spend: **$0.120**
- Lifetime External API spend (recorded): **$0.000**
- Total combined: **$7.983**
- Distinct experiments: **8**
- Anthropic credit remaining: **$4.64**
- Mean Anthropic $/experiment: **$0.526**
- P90 Anthropic $/experiment: **$0.979**
- Runs remaining at mean: **~8**
- Runs remaining at p90: **~4**

## Anthropic Rate Limits — Tier 1 (verified 2026-05-17)

Limits as shown in `console.anthropic.com` (Tier 1).

| Model family | RPM | Input tokens/min | Output tokens/min |
|---|---|---|---|
| Claude Opus | 50 | 500,000 | 80,000 |
| Claude Sonnet | 50 | 30,000 (excluding cache reads) | 8,000 |
| Claude Haiku | 50 | 50,000 | 10,000 |
| Batch API | 50 requests/min | (across all models) | — |

**Note:** Sonnet input is likely the binding constraint at **30K tokens/min**. A post-Synthesizer-refactor warm-up run reported on the order of **58K input** tokens and still completed, which is consistent with the Instructor/SDK path using **prompt caching** (cache reads excluded from that input limit). Worth confirming with a quick measurement on the next full pipeline run.

## 2026-05-17 — Reflector warm-up (Task F-1)

Single-idea end-to-end smoke (`try_b2_4_end_to_end.py`, in-process dispatcher) targeting a **vague freelancer-loneliness** prompt. Pipeline reached **`RESEARCH_READY`**. Postgres aggregates from `scripts/cost_ledger_audit.py` after the run (experiment `53724f06-cb83-4c8a-92bd-e493e994ac34`).

| Date | Activity | Anthropic | Tavily | Notes |
|---|---|---|---|---|
| 2026-05-18 (UTC) | Reflector warm-up, idea 1 (freelancer loneliness, vague) | $0.985 | $0.528 | `RESEARCH_READY`; Reflector partial re-search 12/12 Tavily tasks OK |

**Subtotal (this line item):** Anthropic **$0.985** + Tavily **$0.528** ≈ **$1.513** combined.

### Average cost per pipeline run (this session only)

Single observation: **$0.985** Anthropic / run, **$0.528** Tavily / run, **~9.3 min** wall-clock (smoke client).

Compared to `.cursorrules` target of $0.25–$0.70 **per research engine run** (LLM + external, pre–full B3 complexity): **well above** — expected for **Claude Sonnet across refinement + planner + 11 reader calls + 4 reflector refinements + large synthesizer_v2 context** plus **33 billable Tavily rows**.

### Anthropic credit projection (checkpoint math)

If Anthropic credits **before** this run were ~**$4.64** remaining (ledger checkpoint from 2026-05-17 audit narrative), then **after** deducting ~**$0.985** ≈ **$3.65** remains. At this run’s marginal Anthropic cost, **~3** additional similar warm-up ideas fit before hitting that remainder (floor division); using the post-audit cohort **P90 ~$0.991**/experiment across nine tracked experiments suggests **~3–4** ideas as a realistic planning band.

---

### Known instrumentation gaps

1. **Tavily cost in DB:** Older runs often show **`cost_usd = 0`** for Tavily when the integration wrapper did not persist spend. **Task F-1 (2026-05-18)** recorded **non-zero** Tavily dollars on `ExternalAPICall` rows — treats earlier “always zero” statement as **historical**, not current.
2. **NULL `experiment_id` on LLM rows:** **98** `llm_calls` rows have **`experiment_id` NULL** (warm-up scripts, smoke runs, ad hoc dev calls). That is not a billing bug, but it is a **process gap**: that spend does not show up on per-experiment cost views. Defer a hard policy until production-launch hardening; track as a follow-up so dev workflows attach an experiment (or a dedicated “dev bucket”) consistently.
