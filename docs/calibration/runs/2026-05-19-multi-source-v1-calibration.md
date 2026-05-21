# Calibration Run: Multi-Source Searcher v1 (Task M-1) — 2026-05-19

**Phase:** Searcher multi-source v1 (Tavily + Google Trends) + full five-phase pipeline (end-to-end smoke)

**Prompt version:** `planner_v1_cached`, `reader_v1_cached`, `refinement_v1`, `reflector_query_refinement_v1_cached`, `synthesizer_v3_cached`

**Model:** Claude Sonnet 4.6 (Anthropic), per `LLMCall.model` rows

**Branch / commit:** `main` @ `6f56983266be142b6dada96447a96a85d6a68b0c`

**Anthropic balance at start:** (not recorded this session)

**Tavily balance at start:** (not recorded this session)

**Ideas in calibration set:** 1 (N=1 consumer-shaped calibration; distinct from F-1 / H-4 B2B-ish baselines)

**Experiment ID (M-1):** `2310ec98-95f3-4cb0-ab57-afe38ed971e4`

**Baseline experiment IDs:** F-1 `53724f06-cb83-4c8a-92bd-e493e994ac34` · H-4 `f810fec6-6af3-4bb9-8b95-62e9a31b6fc1`

---

## Idea 1: Toddler sensory-play subscription box (consumer)

**Idea text:** “A subscription box for parents of toddlers that delivers one age-appropriate sensory-play activity per week, with all materials pre-measured and a 5-minute setup card. Targets parents 28-40 with kids aged 1-3 who feel guilty about screen time but lack time to plan activities.”

(`raw_idea` length **276** chars — above `min_length=50`; no padding required.)

**Status:** `RESEARCH_READY`

**Wall-clock (client smoke):** **530.67 s** (~8.8 min) — `PIPELINE_WALL_SECONDS` in stdout capture; poll 52/90 terminal.

**DB experiment timestamps (UTC):** `2026-05-19T16:42:59` → `2026-05-19T16:51:43` (~**524 s** span)

**Anthropic cost (sum `LLMCall.cost_usd`):** **$1.050996** (`n_llm=14`)

**Tavily cost (sum `ExternalAPICall.cost_usd`, `provider=tavily`):** **$0.528000** (`n_ext=33`)

**pytrends cost:** **$0.000000** (`n_ext=1`, `operation=fetch_trends`, **`success=false`**)

**Combined external + Anthropic:** **~$1.579**

**Prompt names observed:** `planner_v1_cached`, `reader_v1_cached`, `refinement_v1`, `reflector_query_refinement_v1_cached`, `synthesizer_v3_cached`

**Roll-up cache tokens (all LLM rows on this experiment):**

| Metric | Value |
|---|---:|
| `SUM(cached_input_tokens)` (cache reads) | 23,954 |
| `SUM(cache_creation_input_tokens)` (cache writes) | 67,212 |

### Cache behavior (cold vs warm)

**Cold-cache profile.** Total **cache_creation** (**67,212**) **exceeds** total **cached_input** (**23,954**) by **~43.3K tokens** — same first-run write-tax pattern as Task H-4 (ADR **0014** §15.1). **Not** a warm-cache amortization run.

**Reader cache reads = 0** on this traversal (Planner also 0 reads); Reflector + Synthesizer contribute all cache reads. Compare H-4: Reader had **5,026** read tokens — run-to-run variance, not multi-source-specific.

---

## Per-phase cost breakdown (`llm_calls`)

| phase | prompt_name | calls | Σ prompt_tokens | Σ cached_input | Σ cache_create | Σ completion | Σ cost_usd |
|---|---|---:|---:|---:|---:|---:|---:|
| planner | planner_v1_cached | 1 | 4,623 | 0 | 4,598 | 1,428 | 0.047656 |
| reader | reader_v1_cached | 7 | 78,288 | 0 | 36,288 | 11,625 | 0.487093 |
| refinement | refinement_v1 | 1 | 3,291 | 0 | 0 | 592 | 0.018753 |
| reflector | reflector_query_refinement_v1_cached | 4 | 16,060 | 5,816 | 8,188 | 417 | 0.044871 |
| synthesizer | synthesizer_v3_cached | 1 | 57,629 | 18,138 | 18,138 | 20,389 | 0.452623 |
| **All phases** | — | **14** | **159,891** | **23,954** | **67,212** | **34,451** | **1.050996** |

