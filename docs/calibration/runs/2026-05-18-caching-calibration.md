# Calibration Run: Prompt caching (Task H-4) — 2026-05-18

**Phase:** Cross-pipeline prompt caching (Planner, Reader, Reflector, Synthesizer; Refinement unchanged)

**Prompt version:** `planner_v1_cached`, `reader_v1_cached`, `refinement_v1`, `reflector_query_refinement_v1_cached`, `synthesizer_v2_cached`

**Anthropic balance at start:** (not recorded this session)

**Tavily balance at start:** (not recorded this session)

**Ideas in calibration set:** 1 (N=1 cold-cache validation; intentionally matched to Task F-1 baseline idea)

**Experiment ID (cached run):** `f810fec6-6af3-4bb9-8b95-62e9a31b6fc1`

**Baseline experiment ID (pre-cache, Task F-1):** `53724f06-cb83-4c8a-92bd-e493e994ac34`

---

## Idea 1: Vague freelancer loneliness (intentional control)

**Idea text:** “Something to help freelancers be less lonely. Intentionally vague: no named product, platform, or monetization.”

**Status:** `RESEARCH_READY`

**Wall-clock:** ~404 s (~6.7 min); **08:20:33 → 08:27:17 UTC**

**Anthropic:** $0.919187 (**14** `llm_calls` rows)

**Tavily:** $0.528 (**33** `external_api_calls` rows)

**Prompt names observed:** `planner_v1_cached`, `reader_v1_cached`, `refinement_v1`, `reflector_query_refinement_v1_cached`, `synthesizer_v2_cached`

**Roll-up cache tokens (all LLM rows on this experiment):**

| Metric | Value |
|---|---:|
| `SUM(cached_input_tokens)` (cache reads) | 27,713 |
| `SUM(cache_creation_input_tokens)` (cache writes) | 59,235 |

### Caching-specific observations

**Write tax vs reads (first-run economics).** Total **cache_creation** (**59,235**) **exceeds** total **cached_input** (**27,713**) by **~31.5K tokens**. Cost on this arm is dominated by establishing Zone A breakpoints on a **cold cache** — consistent with ADR **0014** §15.1 (first caller pays writes; subsequent callers in TTL get discounted reads). **Cross-experiment Zone A reuse** within TTL is **not** exercised by this single run.

**Anthropic §6 illustration vs measured delta.** Narrative projections on the order of **$0.20–0.35**/run savings versus a pre-cache path were **optimistic vs N=1 observed** **−$0.0656** (**−6.7%**) against F‑1. Drivers: (1) cold-cache **write-multiplier** on **~59K** creation tokens consumes most of the expected read-side discount on the first traversal; (2) **five fewer** LLM rows vs F‑1 is **run-to-run Reflector variance**, not a caching attribution; (3) a **warm second run** inside **1 h Zone A TTL** would amortize write tax — **not measured here**.

---

## Per-phase cache token breakdown (`llm_calls`)

Query:

```sql
SELECT
  phase,
  prompt_name,
  COUNT(*) AS calls,
  SUM(prompt_tokens) AS total_prompt_tokens,
  SUM(COALESCE(cached_input_tokens, 0)) AS cached_input,
  SUM(COALESCE(cache_creation_input_tokens, 0)) AS cache_write,
  SUM(completion_tokens) AS completion_tokens,
  SUM(cost_usd) AS cost_usd
FROM llm_calls
WHERE experiment_id = 'f810fec6-6af3-4bb9-8b95-62e9a31b6fc1'
GROUP BY phase, prompt_name
ORDER BY phase, prompt_name;
```

**Result set (Postgres, 2026-05-18):**

| phase | prompt_name | calls | Σ prompt_tokens | Σ cached_input | Σ cache_create | Σ completion | Σ cost_usd |
|---|---|---:|---:|---:|---:|---:|---:|
| planner | planner_v1_cached | 1 | 4,529 | 0 | 4,504 | 1,407 | 0.046989 |
| reader | reader_v1_cached | 7 | 76,192 | 5,026 | 30,156 | 10,322 | 0.435854 |
| refinement | refinement_v1 | 1 | 3,250 | 0 | 0 | 508 | 0.017370 |
| reflector | reflector_query_refinement_v1_cached | 4 | 15,500 | 5,816 | 7,704 | 354 | 0.041886 |
| synthesizer | synthesizer_v2_cached | 1 | 50,802 | 16,871 | 16,871 | 16,554 | 0.377088 |
| **All phases** | — | **14** | **150,273** | **27,713** | **59,235** | **29,145** | **0.919187** |

**Share of cache reads by phase** (Σ cached_input = 27,713):

| phase | Σ cached_input | Share of run total |
|---|---:|---:|
| planner | 0 | 0% |
| reader | 5,026 | 18.1% |
| refinement | 0 | 0% |
| reflector | 5,816 | 21.0% |
| synthesizer | 16,871 | 60.9% |

---

## Side-by-side vs F-1 baseline

| Metric | F-1 (`53724f06…`, pre-cache `_v1` prompts) | H-4 (`f810fec6…`, cached) | Delta |
|---|---|---|---|
| Anthropic | $0.984777 | $0.919187 | **−$0.065590 (−6.7%)** |
| Tavily | $0.528 | $0.528 | **$0** |
| LLM rows | 19 | 14 | **−5** (Reflector variance — **not** a caching effect) |
| Wall-clock | ~561 s (~9.3 min) | ~404 s (~6.7 min) | **−157 s (−28%)** |
| Status | `RESEARCH_READY` | `RESEARCH_READY` | — |

---

## Quality spot-check (manual)

**Named competitors (examples):** Focusmate; Freelancers Union **SPARK**; Designer Hangout; Indie Hackers; Commit Action; Ship 30 for 30.

**Real citation domains (examples):** pewresearch.org; ipse.co.uk; leapers.co; investors.upwork.com; focusmate.com.

**`research_limitations`:** Explicitly notes **no WTP** evidence for peer-social products, **no churn/conversion** series, and **no freelancer-specific cohort postmortems** for peer-matching.

**`overall_recommendation`:** **iterate** — same epistemic stance as F‑1.

**Reasoning:** Comparable or slightly sharper than F‑1; highlights **income instability ranking above loneliness** as the primary paid-for pain in survey evidence.

---

## Open questions (follow-up)

1. **N=2 measurement:** Re-run the **same** idea (or same prompt versions with another idea) **within 1 h** to force **Zone A hits** on the second traversal and measure **true warm-cache** Anthropic $/run (write tax amortized).
2. **Per-phase cache hit ratio:** Which phases contribute most read tokens under multi-experiment reuse (this run: **Synthesizer ~61%** of reads; **Reader + Reflector** split the rest).
3. **Wall-clock −28%:** Separate **caching / fewer round-trips** from **Anthropic API latency variance** (control: compare two non-cached runs or two cached runs with identical LLM row counts).

---

## References

- Procedure template: `docs/calibration/procedure.md`
- Companion artifacts: `2026-05-18-caching-calibration-stdout.txt`, `2026-05-18-caching-calibration-report.json`
- Planning / ADR: `docs/planning/prompt-caching.md`, ADR **0014** §15.1 (write vs read economics)
