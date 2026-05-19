# Multi-Source Searcher — Planning Document

**Status:** APPROVED — co-founder reviewed, decisions resolved, Reddit deferred to v2 pending commercial Data API approval, implementation prompt pending.
**Phase:** Searcher (parallel multi-source evidence collection; extends ADR 0004 Searcher step)  
**Related ADRs to write:** ADR 0014 (Multi-Source Search Inputs); ADR 0015 (Synthesizer Input Contract v2 — 5-field contract with `trends_signals`)  
**Authors:** Cursor Composer (planning artifact); human co-founder (approval)

**v3 update (Reddit deferred):** Reddit integration is removed from v1 scope. Reason: Reddit's Responsible Builder Policy (https://support.reddithelp.com/hc/en-us/articles/42728983564564) requires written commercial approval for AI / commercial use of Reddit data, which Fivvle would require. v1 multi-source ships as Tavily + Google Trends only. Reddit becomes a v2 question contingent on obtaining commercial Data API approval. All §6 (Reddit Integration Detail) content is retained for v2 reference but is NOT part of v1 implementation. §11 file list, §12 ADR stubs, and §15 decisions table are updated accordingly.

---

## 1. Problem Statement

Fivvle's research engine currently uses **Tavily-only** for the Searcher phase (`backend/app/services/searcher_service.py`). Tavily produces **strong evidence for B2B and professional ideas** (company news, analyst-style pages, product documentation, industry coverage). Calibration after the Synthesizer warm-up confirms that pattern: **structured professional surfaces rank well in Tavily's index**.

Tavily is **thin or skewed** for many **consumer-driven, community-led, or emergent-product** ideas:

- **Consumer pain-point validation** — day-to-day friction often lives in forums, long-tail blogs, and app-store complaint patterns before it surfaces as "news." Tavily may return generic SEO pages while the decisive signal is **how people talk about the problem** in communities.
- **Niche communities** — small verticals (hobbies, regional markets, subculture tools) may have **little indexable professional press** but **rich Reddit threads** with concrete complaints, workarounds, and product comparisons.
- **Time-series / demand signals** — whether search interest is **rising, stable, or spiky** is not reliably captured by static web snippets; **Google Trends** provides a **numerical trajectory** that Tavily cannot substitute.
- **Emerging-product and "is this a thing?" searches** — early products and Twitter-era narratives move faster than crawl+rank cycles optimized for evergreen pages.

**Why this matters now.** Report quality is the product differentiator (`.cursorrules` **Quality Discipline** — defensible claims, honest gaps, citations). Post–Synthesizer warm-up showed **strong B2B-shaped outcomes** where Tavily excels; **the long tail of founder ideas** needs **community and demand signals** to reach the same bar. The prior `.cursorrules` line *"Don't add more sources until usage data shows they're needed"* was appropriate for the POC; **post–Synthesizer calibration is that signal**.

**Architectural alignment.** ADR **0004** already describes the Searcher as **parallel API calls (Tavily, Reddit free tier, Google Trends, news)** — i.e. **multi-source search is part of the intended 5-phase design**, not a scope expansion. The full **Build Order** in `.cursorrules` (B3) likewise lists **parallel multi-source searches (Reddit, Trends)** as part of the **full 5-phase workflow**. This planning document closes the gap between **Tavily-only implementation** and that **documented architecture**.

---

## 2. Constraints (Non-Negotiable)

The following rules apply to this design and any future implementation derived from it.

