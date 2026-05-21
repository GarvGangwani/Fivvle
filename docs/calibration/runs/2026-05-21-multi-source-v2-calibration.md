# Calibration Run: Multi-Source Searcher v2 (Task M-2) — 2026-05-21

**Phase:** Re-run of M-1 consumer idea after pytrends cooldown + quality fixes (Commits 5/6/7 on `main`)

**Prompt version:** `planner_v1_cached`, `reader_v1_cached`, `refinement_v1`, `reflector_query_refinement_v1_cached`, `synthesizer_v3_cached`

**Model:** Claude Sonnet 4.6 (Anthropic), per `LLMCall.model` rows

**Branch / commit:** `main` @ `7ffe83947a9df2ce080e42a7a62f3ef2e29957f7` (includes `16cbbfb` Trends disclosure, `7851ad4` Reader guard, `7ffe839` reflection telemetry)

**Anthropic balance at start:** (not recorded this session)

**Tavily balance at start:** (not recorded this session)

**Ideas in calibration set:** 1 (byte-identical to M-1 — isolates cooldown + fixes only)

**Experiment ID (M-2):** `d47261f9-00e4-4264-8832-7a8b0667fd56`

**Baseline experiment IDs:** M-1 `2310ec98-95f3-4cb0-ab57-afe38ed971e4` · F-1 `53724f06-cb83-4c8a-92bd-e493e994ac34` · H-4 `f810fec6-6af3-4bb9-8b95-62e9a31b6fc1`

---

## Idea 1: Toddler sensory-play subscription box (consumer) — identical to M-1

**Idea text:** “A subscription box for parents of toddlers that delivers one age-appropriate sensory-play activity per week, with all materials pre-measured and a 5-minute setup card. Targets parents 28-40 with kids aged 1-3 who feel guilty about screen time but lack time to plan activities.”

(`raw_idea` length **276** chars — same as M-1.)

**Status:** `RESEARCH_READY`

**Wall-clock (client smoke):** **741.10 s** (~12.4 min) — `PIPELINE_WALL_SECONDS` in stdout capture; poll 73/90 terminal.

**DB experiment timestamps (UTC):** `2026-05-21T17:56:51` → `2026-05-21T18:09:03` (~**732 s** span)

**Anthropic cost (sum `LLMCall.cost_usd`):** **$0.981813** (`n_llm=14`)

**Tavily cost (sum `ExternalAPICall.cost_usd`, `provider=tavily`):** **$0.528000** (`n_ext=33`)

**pytrends cost:** **$0.000000** (`n_ext=1`, `operation=fetch_trends`, **`success=false`**, `latency_ms≈10528`)

**Combined external + Anthropic:** **~$1.510**

**Prompt names observed:** `planner_v1_cached`, `reader_v1_cached`, `refinement_v1`, `reflector_query_refinement_v1_cached`, `synthesizer_v3_cached`

**Roll-up cache tokens (all LLM rows on this experiment):**

| Metric | Value |
|---|---:|
| `SUM(cached_input_tokens)` (cache reads) | 45,797 |
| `SUM(cache_creation_input_tokens)` (cache writes) | 55,086 |

### Cache behavior (cold vs warm)

**Mixed profile.** Total **cache_creation** (**55,086**) still **exceeds** total **cached_input** (**45,797**) at experiment roll-up — not a full warm-cache amortization run. **However**, **Synthesizer** row shows **`cached_in=34,838`** and **`cache_wr=2`** (M-1 Synthesizer had **18,138** read + **18,138** write) — **partial warm hit** on Synthesizer cache zone (same prompt family / cross-run). **Reader** contributed **5,143** cache reads (M-1 Reader reads **0**). **Not** within 1 h of M-1 (2026-05-19) — warm signal is cross-experiment prompt-cache reuse, not same-session Zone A.

---

## Per-phase cost breakdown (`llm_calls`)