**External API (`external_api_calls`):**

| provider | operation | count | success | Σ cost_usd |
|---|---|---:|---|---:|
| tavily | search | 33 | 33/33 | 0.528000 |
| pytrends | fetch_trends | 1 | **0/1** | 0.000000 |

---

## Side-by-side vs F-1 and H-4 baselines

| Metric | F-1 (`53724f06…`) | H-4 (`f810fec6…`) | M-1 (`2310ec98…`) | M-1 vs F-1 | M-1 vs H-4 |
|---|---|---|---|---|---|
| Anthropic | $0.984777 | $0.919187 | $1.050996 | **+$0.066 (+6.7%)** | **+$0.132 (+14.3%)** |
| Tavily | $0.528 | $0.528 | $0.528 | **$0** | **$0** |
| pytrends | (not run) | (not run) | $0 (failed) | — | — |
| **Combined** | ~$1.513 | ~$1.447 | **~$1.579** | **+$0.066** | **+$0.132** |
| LLM rows | 19 | 14 | 14 | −5 | 0 |
| Wall-clock | ~561 s | ~404 s | **~531 s** | −30 s | +127 s |
| Status | `RESEARCH_READY` | `RESEARCH_READY` | `RESEARCH_READY` | — | — |
| Synthesizer prompt | `synthesizer_v2_cached` | `synthesizer_v2_cached` | **`synthesizer_v3_cached`** | version bump | version bump |

---

## Trends data captured

**Fetcher outcome:** **No series returned.** One `pytrends` `fetch_trends` call logged with **`success=false`** (`latency_ms≈10754`). Post-run diagnostic (separate from smoke) reproduced **`TooManyRequestsError`** after 3 retries — Google rate limit, not schema validation failure.

**Keywords planned (Searcher `_extract_trends_keywords` contract):** Built from `RefinedIdea` headline / `refined_one_liner` plus Planner `search_queries` (plan not persisted on `Experiment`; partial reconstruction from `refined_idea` JSON):

| Keyword / phrase (planned bag, partial) | Data returned |
|---|---|
| `One toddler activity, ready in 5 minutes, every week` (headline) | **No** (fetch failed) |
| `A weekly subscription box for parents of toddlers (ages 1–3) that delivers one pre-measured sensory-play activity with a 5-minute setup card — no planning, no supply runs required.` (`refined_one_liner`, 180 chars) | **No** |
| Planner `search_queries` (≤3 additional phrases, not stored on experiment row) | **Not observed** |

**Trajectory (max / min / direction per keyword):** **N/A** — no `TrendsSeries.points` populated.

**`trends_signals` in Synthesizer input:** **Absent / empty** — `synthesizer_v3` prompt had **no** `<trends_signals>` block (confirmed: zero occurrences of “google trends”, “search interest”, “interest over time” in `ValidationReport.raw_report` JSON).

---

## Quality assessment

**Citation count:** **47** URLs in `raw_report` findings + competitors; smoke API aggregate **`total_citation_count=53`** (includes duplicate hydration paths).

**Real-URL spot-check (sample):** URLs resolve to real third-party pages — e.g. `fractuslearning.com`, `nytimes.com/wirecutter`, `masandpas.com`, `cpsc.gov`, `community.whattoexpect.com`. No obviously fabricated domains in sample.

**Named competitors:** KiwiCo Panda Crate, Lovevery, Sensory TheraPlay Box, Highlights High Five Activity Box.

**`research_limitations`:** Honest about KiwiCo churn gaps, screen-time-guilt → subscription link unproven, CPSC testing costs — **does not** state that Google Trends demand data was unavailable (graceful-skip not surfaced to founder-facing limitations).