| Source | Constraint |
|--------|-------------|
| `.cursorrules` — Tech stack | **Reddit (PRAW free tier)** — read-only research only, **under 60 req/min**. |
| `.cursorrules` — Tech stack | **pytrends** — Google Trends **with fallback** when unreliable. |
| `.cursorrules` — Reliability / degradation | **Reddit rate-limited:** skip Reddit signals; note in report. **Trends flaky:** retry 3× then continue without; note in report. |
| `.cursorrules` — Timeouts | Reddit: 15s; Google Trends: 15s (per integration call). |
| `.cursorrules` — Logging | **`structlog`** for Python logging. |
| `AGENTS.md` — Prompt injection | Reddit content is **untrusted user-generated text**. Same pattern as Tavily: **clear data/instruction separation**, content wrapped in labelled tags; the model must treat embedded "instructions" inside data as **non-instructions**. |
| `AGENTS.md` — Logging hygiene | **Never** log Reddit post body or comment text — only safe metadata (counts, ids, subreddit name as opaque label if needed, error types). |
| `AGENTS.md` — Integrations | All external API calls go through `backend/app/integrations/` — **no** direct `httpx` / provider SDK calls elsewhere. Wrappers must use **circuit breaker + retry + cost tracking** consistent with existing integrations (see `tavily.py`). |
| `ADR 0001` | **Modular monolith** — no new microservices; Searcher extensions remain in-process. |
| `ADR 0009` | **Pluggable dispatcher** — Searcher behaviour must remain identical whether research runs **in-process** or via **HTTP/Cloud Function**; **identical structlog field semantics** across dispatch paths. Reddit/Trends must **not** fork orchestration into dispatcher-specific code paths. |
| Budget (product / pipeline economics) | **Per-experiment cost target under ~$1.50.** Multi-source adds **external calls and latency**; Tavily credit spend and LLM phases must stay within the same envelope — **no unbounded fan-out**. |

---

## 3. Source Taxonomy

| Source | What it contributes | Idea types that benefit most | Status |
|--------|---------------------|------------------------------|--------|
| **Tavily** | **General web / professional corpus** — articles, docs, landing pages, press, blogs with crawl-friendly text. | **B2B SaaS**, devtools with public docs, categories with active trade press, **marketplace** ideas with existing coverage. | v1 |
| **Reddit (PRAW)** | **Community pain-point signal** — authentic complaints, comparisons, "what do you use?" threads, niche vocabulary. | **Consumer apps**, **hobby / passion** products, **localized** or **subculture** ideas, **early-stage** products where **users** lead the narrative. | v2 deferred |
| **Google Trends (pytrends)** | **Time-series demand validation** — relative interest over time, seasonality, breakout vs decline. **Not** extractable prose evidence. | **Consumer trends**, **seasonal** or **fad-driven** ideas, **geographic** interest checks, **"rising topic?"** validation alongside text evidence. | v1 |

**Why two sources for v1 (not one, not four).** Tavily stays the **breadth** layer; Trends adds **temporal demand** no text snippet replaces. **Community-signal** coverage (Reddit) is **v2**, contingent on commercial Reddit Data API approval — see v3 update. **Explicitly out of scope for MVP** per `.cursorrules`: **Exa**, **Firecrawl**, **Anthropic web search tool**, and **news API** as additional first-class integrations — this plan **does not** add them to v1; v1 scope stays **Tavily + Trends** without **source sprawl**.

---

## 4. Input Contract — What Each Source Receives

**Shared base input (all sources):**

- The **research question text** for the question being served (from `ResearchPlan.questions[]`).
- **`search_queries`** from `ResearchQuestion.search_queries` — today **1–3 strings per question**, each **Tavily-ready** in the Planner sense (`.cursorrules`/`planner.py`: short web-style queries, **no** `site:` operators in v1 planner output).