| phase | prompt_name | calls | Σ prompt_tokens | Σ cached_input | Σ cache_create | Σ completion | Σ cost_usd |
|---|---|---:|---:|---:|---:|---:|---:|
| planner | planner_v1_cached | 1 | 4,590 | 0 | 4,565 | 1,451 | 0.047878 |
| reader | reader_v1_cached | 7 | 84,027 | 5,143 | 42,387 | 11,670 | 0.495671 |
| refinement | refinement_v1 | 1 | 3,291 | 0 | 0 | 563 | 0.018318 |
| reflector | reflector_query_refinement_v1_cached | 4 | 15,967 | 5,816 | 8,132 | 390 | 0.044147 |
| synthesizer | synthesizer_v3_cached | 1 | 55,740 | 34,838 | 2 | 20,176 | 0.375799 |
| **All phases** | — | **14** | **163,615** | **45,797** | **55,086** | **34,250** | **0.981813** |

**External API (`external_api_calls`):**

| provider | operation | count | success | Σ cost_usd |
|---|---|---:|---|---:|
| tavily | search | 33 | 33/33 | 0.528000 |
| pytrends | fetch_trends | 1 | **0/1** | 0.000000 |

---

## Three-fix validation (M-1 → M-2)

### (1) Trends — Commit 5 (`16cbbfb` Synthesizer v3 disclosure)

| Check | M-1 | M-2 | Verdict |
|---|---|---|---|
| `fetch_trends` success | **No** (`TooManyRequestsError`) | **No** (`ResponseError` in logs) | Cooldown **insufficient** — still no series |
| `<trends_signals>` in Synthesizer input | Absent | Absent (no data) | N/A |
| Trends cited in report body | 0 trend-language hits | 0 (`trends_term_occurrences_in_report_json=0`) | N/A |
| **v3 disclosure** in `research_limitations` | **No** | **No** (`research_limitations_trends_disclosure=False`) | **Commit 5 not validated** — prompt rule present but model did not emit required sentence |

### (2) Reader guard — Commit 6 (`7851ad4` normalization + instrumentation)

| Check | M-1 (pre-fix) | M-2 | Verdict |
|---|---|---|---|
| Guard event | `reader hallucinated quote` (no `failure_class`) | `reader quote guard trip` + `failure_class` | Instrumentation **works** |
| Trip tally (this run) | — | **11** trips: **10** `normalization_recovered`, **1** `unmatched`, **0** `boundary_overrun` | Most false-positive class **kept** (not nulled) |
| Questions **>10%** quote-null rate | **~5/7** (M-1 forensic replay, experiment `2310ec98`) | **1/7** (`q1` only; run-level `affected_question_ids=['q1']`, `total_quote_hallucinations=1`) | **Large improvement** — threshold trips **5/7 → 1/7** |
| Unmatched nulled quotes | All failures nulled | **1** unmatched nulled (`mysubscriptionaddiction.com`, `q1`) | Expected residual |

### (3) Reflection telemetry — Commit 7 (`7ffe839` `waves_used` → `reflection_loops_used`)

| Check | M-1 | M-2 | Verdict |
|---|---|---|---|
| `reflection_loops_used` (DB) | **0** (write-side bug) | **0** | **Not validated** |
| Reflector re-search executed | Yes (4 LLM rows) | Yes — `reflector partial re-search aggregate` **12/12** Tavily OK, 4 questions with new hits | Wave **would be 1** |
| Logs vs DB | N/A | **`reflector phase encountered unexpected error; degrading`** (`error_type=TypeError`) immediately after successful re-search — phase never completed | **Runtime blocker** — telemetry wiring not exercised on happy path |

---

## Side-by-side vs M-1, F-1, and H-4

| Metric | F-1 | H-4 | M-1 | M-2 | M-2 vs M-1 |
|---|---|---|---|---|---|
| Anthropic | $0.984777 | $0.919187 | $1.050996 | $0.981813 | **−$0.069 (−6.6%)** |
| Tavily | $0.528 | $0.528 | $0.528 | $0.528 | **$0** |
| Combined | ~$1.513 | ~$1.447 | **~$1.579** | **~$1.510** | **−$0.069** |
| LLM rows | 19 | 14 | 14 | 14 | 0 |
| Wall-clock | ~561 s | ~404 s | ~531 s | **~741 s** | +210 s |
| Status | `RESEARCH_READY` | `RESEARCH_READY` | `RESEARCH_READY` | `RESEARCH_READY` | — |
| pytrends | (n/a) | (n/a) | fail | fail | same outcome |

