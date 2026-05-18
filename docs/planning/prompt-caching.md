# Anthropic Prompt Caching — Planning Document

**Status:** DRAFT — pending human review  
**Phase:** Research engine (cross-cutting LLM cost optimization; applies to all Anthropic Sonnet phases via `backend/app/llm/client.py`)  
**Related ADRs to write:** See §12 (ADR number sequencing depends on multi-source Searcher ADRs **0014** / **0015**)  
**Authors:** Cursor Composer (planning artifact); human co-founder (review for v2)  

---

## 1. Problem Statement

Recent calibration and cost-ledger work show **per-run spend is dominated by input tokens** to the **Synthesizer** (on the order of **~50%** of Anthropic cost per experiment in representative warm-up runs) and the **Reader** fan-out (on the order of **~30%**), with the remainder spread across Planner, Refinement, Reflector, and retries.

The Reader executes **7–11 LLM calls per experiment** (7 questions baseline; additional calls when Reflector-triggered refinement re-runs Reader). Each call repeats **substantial shared context** — system instructions, RefinedIdea, ResearchPlan, and orchestration framing — that is billed at **full input rates on every call**. The **Synthesizer** makes a **single** call per experiment but carries a **very large** instruction + context prefix (~**48K input tokens** observed in calibration notes), so **input is again the main cost component** (~**$0.144** of ~**$0.49** Synthesizer spend tied to input at **$3/M** Sonnet list pricing in `backend/app/llm/cost.py`).

**Multi-source Searcher** ([`docs/planning/multi-source-searcher.md`](multi-source-searcher.md), **APPROVED**, pending implementation) will **grow Reader input materially** (Reddit/Trends surfaces, larger merged bundles). Without prompt caching, multi-source is likely to push full-pipeline cost **above** the product `.cursorrules` envelope of **~$1.50 per experiment** once Reader prompts absorb the extra evidence text.