**Per-source query adaptation (Searcher's job for v1):**

| Source | Adaptation |
|--------|------------|
| **Tavily** | Use `search_queries` **as-is** (current behaviour). |
| **Google Trends** | Build a **1–5 keyword bag** from the **question text + search_queries** (dedupe, flatten to short keyword phrases). Trends **does not** accept seven independent full-sentence questions as seven full Trends API sessions within budget — see §7. |

**Open question (flagged for v1 recommendation):** Should `ResearchPlan` grow **per-source query fields** (e.g. `reddit_queries`, `trends_keywords`)? **Recommendation for v1:** **No** — keep a **single Planner output shape**; **Searcher owns adaptation** from `question` + `search_queries`. **Revisit** if calibration shows **Planner-authored per-source queries** materially outperform heuristic adaptation.

---

## 5. Output Contract — How Multi-Source Results Merge

**Current shape (Tavily-only):** `dict[str, list[TavilyResult]]` keyed by **`question_id`**.

**Proposed shape (multi-source):** For each `question_id`, a **merged bundle** (conceptually):

```
MergedSearchResults:
  tavily:  list[TavilyResult]
  trends:  TrendsSeries | None  — or null per §7 keying choice; Trends is NOT per-question in this object when keyed pipeline-level; see §7
```

**Clarification:** **Trends** is attached **once per pipeline run** (or keyed separately — see §7), **not** duplicated inside every question's `MergedSearchResults` if the series is **global**. The per-question dict may expose **`trends: None`** always, with Trends carried on orchestrator state / Synthesizer input — **exact wiring is an implementation detail** bounded by §7 and §10.

**Why not a single flat `list` of polymorphic `SearchResult` for Reader?**

- **Trends** is **not evidence text** — it must **not** pass through Reader as "snippets."

**Alternative considered:** A **Pydantic discriminated union** of result types (`kind: "tavily" | …`). **Recommendation for v1:** **Per-source keyed structure** (`tavily`, `trends`, …) so orchestration code keeps **explicit branches** — **no hidden polymorphism** that obscures per-source handling and validation. (When Reddit lands in v2, Reader will need **different extraction rules** for **static web text** vs **Reddit discourse** — see §6.)

---

## 6. Reddit Integration Detail

**Deferred from v1 implementation per v3 update.** This section is retained for v2 reference if commercial Reddit Data API approval is later obtained. The v1 multi-source implementation skips Reddit entirely.

**Library:** **PRAW** (Python Reddit API Wrapper). **Reasons:** mature, **free-tier compatible**, synchronous client with a well-understood **async bridge** pattern (same family as Tavily's `asyncio.to_thread` in `tavily.py`).

**Alternative:** `asyncpraw` — **note for v1:** defer to limit **dependency and behaviour surface**; **PRAW + `asyncio.to_thread()`** (or equivalent) matches existing integration style and keeps **one clear pattern** across wrappers.

**Auth model:** OAuth **script-type** app (read-only use). Secrets: **`REDDIT_CLIENT_ID`**, **`REDDIT_CLIENT_SECRET`**, **`REDDIT_USER_AGENT`** — **Secret Manager** in production, **`.env`** in local dev (`AGENTS.md` secrets discipline).

**Rate limits:** **60 requests/minute** free-tier class constraint in `.cursorrules`. Wrapper must enforce **circuit breaker + retry** per integration norms; **graceful skip** on sustained failure (`.cursorrules` degradation text).

**Query strategy (v1 intent):** Use **`search.subreddit("all", query=...)`** (or equivalent **global search**) for **broad pain-point discovery**. **Top N** results per query (N calibration-pending), **sort** combining **relevance and score** (exact ranking left to implementation + eval).

**Data shape (conceptual) — `RedditResult`:**

| Field | Role |
|-------|------|
| `url` | Permalink — participates in Reader URL allow-list with Tavily URLs |
| `title` | Post title |
| `selftext_excerpt` | Truncated body text, **max ~500 chars** — bounds payload and prompt size |
| `score` | Post score |
| `num_comments` | Engagement proxy |
| `subreddit_name` | Subreddit (metadata, not logged as full post body) |
| `created_utc` | Time context |

**SECURITY (load-bearing):** Reddit is **unstructured UGC** and the **highest prompt-injection risk surface** in the pipeline after Tavily. Reader prompts must wrap Reddit bodies in **clearly labelled** tags (e.g. **`<untrusted_reddit_content>`**) with the same **"data, not instructions"** framing as `AGENTS.md` / Tavily. **This requirement is non-optional** and **pairs with** the planned **Reader prompt revision** (reader_v2 — not authored in this doc).

---

## 7. Google Trends Integration Detail

**Library:** **pytrends** (already listed in `.cursorrules` tech stack).

**Data shape (conceptual) — `TrendsSeries`:**

| Field | Role |
|-------|------|
| `keywords` | The keyword set used for this request |
| `geo` | Region code (default / calibration-pending) |
| `time_range` | Window for the series |
| `interest_over_time` | List of `{date, value}` points |
| `related_queries` | Optional list of related query strings |

**Semantic role:** **Numerical signal**, **not** extractable text evidence. **Reader does not** emit `ExtractedEvidence` **from** Trends rows. **Synthesizer** consumes `TrendsSeries` as a **separate signal channel** (§10).

**Reliability:** pytrends is **historically flaky**. **Circuit breaker + retry** (align with `.cursorrules`: **retry 3× then continue without; note in report**).

**Query budget:** **~3 Trends calls per pipeline run** (e.g. one per ~2 research questions, **batching** when keyword sets overlap to avoid redundant pulls). **Zero LLM cost**, but **latency budget** must be tracked alongside Tavily/Reddit wall-clock.

**Keying for downstream (feeds §10):** Prefer **`dict[str, TrendsSeries]`** keyed by **`question_id`** where each question (or question group) has **at most one** series — **or** a **small fixed set of keys** (e.g. **`q1`–`q7`** with nulls) so Synthesizer can align trends to narrative sections. **Global single series** is acceptable only if the run uses **one consolidated keyword bag** for the whole idea — **human review should pick** between **per-question** vs **one global "market demand"** key for v2.

---

## 8. Execution Model — How the Searcher Runs Multiple Sources

**Per question:** Run **Tavily only** — same fan-out as today's implementation (`asyncio.gather()` over `(question_id, search_query)` pairs). **No Reddit** in v1.

**Trends:** **Not** inner-looped per question in the same way — **batch / cap** at **~3 calls per run** (§7), executed **once or a few times per pipeline**, **not** N× per every `(question, query)` pair.

**Per-source failure isolation:** If Trends fails for the run, **Tavily results per question still return**. **No source is mandatory** for a question: if **all** sources fail for that question, the **question proceeds** with **empty evidence**; **Reader's existing gap / sentinel paths** apply.

**Concurrency / limits:**

- **Current Tavily implementation** (`searcher_service.py`): **no `asyncio.Semaphore`** — **all** `(question_id, search_query)` Tavily tasks launch in **one** `asyncio.gather()`. Parallel Tavily calls ≈ **total query count** (often ~14 for 7×2).
- **v1 multi-source impact:** With Reddit deferred, the **Tavily-only fan-out (~14 parallel calls for 7×2) stays unchanged** — the v2 doubling concern from adding Reddit **does not apply** in v1. **Semaphore decision:** **no change from current Searcher implementation for v1**; revisit when Reddit lands in v2.

**Mandatory vs optional:** **None** of Tavily / Trends is **hard-required** for the run to continue — only **orchestrator-level total failure policies** (e.g. all Tavily failed today → `SearcherFailure`) may remain; **multi-source** should **relax** toward **partial success** where consistent with `.cursorrules` **partial results** behaviour.

---

## 9. Reader Phase Impact

**v1 multi-source:** **Reader is unaffected.** Tavily-only evidence still flows through the existing Reader path; **no prompt revision** (`reader_v1_cached` stays as-is). Trends does **not** go to Reader (§7 — Synthesizer-only signal), so there is **no Trends-aware framing** required in Reader for v1.

**Trends:** **Does not** appear in Reader user prompts — **not text evidence**.

**Schema impact (v1):** **No new `ExtractedEvidence.source` field** — all text evidence remains Tavily-sourced. **URL hallucination guard** continues to validate **`source_url`** against **Tavily URLs** supplied for **that question** (unchanged).

**v2 note (when Reddit ships):** Reader will need a **prompt revision** with **structured sections** — **`tavily_results`** and **`reddit_results`**, **each XML-wrapped** per **`AGENTS.md`** (e.g. **`<untrusted_reddit_content>`**); **`ExtractedEvidence.source`** becomes **`Literal["tavily", "reddit"]`**; URL guard expands to **Tavily ∪ Reddit** — see §6.

**Execution:** **Per-question concurrent Reader model** (**ADR 0011**) **unchanged** — **one LLM call per question**.

---

## 10. Synthesizer Phase Impact

**Evidence path:** **ReaderOutput** remains the **evidence abstraction** for **text atoms**; Synthesizer stays **source-agnostic** at the **finding / claim** level when reading **`ExtractedEvidence`**.

**New channel — Trends:** **SynthesizerInput** gains a **fifth field:**

```
trends_signals: dict[str, TrendsSeries] | None
```

**Relationship to ADR 0012:** ADR 0012 locks **`SynthesizerInput`** at **four fields** (`refined_idea`, `research_plan`, `reader_outputs`, `rubric_version`). Adding **`trends_signals`** is a **deliberate, scoped extension** — **not** a casual contract drift. **ADR 0015** will record the **5-field contract** and **supersede** the **"four fields"** statement in ADR 0012 using the normal **"Superseded by ADR 0015"** pattern **without deleting** ADR 0012 history.

**Hydration / citations:** Reddit citations appear in the Synthesizer's final report alongside Tavily-backed citations. To avoid **bare URLs** and regression versus Tavily (where **`TavilyResult`** supplies title-class metadata today), Reddit citations need **at minimum** the **permalink URL**, **post title**, and **subreddit display name** when rendered. Extend the orchestrator's **`citation_hydration_index`** from **`dict[str, TavilyHydrationEntry]`** (Tavily-only today) to a **source-aware** structure: **either** **(a)** a **single dict keyed by URL** whose **`CitationHydrationEntry`** carries a **`source: Literal["tavily", "reddit"]`** discriminator plus **nullable Reddit-specific fields**, **or** **(b)** **per-source hydration indices** merged when building Synthesizer input. **Recommendation for v1: (a)** — **one lookup site** in **`synthesizer_service.py`**, **no per-source merge logic**, and ADR **0012**'s **`CitationHydrationEntry`** pattern stays **single-typed** across URLs. Per ADR **0012**, **hydration data never enters the Synthesizer LLM prompt**; it is **metadata only**, used to **enrich citation rendering after** the model produces text.

**Keying note:** **`trends_signals`** keyed by **`question_id`** (or agreed global key — §7) keeps alignment with **`reader_outputs`**; final key choice is a **v2 review** item if partial.

---

## 11. Files to Create / Modify

| File | Action | Notes |
|------|--------|--------|
| `backend/app/integrations/trends.py` | **New** | pytrends wrapper: same reliability + cost / latency logging pattern as `tavily.py` |
| `backend/app/services/searcher_service.py` | **Modify** | Multi-source orchestration, **`MergedSearchResults`** (`tavily` + `trends` keys), partial failure semantics |
| `backend/app/schemas/searcher.py` (or adjacent module name TBD) | **New** | Conceptual **`MergedSearchResults`**, **`TrendsSeries`** — **exact module split** decided at implementation |
| `backend/app/services/research_engine_service.py` | **Modify** | Pass merged Searcher output to Reader; attach **Trends** to Synthesizer path / state |
| `backend/app/schemas/synthesizer_input.py` (or equivalent) | **Modify** | **`trends_signals`** fifth field |
| `backend/app/services/synthesizer_service.py` / `synthesizer_input.py` | **Modify** | Thread Trends into prompt building **without** treating it as **`ExtractedEvidence`** |
| `backend/app/llm/prompts/synthesizer.py` | **Modify** | **`synthesizer_v3`** (or next) when Trends-aware prompt ships — **prompt text not in this doc** |
| `docs/adr/0014-multi-source-search-inputs.md` | **New** | Stub → full ADR |
| `docs/adr/0015-synthesizer-input-contract-v2.md` | **New** | Stub → full ADR; supersedes ADR 0012 **field-count** language only |
| `docs/llm-schema-calibration.md` | **Modify** | Caps for Trends payloads |
| `docs/cost-ledger.md` (if present) | **Modify** | Trends line items |

---

## 12. ADR Stubs Required

### ADR 0014 — Multi-Source Search Inputs

| Section | Sketch |
|---------|--------|
| **Context** | Tavily-only Searcher under-serves consumer/community/time-series ideas; ADR 0004 and Build Order already name Reddit + Trends. |
| **Decision** | **v1 = two sources** (Tavily, Trends); **per-source-keyed merged output**; **Searcher-owned query adaptation** from Planner strings; **Reddit deferred to v2** pending commercial Data API approval. |
| **Reasoning summary** | Quality lever for full idea distribution; avoids polymorphic soup; keeps Planner schema stable for v1. |

### ADR 0015 — Synthesizer Input Contract v2 (5-field; `trends_signals`)

| Section | Sketch |
|---------|--------|
| **Context** | ADR 0012 locks a 4-field `SynthesizerInput`; Trends is **non-text** and must not be forced through Reader. |
| **Decision** | Add **`trends_signals`** as field five; **ADR 0012** annotated **superseded in respect of field count** by **ADR 0015** (ADR 0012 file **retained**). |
| **Reasoning summary** | Preserves Reader–Synthesizer separation; makes demand signal explicit and testable. |

**Full ADRs** are written **outside** this planning document.

---

## 13. Calibration Obligations

Per **`docs/llm-schema-calibration.md`:**

- **Length caps** on new fields (**`TrendsSeries`** serialised size, related query lists): treat as **initial estimates**; log lengths at runtime; after data, set caps to **observed max + 10–15%**.
- **First 5-idea calibration session** after multi-source ships: measure **Reflector `mono_domain` trigger rate** (or equivalent rule from ADR 0013 / implementation) — **expected to drop modestly** with Trends adding cross-domain queries; **full mono_domain reduction requires v2 Reddit**.
- **Cost ledger:** First multi-source run **records** **Trends** as a **distinct external cost/latency line** (Tavily already tracked).
- **Pipeline budget check:** Confirm **end-to-end run** stays **under ~$1.50** with typical query counts.

---

## 14. What This Document Does NOT Cover

- **Implementation commits and sequencing** — a separate implementation plan will order PRs and migrations.
- **Reddit integration** — deferred to v2 pending commercial Data API approval; see v3 update header and §6 deferral note.
- **Full Reader prompt text** for **reader_v2** (Reddit-era) — authored when Reddit ships in v2.
- **Full Synthesizer prompt text** for **Trends-aware** synthesis — authored when **synthesizer_v3** (or next) is drafted.
- **News API integration** — **out of scope for MVP** per `.cursorrules`.
- **Exa / Firecrawl** — **out of scope for MVP** per `.cursorrules`.
- **Executable code, schemas, and tests** — **planning only**; no module bodies or Pydantic class definitions are fixed here.

---

## 15. Decisions and Rationale

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Merged output shape** | **Per-source keys** (`tavily`, `trends`, …) vs **flat discriminated union** | **Explicit orchestration branches**; **Trends** stays out of Reader entirely — polymorphic lists **hide** source-specific handling. |
| **Trends consumer** | **Synthesizer signal** vs **Reader input** | Trends is **numeric**, not quotable evidence; **Reader stays text-extraction**; avoids false **`ExtractedEvidence`** rows. |
| **Reader prompts (v1)** | **No change** | Tavily-only Reader path unchanged; Trends bypasses Reader (§7, §9). |
| **Source count v1** | **Two** (**Tavily + Trends**); **Reddit deferred to v2** pending commercial Reddit Data API approval per Responsible Builder Policy | v1 ships without Reddit; community-signal gap addressed in v2 if approval obtained. |
| **Reddit deferral** | **Indefinitely defer**; **v2 contingent** on commercial Data API approval | Reddit's Responsible Builder Policy prohibits AI/commercial use of Reddit data without written approval; pursuing approval is a **separate effort** not blocking v1 multi-source. |

### Resolved questions

| Topic | Decision | Rationale |
|-------|----------|-----------|
| **Mono-domain rule (v1)** | **Mono-domain rule in v1 applies only to Tavily URLs**; revisit when Reddit lands in v2. | No Reddit domains in v1 evidence set. |
| **Schema brittleness** (pytrends drift) | **Strict internal DTOs** in **`backend/app/integrations/trends.py`**. Provider-shape mapping stays **inside the wrapper**. **`TrendsSeries`** is **Fivvle-owned**; **pytrends types never leak** past the integration boundary. | Same pattern as **`tavily.py`**. |
| **Partial-source observability** | Emit **`searcher_source_outcomes`** **once per pipeline run** via **`structlog`**: **per-source** success / failure / skip **counts** and **total latencies**. Per-question detail remains in **existing per-question debug logs**. **No content.** | Aligns with the **`planner_field_lengths`** instrumentation pattern **recently shipped**. |
| **Budget enforcement** | **Config-driven** via **`Settings`** (e.g. **`searcher_max_trends_calls_per_run`**). **Code constants are anti-calibration.** | Matches **`reader_concurrency_limit`** and **`reflector_max_refinement_waves`**. |

---

*Document status: **APPROVED — co-founder reviewed, Reddit deferred to v2, implementation prompt pending.** v3.*