**vs ~$1.50 planning envelope:** M-2 **~$1.510** — **at envelope** (M-1 was **over** at ~$1.579).

---

## Trends data captured

**Fetcher outcome:** **No series returned.** One `pytrends` `fetch_trends` call with **`success=false`**; log: `pytrends fetch_trends failed` `error_type=ResponseError` (distinct from M-1 `TooManyRequestsError` — still no usable series).

**`trends_signals` in Synthesizer input:** **Absent / empty** — zero trend terms in `raw_report` JSON.

**Disclosure (Commit 5):** **Not observed** in `research_limitations` (691 chars; no Google Trends / search-interest unavailable sentence).

---

## Reader guard breakdown (log forensics, experiment `d47261f9…`)

| `failure_class` | Count |
|---|---:|
| `normalization_recovered` | 10 |
| `unmatched` | 1 |
| `boundary_overrun` | 0 |
| **Total guard trips** | **11** |

**Per-question >10% threshold:** **1/7** (`q1`, rate 1/7 ≈ 14.3% with 7 extractions carrying quotes).

**M-1 comparison:** Pre-fix forensic on `2310ec98…` reported **~5/7** questions over the 10% quote-null threshold with **no** `failure_class` breakdown (all trips treated as hallucinations).

---

## Quality assessment

**Citation count:** **48** URLs in `raw_report` JSON (`citation_count_from_json`); smoke API **`total_citation_count=48`**.

**`research_limitations`:** Strong on Reddit/COGS/FDA gaps — **missing** required Trends-unavailable disclosure (Commit 5).

**`overall_recommendation`:** **iterate**

**Ship to founder?** **Conditional no** for multi-source + telemetry sign-off: (a) Trends still absent, (b) disclosure rule not followed, (c) `reflection_loops_used` still 0 after live Reflector crash. **Conditional yes** for citation-quality delta: Reader guard fix materially reduced false nulling (**5/7 → 1/7** threshold trips).

---

## vs §6 cost projection

| Projection | Observed (M-2) | Verdict |
|---|---|---|
| Pipeline **< ~$1.50** with Trends | **~$1.510** | **Borderline** (under M-1, not under envelope on strict rounding) |
| Warm-cache Anthropic savings | Synthesizer **heavy read / negligible write** | **Partial** cross-run cache reuse |
| Trends load-bearing consumer signal | Still **no** series | **Not testable** until `fetch_trends` succeeds |

---

## Issues / surprises

1. **pytrends still failed** (`ResponseError`) — 2+ day cooldown did not restore series; M-2 cannot validate Trends caps or Synthesizer uptake.
2. **Commit 5 disclosure absent** despite empty `trends_signals` — prompt compliance gap or instruction strength issue.
3. **Commit 7 blocked live:** Reflector completed re-search then **`TypeError`** → degrade path → `reflection_loops_used=0` despite successful Tavily wave.
4. **Wall-clock +210 s vs M-1** — Synthesizer **626 s** LLM latency (Anthropic `520` retry + `instructor_attempts=2`) dominates; not Trends-related.
5. **Anthropic −6.6% vs M-1** with same Tavily bundle — Synthesizer cache read + lower reported `cost_usd` on large completion.

---

## Open questions / backlog

1. **Fix Reflector `TypeError`** after `reflector partial re-search aggregate` and re-run M-3 (same idea) to validate `reflection_loops_used`.
2. **pytrends:** diagnose `ResponseError` vs rate limit; consider mocked Trends fixture run for schema calibration.
3. **Trends disclosure:** enforce post-parse check or stronger prompt anchor when `trends_signals` empty.
4. **M-3** when Trends succeeds: measure real `TrendsSeries.points` length vs cap (520).
5. Do **not** promote ADR **0015/0016** on this data alone — human decision.

---

## References

- Procedure: `docs/calibration/procedure.md`
- Companion artifacts: `2026-05-21-multi-source-v2-calibration-stdout.txt`, `2026-05-21-m2-check-output.txt`, `2026-05-21-m2-uvicorn.log` (guard + reflector forensics)
- Prior run: `2026-05-19-multi-source-v1-calibration.md`
- Reader guard diagnosis (M-1 baseline): pre-fix replay on `2310ec98…` (~5/7 questions over threshold)
