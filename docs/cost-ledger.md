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
- Distinct experiments: **8** (listed in table above — audit date 2026-05-17)
- Anthropic credit remaining (checkpoint at audit narrative): **$4.64**
- Mean Anthropic $/experiment: **$0.526**
- P90 Anthropic $/experiment: **$0.979**
- Runs remaining at mean: **~8**
- Runs remaining at p90: **~4**

### Tracked cohort — projection refresh (2026-05-18, includes F‑1 + H‑4)

Eight audit experiments above **plus** Task F‑1 (`53724f06…`, **$0.984777** Anthropic) **plus** Task H‑4 (`f810fec6…`, **$0.919187** Anthropic). Sorted costs → linear **p90**.

| Metric | Value |
|---|---|
| n | **10** |
| Mean Anthropic $/experiment | **$0.611** |
| P90 Anthropic $/experiment | **$0.988** |
| Checkpoint remaining (after H‑4) | **~$2.73** (≈ `$3.65` post F‑1 minus **$0.919187**) |
| Floor runs @ mean | **4** (`$2.73 / $0.611`) |
| Floor runs @ p90 | **2** (`$2.73 / $0.988`) |

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

If Anthropic credits **before** Task F‑1 were ~**$4.64** remaining (ledger checkpoint from 2026-05-17 audit narrative), then **after F‑1 (~$0.985)** ≈ **$3.65** remains as the working checkpoint. After **Task H‑4 caching smoke (~$0.919** Anthropic) on the same vague‑idea rerun, ≈ **$2.73** remains. Multi-run planning uses the **ten‑experiment cohort mean/p90** (**$0.611** / **$0.988**) in the **Tracked cohort — projection refresh** table under the audit section above.

---

## 2026-05-18 — Caching calibration (Task H-4)

Single-idea end-to-end smoke on experiment **`f810fec6-6af3-4bb9-8b95-62e9a31b6fc1`**: same intentionally vague freelancer‑loneliness idea as Task F‑1 (`53724f06-cb83-4c8a-92bd-e493e994ac34`), with **`*_cached` planner/reader/reflector/synthesizer** prompts and **`refinement_v1`** unchanged. Pipeline reached **`RESEARCH_READY`**. Timestamps: **08:20:33 → 08:27:17 UTC** (~**404 s** wall‑clock). Calibration detail: `docs/calibration/runs/2026-05-18-caching-calibration.md`.

| Date | Activity | Anthropic | Tavily | Notes |
|---|---|---|---|---|
| 2026-05-18 (UTC) | Caching calibration (H‑4), same idea as F‑1 | $0.919187 | $0.528 | `RESEARCH_READY`; **14** LLM rows, **33** billable Tavily rows |

**Subtotal (this line item):** Anthropic **$0.919187** + Tavily **$0.528** ≈ **$1.447** combined.

### Comparison vs Task F‑1 baseline

| Metric | F‑1 (`53724f06…`, pre-cache `_v1` prompts) | H‑4 (`f810fec6…`, cached layout) | Delta |
|---|---|---|---|
| Anthropic | $0.984777 (19 LLM rows) | $0.919187 (14 LLM rows) | **−$0.065590 (−6.7%)** |
| Tavily | $0.528 (33 ext rows) | $0.528 (33 ext rows) | **$0** |
| Wall‑clock | ~561 s | ~404 s (−157 s, **−28%**) | |

Interpretation notes: **§6** illustrative **$0.20–0.35/run** Anthropic savings on a **first-run cold cache** are **not observed** — **write tax** dominates (**~59.2K** cache creation tokens vs **~27.7K** cache reads in DB). Fewer Anthropic rows vs F‑1 is predominantly **Reflector variance**, not attribution to caching mechanics; see calibration sheet.

### Projection refresh vs nine-experiment cohort (F‑1 only)

Nine-way cohort (audit **eight + F‑1**) **mean ~$0.577**, **p90 ~$0.991** — consistent with the F‑1 section’s “nine tracked experiments” narrative. Adding H‑4: **mean $0.611**, **p90 $0.988** (see audit **Tracked cohort — projection refresh** table).

---

## 2026-05-19 — Multi-Source Searcher v1 calibration (Task M-1)

Single-idea end-to-end smoke on experiment **`2310ec98-95f3-4cb0-ab57-afe38ed971e4`**: **consumer-shaped** toddler sensory-play subscription box (distinct from F‑1 / H‑4 freelancer-loneliness baselines). Pipeline reached **`RESEARCH_READY`**. Timestamps: **16:42:59 → 16:51:43 UTC** (~**524 s** DB span; **530.67 s** smoke client). Calibration detail: `docs/calibration/runs/2026-05-19-multi-source-v1-calibration.md`.