**`overall_recommendation`:** **iterate**

**Ship to founder?** **Conditional no** for a Trends-calibration sign-off: report quality on Tavily evidence is usable, but **this run did not exercise the multi-source value proposition** because Trends never landed. For a generic founder read, **yes with edits** — citations and competitor framing are credible; limitations block is strong except missing Trends gap disclosure.

---

## vs §6 cost projection (prompt-caching / pipeline economics)

Reference: `docs/planning/prompt-caching.md` §6 (**$0.20–0.35**/run illustrative Anthropic savings on warm cache) and `docs/planning/multi-source-searcher.md` §13 (**end-to-end under ~$1.50**).

| Projection | Observed (M-1) | Verdict |
|---|---|---|
| Warm-cache Anthropic savings $0.20–0.35 vs pre-cache | **Cold cache**; Anthropic **+$0.132** vs H-4, **+$0.067** vs F-1 | **Not validated** — write tax still dominates |
| Reader input “2–3×” absorbable post multi-source | Reader Σ `prompt_tokens` **78,288** vs H-4 **76,192** (~**+2.8%**) | **Not observed** — Reader unchanged by design; no extra evidence text |
| Pipeline **< ~$1.50** with Trends | **~$1.579** combined | **Refuted** (modestly over; driven by Anthropic + same Tavily bundle, not pytrends spend) |

---

## Findings — was Trends load-bearing?

**No.** Trends failed before any series reached `MergedSearchResults.trends` → `SynthesizerInput.trends_signals`. Synthesizer **did not** cite Trends trajectories (0 trend-language findings). Report conclusions rest on **Tavily / Reader** evidence (subscription-box comparables, safety/regulatory, guilt/retention gaps).

**Implication:** M-1 validates **graceful degradation** and **Tavily-only consumer report quality**, **not** the hypothesis that Trends signal improves consumer-shaped ideas vs F-1/H-4 baselines. **N=2** retry required after pytrends rate-limit cooldown (or mocked Trends fixture run) before ADR **0015/0016** promotion.

---

## Issues / surprises

1. **pytrends `TooManyRequestsError`** on the only `fetch_trends` attempt — pipeline still reached `RESEARCH_READY` (correct per ADR **0015**).
2. **`research_limitations` omits missing Trends** despite `.cursorrules` “note in report” degradation language — product/prompt gap.
3. **Anthropic +6.7% / +14.3%** vs baselines with **same 33 Tavily rows** — likely **`synthesizer_v3_cached`** larger completion (**20,389** vs H-4 **16,554**) plus cold-cache write volume, **not** Trends input size.
4. **Reflector ran** (4 refinement calls, `RESEARCH_REFLECTING` in `phases_completed`) — comparable to H-4; not a no-reflector fast path.
5. **Smoke auth friction:** `_get_token.py` password path unused; custom-token mint required correct Firebase uid (`…MVJ3CLB3` suffix) — operational note for future calibrations.

---

## Open questions for next calibration

1. **M-2:** Re-run **same idea** after pytrends cooldown (or from clean IP) to capture non-zero `TrendsSeries` and measure Synthesizer uptake.
2. Should **`research_limitations`** auto-include a bullet when `trends_signals` is empty due to integration failure?
3. **Synthesizer v3** dollar delta vs v2 on identical idea — isolate prompt version from Trends.
4. **Warm-cache second traversal** (H-4 follow-up pattern) with Trends succeeding — separate write-tax from read savings.
5. Persist **planned Trends keyword bag** (metadata only) on experiment or `ExternalAPICall` for calibration forensics without logging series values in production logs.

---

## References

- Procedure template: `docs/calibration/procedure.md`
- Companion artifact: `2026-05-19-multi-source-v1-calibration-stdout.txt`
- Planning: `docs/planning/multi-source-searcher.md`, `docs/planning/prompt-caching.md` §6
- ADRs (Proposed): **0015**, **0016**
- Baselines: `2026-05-17-reflector-warmup.md` (F-1), `2026-05-18-caching-calibration.md` (H-4)