**Anthropic prompt caching** ([Prompt caching](https://docs.claude.com/en/docs/build-with-claude/prompt-caching)) applies a **~90% discount** on **cache hits** for eligible input (provider-documented **10% of base input price** for cached read tokens vs standard input). Cache **writes** cost **more** than a plain request (provider-documented **1.25×** for **5-minute TTL** and **2×** for **1-hour TTL** on the written portion). This is fundamentally a **billing and plumbing** optimization: **no model downgrade**, **no change to output schema contracts**, **no new trust boundary** if dynamic content stays in non-cached segments — **highest ROI** among cost levers Fivvle can pull **before** expanding Reader inputs for multi-source.

**Product tie-in:** lower marginal cost per research run improves **unit economics** for a **free tier**, extends runway on Anthropic credits, and keeps **conversion to paid** plausible without tightening quality ceilings.

---

## 2. Constraints (Non-Negotiable)

The following rules apply to this design and any future implementation derived from it.

| Source | Constraint |
|--------|------------|
| `.cursorrules` — Model quality | **Do not downgrade models to save tokens.** Research phases use **Claude** (Sonnet **4.6** in current services such as `reader_service.py`, `planner_service.py`, `reflector_service.py`). **Caching applies to the same Sonnet models** — it is not a substitute for switching to Haiku. |
| `.cursorrules` — Logging | Use **`structlog`** for Python logging at all LLM call sites. |
| `.cursorrules` — Cost tracking | **`LLMCall`** (and related cost rollups) must record **every** paid LLM call. **Cached input** must be **distinguishable** from **standard / write** input in persisted rows and in **`cost_usd`** derivation (see §7). |
| `.cursorrules` — Budget | **Per-experiment cost target under ~$1.50.** Caching is intended to **defend** this envelope when multi-source increases Reader payloads — it is **not** permission to bypass budget discipline elsewhere. |
| `AGENTS.md` — Prompt injection | Caching **does not shrink** the injection surface. **Tavily / Reddit / Trends** (and any scraped text) remain **per-call dynamic** content, wrapped and labelled as **untrusted data** — **not** placed in silently reusable cached blocks without the same separation discipline. |
| `AGENTS.md` — Logging hygiene | **Never log** prompt bodies, cached blocks, or scraped content. Log **only** aggregate token counts, cache hit/miss/write **counts**, and safe metadata (phase, `prompt_name`, experiment id). |
| `ADR 0009` | **Pluggable dispatcher** — caching behaviour and **log field semantics** must be **identical** whether the pipeline runs **in-process** or via **HTTP / Cloud Function**. |
| Budget maths — write amplification | The **first** call that **populates** a cache breakpoint pays **higher** input cost on the written prefix (**1.25×** or **2×**, per Anthropic). Caching is a **long-run / amortized** win; **per-experiment** economics must account for **write vs read** (see §5–§6). |
| Implementation stack | **`backend/app/llm/client.py`** is the **canonical** wrapper — all phases must route Anthropic calls through it. **Instructor** + **Anthropic SDK** versions must **support** prompt caching for structured calls — confirm at implementation time and **pin** versions deliberately (see §14). |

---

## 3. Cache Taxonomy — What Gets Cached

Partition prompts into **three cache zones** by **stability**:

| Zone | Stability | Examples | Caching intent |
|------|-----------|----------|----------------|
| **A — Global stable** | Same across **all** experiments for a given prompt version | Versioned system instructions (`planner_v1`, `reader_v1`, `synthesizer_v2`), **JSON schema / field contract** descriptions, rubric skeleton | **Highest** reuse value; also eligible for **longer TTL** cross-experiment (§5) |
| **B — Per-experiment stable** | Stable for the **duration of one** `Experiment` / pipeline run | **RefinedIdea** text, **ResearchPlan** JSON/content, shared run metadata injected once | **Medium** value — reused across **Reader** calls, **Reflector** loops, and **Synthesizer** |
| **C — Per-call dynamic** | Different every call | **Tavily / Reddit** excerpts, **Trends** artefacts, **question_id**, single-question framing, tool-free search result payloads | **Never cached** — treat as **untrusted** user/web data per `AGENTS.md` |

**Cache breakpoints (Anthropic Messages API):** Anthropic supports **up to four** `cache_control` breakpoints **per request** (per [Prompt caching](https://docs.claude.com/en/docs/build-with-claude/prompt-caching)). A practical layout:

| Marker | Suggested attachment |
|--------|---------------------|
| **1** | End of **Zone A** (global instruction + schema block) |
| **2** | End of **Zone B** (RefinedIdea + ResearchPlan bundle) |
| **3–4** | Reserve for **additional stable prefixes** only if a phase splits instructions across multiple stable files **without** mixing Zone C content between breakpoints |

**Rule:** **Zone C must appear after** the last breakpoint that includes experiment-stable content, so dynamic scraped blobs never *precede* a marker that would cause accidental caching of volatile text.

---

## 4. Per-Phase Cache Strategy

| Phase | Zones used | Expected cache behaviour | TTL recommendation | Rationale |
|-------|--------------|-------------------------|---------------------|-----------|
| **Refinement** | A + B (idea only; plan may not exist yet) | **Single call** per experiment → **one read** of a cache block **within the same request** still pays **write** on first touch; **little fan-out** | Prefer **5-min** if caching at all; **likely skip v1** (see §15) | Low **amortization** unless the same prefix is **reused across many experiments** in a short window |
| **Planner** | A + B | **1–2 calls** typical | **5-min** for Zone B; **1-hour** optional for Zone A if Planner traffic is continuous | Helps second-chance / retry paths; not the largest spend bucket alone |
| **Reader** | A + B + C | **7–11+ calls** — **strong** reuse of A+B across fan-out | **Hybrid:** Zone A **1-hour**, Zone B **5-min** (§5) | **Primary** savings locus — every extra question hits shared prefixes |
| **Reflector** | A + C (+ possibly B in refinement prompts) | **0–4** calls; variable | **5-min** for any B-like experiment context | Smaller aggregate share today; align TTL with Reader if sharing Zone B in the **same run** |
| **Synthesizer** | A + B + C (evidence) | **1 call** but **very large** Zone A+B potential | **Hybrid** same as Reader within a run; Zone A benefits **cross-experiment** if **prompt version** stable | Large **absolute** input → large **absolute** savings on cache hits |

**Hit-rate intuition (not a guarantee):** Reader **Zone B** should approach **high** hit rates after call 1 in a run. **Zone A** may show **moderate** cross-experiment hits when the same **`prompt_name`** version is hot on the deployment. **Synthesizer** is **one call** per experiment for that phase, so **within-run** cache *reads* apply mainly if the **same** request re-enters after a **miss** (uncommon) — **cross-experiment** Zone A hits are the main **repeat** story.

---

## 5. TTL Decision Framework

Anthropic exposes **TTL choices** for cached content (per [Prompt caching](https://docs.claude.com/en/docs/build-with-claude/prompt-caching)):

| TTL | Write cost multiplier (cached prefix) | Break-even reads (provider pricing) |
|-----|--------------------------------------|-------------------------------------|
| **5 minutes** | **1.25×** | **1** subsequent read at standard discount |
| **1 hour** | **2×** | **2** subsequent reads |

**5-minute TTL** fits **within-experiment** reuse: Reader fan-out typically completes in **~60–120 seconds** of wall-clock (order-of-magnitude), well inside **5 minutes**. Reflector → Reader refinement cycles that stay **sequential and short** also remain inside the window **most** of the time.

**1-hour TTL** fits **Zone A** (global prompts + schema) when **many** experiments run on a **warm** deployment — the **first** experiment pays **write**; **later** experiments in the hour **read** the same prefix at **cache-hit** rates.

**Hybrid default (recommended for v2 adoption):**

- **`cache_control` on Zone A** → **1-hour TTL** (maximize cross-experiment reuse; accept **2×** write cost **once** per hour per warm prefix).
- **`cache_control` on Zone B** → **5-minute TTL** (minimize write multiplier on **per-experiment** text that **does not** benefit cross-experiment reuse).

**Trade-off:** Two breakpoints **add** SDK/composer complexity and must respect the **four-breakpoint** ceiling (§3). **Benefit:** Avoids paying **2×** write on **every** new founder’s RefinedIdea when only **global** instructions needed cross-run reuse.

---

## 6. Cost Model — Projected Savings

**Baseline (audit snapshot, documented in `docs/cost-ledger.md`):**

- **Mean** Anthropic **$/experiment:** **$0.526**
- **P90** Anthropic **$/experiment:** **$0.979**
- Reference single-run calibration: **`$0.985`** Anthropic for a **full B3-style** path (Task F-1 narrative, 2026-05-18 entry) — aligns with **~$1** order of magnitude for **heavy** runs.

**Synthesizer (illustrative):**

- Observed order-of-magnitude: **~48K input tokens**; at **$3/M** input → **~$0.144** input component (matches calibration note that ~**$0.144** of **~$0.49** is input-shaped).
- If **all 48K** were **cache hits** at **10%** of input price → **~$0.0144** effective vs **~$0.144** uncached → **~$0.13** **saved** on **that** idealized call **before** accounting for **writes** and **mixed** hit/miss reality.
- **Net Synthesizer savings** in the **~25%** range is a **planning** anchor, not a promise — **output tokens** and **partial** cache coverage reduce realised savings.

**Reader fan-out (illustrative):**

- **7–11 calls** × **~$0.03** **input-dominated** marginal cost per call (order-of-magnitude from calibration spread) → **shared Zone A+B** duplicated **6–10** times less expensively after the **first** populated cache.
- **Order-of-magnitude combined Anthropic savings per experiment:** **$0.20–$0.35** (**~20–35%** of total Anthropic per-experiment cost in the **$0.526 mean** world), i.e. **~40–60%** of **variable input-heavy** spend — **highly dependent** on **actual** hit rates and **write** volume.

**Multi-source amplification:** When Reader input grows **2–3×** on evidence text, **uncached** (Zone C) spend grows — but **Zones A+B** scale **sublinearly** if structure holds, so **cached fraction** of total input **rises** → **savings concentration** on Reader **increases**. That is why **caching before multi-source** is the **economic** prerequisite.

**Write amortization:** First touch **writes** the breakpoint; **subsequent reads** in TTL window pay **discounted** read pricing. **Reader** almost always **breaks even within one experiment** after the **first** cached call **reads** Zones A+B again (5-min TTL, **1.25×** write). **Zone A 1-hour** breaks even after **two** cross-experiment reads **within an hour** under **2×** write pricing (provider table).

---

## 7. Implementation Architecture

**Single source of truth:** extend **`complete_structured()`** in **`backend/app/llm/client.py`** to accept an explicit **cache layout** (e.g. `cache_breakpoints` / list of **content spans** + **TTL** choices) aligned with Anthropic’s **`cache_control`** API — **no** ad-hoc SDK calls in phase services.

**Per-phase services:** each service’s **prompt builder** splits **`system` + `user`** (or multi-block messages) into **cacheable prefixes** and **dynamic suffixes**, then passes the decomposition into **`complete_structured()`**.

**`LLMCall` schema:** add columns that split **input** into categories — **either** `cached_input_tokens` **plus** explicit **write/read** breakdown **or** split `prompt_tokens` into **`prompt_tokens_uncached` + `prompt_tokens_cached_read` + `prompt_tokens_cached_write`** (exact naming TBD at implementation). **Migration required.**

**`cost_usd`:** `compute_cost_usd` (or successor) must apply **cache read** rate (**0.1 ×** list input price for **cached read** tokens per Anthropic docs) and **write** multipliers (**1.25×** / **2×**) on the **appropriate** token buckets as returned by usage APIs.

**Logging — INFO (safe):** `cache_hit_count`, `cache_miss_count`, `cache_write_count` (or provider equivalents), **`cached_tokens`**, **`uncached_tokens`**, **per-call** — **never** log prompt text.

---

## 8. Failure Handling

| Scenario | Behaviour |
|----------|-----------|
| **Cache miss** | Normal — **not** an application error. Treated as **first population** or **expired** prefix. |
| **TTL expiry between calls** | Pipeline proceeds; **full input pricing** applies to **new** writes on next touch. **No retry** required for correctness. |
| **Provider-side eviction / failure** | Same as **miss** — **degraded cost**, **not** degraded output schema. |
| **Prompt / version drift** | Changing **`PROMPT_NAME`** or instruction text **invalidates** semantic equality — expect **new** writes. **Document** version bumps in prompt modules; **no** special-case recovery code required. |

---

## 9. Observability

| Layer | Fields / intent |
|-------|-----------------|
| **Per-call DEBUG** | `cache_breakpoint_count`, `cached_input_tokens`, `uncached_input_tokens`, `cache_creation_input_tokens` (write portion), `prompt_name`, `phase` |
| **Per-call INFO** | Counts only — **§7** |
| **Per-experiment summary (INFO at pipeline completion)** | `total_cache_hit_tokens`, `total_cache_write_tokens`, `total_uncached_input_tokens`, **`estimated_cost_without_caching`**, **`actual_cost_with_caching`**, **`savings_pct`** — definitions **implementation-owned** (this doc does not prescribe SQL shape) |

**Cost ledger tooling:** `backend/scripts/cost_ledger_audit.py` (per Task E baseline) should **eventually** surface **caching** metrics in a **follow-up** task. **Not** specified here.

---

## 10. State Machine Integration

**None.** Prompt caching is **transparent** to **`ExperimentStatus`**. **No** new states, transitions, or guards.

---

## 11. Files to Create / Modify

| File | Action | Notes |
|------|--------|-------|
| `backend/app/llm/client.py` | **Modify** | Extend `complete_structured()` with **cache breakpoint** plumbing; update **`cost_usd`** math for **cached** token buckets |
| `backend/app/db/models/llm_call.py` | **Modify** | Add **cached / uncached / write** token columns **or** split **`prompt_tokens`** — final column layout TBD |
| `backend/migrations/` | **New migration** | `LLMCall` schema update |
| `backend/app/services/refinement_service.py` | **Modify** | Split prompts into zones |
| `backend/app/services/planner_service.py` | **Modify** | Split prompts into zones |
| `backend/app/services/reader_service.py` | **Modify** | Split prompts — **highest** ROI |
| `backend/app/services/reflector_service.py` | **Modify** | Split prompts into zones |
| `backend/app/services/synthesizer_service.py` | **Modify** | Split prompts — **large** input |
| `backend/app/llm/prompts/refinement.py` | **Modify** | **Prefix layout** friendly to caching — **no** semantic drift vs v1 (verify in calibration) |
| `backend/app/llm/prompts/planner.py` | **Modify** | Same |
| `backend/app/llm/prompts/reader.py` | **Modify** | Same |
| `backend/app/llm/prompts/reflector_query_refinement.py` | **Modify** | Same |
| `backend/app/llm/prompts/synthesizer.py` | **Modify** | Same |
| `docs/adr/00NN-prompt-caching.md` | **New** | **ADR number = §12** |
| `backend/scripts/cost_ledger_audit.py` | **Modify (optional / follow-up)** | Surface **caching** aggregates |
| `backend/tests/llm/test_client.py` | **Modify** | **Caching** behaviour and **cost** decomposition tests |

---

## 12. ADR Stubs Required

**Title:** **Anthropic Prompt Caching for Research Engine Phases**

**Context:** Per-run cost is dominated by **Synthesizer + Reader** input; **multi-source Searcher** will **increase** Reader payloads; **ADR 0010–0013** do **not** cover **caching** semantics.

**Decision:** Implement **Anthropic prompt caching** in **`client.py`** with a **hybrid TTL** strategy (**5-min** for per-experiment stable blocks; **1-hour** for global instruction/schema blocks where appropriate), and **extend `LLMCall` cost accounting** to **split** cached vs uncached input.

**Reasoning summary:** **Multi-source** economic viability is **much safer** if **caching ships first** — **zero-quality** change if structured correctly.

**ADR numbering caveat:** [`docs/planning/multi-source-searcher.md`](multi-source-searcher.md) **reserves** **ADR 0014** (Multi-Source Search Inputs) and **ADR 0015** (Synthesizer Input Contract v2). [`docs/adr/README.md`](../adr/README.md) currently lists **0013** as the latest **numbered** record. **`0014` is the next free slot** if no other ADR is merged first — **if** multi-source lands **first**, prompt caching takes the **next** free number (**likely `0016`** after **0014** + **0015**). **Final** number chosen **at implementation time**.

---

## 13. Calibration Obligations

After implementation, run a **1-idea calibration** ( **Task H-1** / **F-1**-style):

| Obligation | Detail |
|------------|--------|
| **Cost reduction vs baseline** | Compare **Anthropic $/run** to **pre-cache** cohort — include **`$0.985`** F-1 Anthropic anchor **and** **`mean` / `p90`** from **cost ledger audit** |
| **Per-phase cache metrics** | Hit / miss / write **rates** by **`prompt_name`** |
| **Write amortization** | Confirm **Reader** fan-out shows **expected** **second-call** discounting on **shared** prefixes |

**`docs/llm-schema-calibration.md`:** **No** schema cap changes **expected**; if prompt **reordering** for cache layout affects **JSON shape** or **field population**, **flag** and **stop** rollout until resolved.

---

## 14. What This Document Does NOT Cover

- **Concrete prompt rewrites** and **exact** prefix ordering — **implementation** work; must preserve **semantic** contracts.
- **Anthropic SDK / Instructor** **exact** version pins — **dependency** decision at implementation.
- **OpenAI** prompt caching — **out of scope** until/if **OpenAI** is a **first-class** provider per **`ADR 0002`**.
- **Alembic** vs manual migration mechanics — **DB ops** choice.
- **Cross-experiment cache warming** jobs (e.g. **cron** that refreshes Zone A **every 50 minutes**) — **possible** future optimisation; **not** v1.

---

## 15. Decisions and Rationale + Open Questions

### 15.1 Decisions (planning-level)

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Cache topology** | **Three zones (A/B/C)** vs **one monolithic** cached blob | Prevents **accidentally** caching **scraped** content; matches **security** story in `AGENTS.md` |
| **TTL strategy** | **Hybrid** (**1-hour** Zone A + **5-min** Zone B) vs **single TTL everywhere** | Balances **cross-experiment** reuse vs **write** penalty on **per-founder** text |
| **Persistence** | **Split token columns / explicit cache buckets** in **`LLMCall`** vs **derived-only** reporting | **Auditability**, **admin** dashboards, and **circuit-breaker** **cost** truth |
| **Integration point** | **Single `client.py` extension** vs **per-phase** Anthropic SDK usage | **Enforces** `.cursorrules` **single-wrapper** rule and **ADR 0009** parity |
| **Shipping order** | **Caching before multi-source** (sequence **not** parallelised for economics) | Multi-source **amplifies** Reader tokens — **remove** **uncached** tax **first** |
| **Quality bar** | **No model downgrade** | Aligns with **`.cursorrules`** — caching is **not** a **Haiku** pivot |
| **Failure semantics** | **Cost-only** degradation on miss | **No** user-facing **status** change |

### 15.2 Open questions (for **v2** human revision)

1. **Refinement** is **one** LLM call per experiment — should it **opt out** of caching in **v1** because **write** cost may **exceed** **read** benefit unless **cross-experiment** Zone A traffic is **very** high?
2. If **5-min TTL** for Zone B **expires** in the **gap** between **Reader completion** and **late Reflector-driven Reader re-entry** (unlikely but **possible** on **slow** runs), do we need **any** **1-hour** **Zone B**, or **accept** full-price refresh — what is the **measurement** plan?
3. Should **Cloud Run / API startup** **pre-warm** Zone A (**one** **write** per deploy / hour) to **remove** **first-call** miss latency and cost for **first** experiment after **cold** start?
4. If **Synthesizer** **rubric** moves for **prefix** stability, does **output** **quality** change? **Gate** on **`ValidationReport` equivalence** calibration (`synthesizer_v2` vs **cached-layout** **v2**).
5. **`LLMCall`** migration — will **`NULL`** **legacy** rows for new **cache** columns **break** **admin** / **`cost_ledger_audit.py`** **aggregations**? **Define** **COALESCE** policy vs **backfill** job.

---

*Document status: **DRAFT — pending human review.** Intended revision path: **v1 → v2** after co-founder edit (mirrors `docs/planning/eval-set-discipline.md` discipline).*