| Date | Activity | Anthropic | Tavily | pytrends | Notes |
|---|---|---|---|---|---|
| 2026-05-19 (UTC) | Multi-source v1 calibration (M‑1), toddler subscription box | $1.050996 | $0.528 | $0.00 | `RESEARCH_READY`; **14** LLM rows, **33** Tavily rows; **1** pytrends call **`success=false`** (`TooManyRequestsError`) |

**Subtotal (this line item):** Anthropic **$1.050996** + Tavily **$0.528** ≈ **$1.579** combined (**above** planning-doc **~$1.50** envelope).

### Comparison vs Task F‑1 and H‑4 baselines

| Metric | F‑1 | H‑4 | M‑1 | M‑1 vs F‑1 | M‑1 vs H‑4 |
|---|---|---|---|---|---|
| Anthropic | $0.984777 | $0.919187 | $1.050996 | **+$0.066 (+6.7%)** | **+$0.132 (+14.3%)** |
| Tavily | $0.528 | $0.528 | $0.528 | **$0** | **$0** |
| Combined | ~$1.513 | ~$1.447 | **~$1.579** | **+$0.066** | **+$0.132** |
| Wall‑clock | ~561 s | ~404 s | ~531 s | −30 s | +127 s |

Interpretation: **Trends signal not exercised** (pytrends rate-limited); report quality reflects **Tavily + B3** only. **`synthesizer_v3_cached`** and cold-cache write tax drive Anthropic delta vs H‑4, not Reader input growth (Reader prompt tokens **+2.8%** vs H‑4).

### Tracked cohort — projection refresh (includes M‑1)

Eleven experiments: audit **eight** + F‑1 + H‑4 + M‑1. Re-run `scripts/cost_ledger_audit.py` for exact mean/p90; provisional from M‑1 Anthropic **$1.051** vs prior **p90 ~$0.988** → expect **p90 at or above ~$1.05** until more runs land.

---

## 2026-05-21 — Multi-Source Searcher v2 calibration (Task M-2)

Single-idea end-to-end smoke on experiment **`d47261f9-00e4-4264-8832-7a8b0667fd56`**: **byte-identical** toddler sensory-play subscription box to Task M‑1 (`2310ec98…`), after Commits 5/6/7 on `main` @ `7ffe839`. Pipeline reached **`RESEARCH_READY`**. Timestamps: **17:56:51 → 18:09:03 UTC** (~**732 s** DB span; **741.10 s** smoke client). Calibration detail: `docs/calibration/runs/2026-05-21-multi-source-v2-calibration.md`.

| Date | Activity | Anthropic | Tavily | pytrends | Notes |
|---|---|---|---|---|---|
| 2026-05-21 (UTC) | Multi-source v2 calibration (M‑2), same idea as M‑1 | $0.981813 | $0.528 | $0.00 | `RESEARCH_READY`; **14** LLM rows, **33** Tavily; **1** pytrends **`success=false`** (`ResponseError`); Reader guard trips **11** (**10** `normalization_recovered`, **1** `unmatched`); `reflection_loops_used=0` (Reflector `TypeError` after re-search) |

**Subtotal (this line item):** Anthropic **$0.981813** + Tavily **$0.528** ≈ **$1.510** combined (**below** M‑1 ~$1.579; **at** ~$1.50 envelope).

### Comparison vs Task M‑1

| Metric | M‑1 | M‑2 | Delta |
|---|---|---|---|
| Anthropic | $1.050996 | $0.981813 | **−$0.069 (−6.6%)** |
| Tavily | $0.528 | $0.528 | **$0** |
| Combined | ~$1.579 | **~$1.510** | **−$0.069** |
| Wall‑clock | ~531 s | ~741 s | +210 s (Synthesizer retry/latency) |
| pytrends | fail (`TooManyRequests`) | fail (`ResponseError`) | still no Trends series |
| Reader >10% threshold trips | ~5/7 questions | **1/7** (`q1`) | guard fix validated |
| Trends disclosure in report | No | No | Commit 5 not observed |
| `reflection_loops_used` | 0 | 0 | Commit 7 blocked by Reflector `TypeError` |

### Tracked cohort — projection refresh (includes M‑2)

Twelve experiments: audit **eight** + F‑1 + H‑4 + M‑1 + M‑2. Re-run `scripts/cost_ledger_audit.py` for exact mean/p90.

---

### Known instrumentation gaps

1. **Tavily cost in DB:** Older runs often show **`cost_usd = 0`** for Tavily when the integration wrapper did not persist spend. **Task F-1 (2026-05-18)** recorded **non-zero** Tavily dollars on `ExternalAPICall` rows — treats earlier “always zero” statement as **historical**, not current.
2. **NULL `experiment_id` on LLM rows:** **98** `llm_calls` rows have **`experiment_id` NULL** (warm-up scripts, smoke runs, ad hoc dev calls). That is not a billing bug, but it is a **process gap**: that spend does not show up on per-experiment cost views. Defer a hard policy until production-launch hardening; track as a follow-up so dev workflows attach an experiment (or a dedicated “dev bucket”) consistently.
