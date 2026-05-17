# Multi-Source Searcher — Planning Document

**Status:** DRAFT — pending human review  
**Phase:** Searcher (parallel multi-source evidence collection; extends ADR 0004 Searcher step)  
**Related ADRs to write:** ADR 0014 (Multi-Source Search Inputs); ADR 0015 (Synthesizer Input Contract v2 — 5-field contract with `trends_signals`)  
**Authors:** Cursor Composer (planning artifact); human co-founder (approval)

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

| Source | What it contributes | Idea types that benefit most |
|--------|---------------------|------------------------------|
| **Tavily** | **General web / professional corpus** — articles, docs, landing pages, press, blogs with crawl-friendly text. | **B2B SaaS**, devtools with public docs, categories with active trade press, **marketplace** ideas with existing coverage. |
| **Reddit (PRAW)** | **Community pain-point signal** — authentic complaints, comparisons, "what do you use?" threads, niche vocabulary. | **Consumer apps**, **hobby / passion** products, **localized** or **subculture** ideas, **early-stage** products where **users** lead the narrative. |
| **Google Trends (pytrends)** | **Time-series demand validation** — relative interest over time, seasonality, breakout vs decline. **Not** extractable prose evidence. | **Consumer trends**, **seasonal** or **fad-driven** ideas, **geographic** interest checks, **"rising topic?"** validation alongside text evidence. |

**Why three sources for v1 (not two, not four).** Tavily stays the **breadth** layer; Reddit adds **community truth** where the web is thin; Trends adds **temporal demand** no text snippet replaces. **Explicitly out of scope for MVP** per `.cursorrules`: **Exa**, **Firecrawl**, **Anthropic web search tool**, and **news API** as additional first-class integrations — this plan **does not** add them to v1; scope stays **Tavily + Reddit + Trends** aligned with the documented stack and Build Order, without **source sprawl**.

---

## 4. Input Contract — What Each Source Receives

**Shared base input (all sources):**

- The **research question text** for the question being served (from `ResearchPlan.questions[]`).
- **`search_queries`** from `ResearchQuestion.search_queries` — today **1–3 strings per question**, each **Tavily-ready** in the Planner sense (`.cursorrules`/`planner.py`: short web-style queries, **no** `site:` operators in v1 planner output).

**Per-source query adaptation (Searcher's job for v1):**

| Source | Adaptation |
|--------|------------|
| **Tavily** | Use `search_queries` **as-is** (current behaviour). |
| **Reddit** | Map the same strings to Reddit search: **broad discovery** via `search` across **`all`** (or configured default), optionally **lightweight query shaping** (strip site-specific cruft; **no** custom subreddit injection in v1 unless calibration shows systematic benefit). **Open design point:** subreddit hints could be a v2 Planner field — **not** required for v1. |
| **Google Trends** | Build a **1–5 keyword bag** from the **question text + search_queries** (dedupe, flatten to short keyword phrases). Trends **does not** accept seven independent full-sentence questions as seven full Trends API sessions within budget — see §7. |

**Open question (flagged for v1 recommendation):** Should `ResearchPlan` grow **per-source query fields** (e.g. `reddit_queries`, `trends_keywords`)? **Recommendation for v1:** **No** — keep a **single Planner output shape**; **Searcher owns adaptation** from `question` + `search_queries`. **Revisit** if calibration shows **Planner-authored per-source queries** materially outperform heuristic adaptation.

---

## 5. Output Contract — How Multi-Source Results Merge

**Current shape (Tavily-only):** `dict[str, list[TavilyResult]]` keyed by **`question_id`**.

**Proposed shape (multi-source):** For each `question_id`, a **merged bundle** (conceptually):

```
MergedSearchResults:
  tavily:  list[TavilyResult]
  reddit:  list[RedditResult]
  trends:  null  — Trends is NOT per-question in this object; see §7 for pipeline-level Trends
```

**Clarification:** **Trends** is attached **once per pipeline run** (or keyed separately — see §7), **not** duplicated inside every question's `MergedSearchResults` if the series is **global**. The per-question dict may expose **`trends: None`** always, with Trends carried on orchestrator state / Synthesizer input — **exact wiring is an implementation detail** bounded by §7 and §10.

**Why not a single flat `list` of polymorphic `SearchResult` for Reader?**

- **Reader** must apply **different extraction rules** to **static web text** vs **Reddit discourse** (tone, trust, citation style).
- **Trends** is **not evidence text** — it must **not** pass through Reader as "snippets."

**Alternative considered:** A **Pydantic discriminated union** of result types (`kind: "tavily" | "reddit" | …`). **Recommendation for v1:** **Per-source keyed structure** (`tavily`, `reddit`, …) so Reader and orchestration code keep **explicit branches** — **no hidden polymorphism** that obscures per-source prompt sections and validation.

---

## 6. Reddit Integration Detail

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

**Per question:** Run **Tavily** and **Reddit** **concurrently** via **`asyncio.gather()`** (same spirit as today's top-level Tavily fan-out: **maximize independence**, **isolate failures**).

**Trends:** **Not** inner-looped per question in the same way — **batch / cap** at **~3 calls per run** (§7), executed **once or a few times per pipeline**, **not** N× per every `(question, query)` pair.

**Per-source failure isolation:** If Reddit fails for **`q3`**, **Tavily results for `q3` still return**. The merged structure for `q3` has **`reddit: []`** (or omitted empty equivalent) and **Tavily populated** as available. **No source is mandatory** for a question: if **all** sources fail for that question, the **question proceeds** with **empty evidence**; **Reader's existing gap / sentinel paths** apply.

**Concurrency / limits:**

- **Current Tavily implementation** (`searcher_service.py`): **no `asyncio.Semaphore`** — **all** `(question_id, search_query)` Tavily tasks launch in **one** `asyncio.gather()`. Parallel Tavily calls ≈ **total query count** (often ~14 for 7×2).
- **Multi-source impact:** Adding Reddit introduces **another parallel fan-out** per question-query (conceptually **doubles or more** outbound network calls vs Tavily-only for the same plan). **v1 implementation must reassess:** whether to add a **semaphore** or **lower per-source parallelism** so **Reddit 60/min**, **Tavily rate limits**, and **process stability** remain safe. **This planning doc does not pick a number** — it records the **need** to reconcile fan-out with `.cursorrules` limits and **$1.50** run budget.

**Mandatory vs optional:** **None** of Tavily / Reddit / Trends is **hard-required** for the run to continue — only **orchestrator-level total failure policies** (e.g. all Tavily failed today → `SearcherFailure`) may remain; **multi-source** should **relax** toward **partial success** where consistent with `.cursorrules` **partial results** behaviour.

---

## 9. Reader Phase Impact

**Prompt evolution:** **Single Reader prompt revision** (e.g. **reader_v2**) that accepts **structured sections** — **`tavily_results`** and **`reddit_results`**, **each XML-wrapped** per **`AGENTS.md`**. **Do not** split into **separate Reader prompts per source** for v1 — **one model call per question** stays aligned with **ADR 0011**; the input merely gains **explicit sections**.

**Trends:** **Does not** appear in Reader user prompts — **not text evidence**.

**Schema impact (planning-level):** **`ExtractedEvidence`** gains a **`source`** field: **`Literal["tavily", "reddit"]`** (exact enum naming TBD at implementation). **URL hallucination guard** must validate **`source_url`** against the **union of Tavily URLs and Reddit URLs** supplied for **that question**.

**Execution:** **Per-question concurrent Reader model** (**ADR 0011**) **unchanged** — **one LLM call per question**, richer input.

---

## 10. Synthesizer Phase Impact

**Evidence path:** **ReaderOutput** remains the **evidence abstraction** for **text atoms**; Synthesizer stays **source-agnostic** at the **finding / claim** level when reading **`ExtractedEvidence`**.

**New channel — Trends:** **SynthesizerInput** gains a **fifth field:**

```
trends_signals: dict[str, TrendsSeries] | None
```

**Relationship to ADR 0012:** ADR 0012 locks **`SynthesizerInput`** at **four fields** (`refined_idea`, `research_plan`, `reader_outputs`, `rubric_version`). Adding **`trends_signals`** is a **deliberate, scoped extension** — **not** a casual contract drift. **ADR 0015** will record the **5-field contract** and **supersede** the **"four fields"** statement in ADR 0012 using the normal **"Superseded by ADR 0015"** pattern **without deleting** ADR 0012 history.

**Hydration / citations:** **`citation_hydration_index`** (Tavily URL metadata) **remains** for Tavily-originated URLs; **Reddit URLs** need **consistent hydration rules** (title / domain from merged search results) — **implementation detail** for the orchestrator, **out of scope** for this planning text beyond **acknowledging the join**.

**Keying note:** **`trends_signals`** keyed by **`question_id`** (or agreed global key — §7) keeps alignment with **`reader_outputs`**; final key choice is a **v2 review** item if partial.

---

## 11. Files to Create / Modify

| File | Action | Notes |
|------|--------|--------|
| `backend/app/integrations/reddit.py` | **New** | PRAW wrapper: `asyncio.to_thread`, circuit breaker, retry, `ExternalAPICall` logging, **no post/comment body in logs** |
| `backend/app/integrations/trends.py` | **New** | pytrends wrapper: same reliability + cost / latency logging pattern as `tavily.py` |
| `backend/app/services/searcher_service.py` | **Modify** | Multi-source orchestration, **`MergedSearchResults`**, partial failure semantics, concurrency review vs current gather-all |
| `backend/app/schemas/searcher.py` (or adjacent module name TBD) | **New** | Conceptual **`MergedSearchResults`**, **`RedditResult`**, **`TrendsSeries`** — **exact module split** decided at implementation |
| `backend/app/services/research_engine_service.py` | **Modify** | Pass merged Searcher output to Reader; attach **Trends** to Synthesizer path / state |
| `backend/app/services/reader_service.py` | **Modify** | Accept per-source sections; URL guard over **Tavily ∪ Reddit**; prompt name **reader_v2** when rewritten |
| `backend/app/llm/prompts/reader.py` | **Modify** | **XML sections** for Tavily vs Reddit; **PROMPT_NAME** bump |
| `backend/app/schemas/reader.py` | **Modify** | **`ExtractedEvidence.source`** — requires coordinated calibration entry |
| `backend/app/schemas/synthesizer_input.py` (or equivalent) | **Modify** | **`trends_signals`** fifth field |
| `backend/app/services/synthesizer_service.py` / `synthesizer_input.py` | **Modify** | Thread Trends into prompt building **without** treating it as **`ExtractedEvidence`** |
| `backend/app/llm/prompts/synthesizer.py` | **Modify** | **`synthesizer_v3`** (or next) when Trends-aware prompt ships — **prompt text not in this doc** |
| `docs/adr/0014-multi-source-search-inputs.md` | **New** | Stub → full ADR |
| `docs/adr/0015-synthesizer-input-contract-v2.md` | **New** | Stub → full ADR; supersedes ADR 0012 **field-count** language only |
| `docs/llm-schema-calibration.md` | **Modify** | Caps for Reddit excerpt, Trends payloads, new Reader fields |
| `docs/cost-ledger.md` (if present) | **Modify** | Reddit + Trends line items |

---

## 12. ADR Stubs Required

### ADR 0014 — Multi-Source Search Inputs

| Section | Sketch |
|---------|--------|
| **Context** | Tavily-only Searcher under-serves consumer/community/time-series ideas; ADR 0004 and Build Order already name Reddit + Trends. |
| **Decision** | **v1 = three sources** (Tavily, Reddit, Trends); **per-source-keyed merged output** per question; **Searcher-owned query adaptation** from Planner strings. |
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

- **Length caps** on new fields (**`RedditResult.selftext_excerpt`**, **`TrendsSeries`** serialised size, related query lists): treat as **initial estimates**; log lengths at runtime; after data, set caps to **observed max + 10–15%**.
- **First 5-idea calibration session** after multi-source ships: measure **Reflector `mono_domain` trigger rate** (or equivalent rule from ADR 0013 / implementation) — **expect meaningful drop** when **Reddit domains** diversify the URL set vs Tavily-only mono-site runs.
- **Cost ledger:** First multi-source run **records** **Reddit** and **Trends** as **distinct external cost/latency lines** (Tavily already tracked).
- **Pipeline budget check:** Confirm **end-to-end run** stays **under ~$1.50** with typical query counts.

---

## 14. What This Document Does NOT Cover

- **Implementation commits and sequencing** — a separate implementation plan will order PRs and migrations.
- **Full Reader prompt text** for **reader_v2** — authored when the prompt change is implemented.
- **Full Synthesizer prompt text** for **Trends-aware** synthesis — authored when **synthesizer_v3** (or next) is drafted.
- **News API integration** — **out of scope for MVP** per `.cursorrules`.
- **Exa / Firecrawl** — **out of scope for MVP** per `.cursorrules`.
- **Executable code, schemas, and tests** — **planning only**; no module bodies or Pydantic class definitions are fixed here.

---

## 15. Decisions and Rationale

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Merged output shape** | **Per-source keys** (`tavily`, `reddit`, …) vs **flat discriminated union** | **Explicit Reader branches** and prompts; **Trends** stays out of Reader entirely — polymorphic lists **hide** source-specific handling. |
| **Reddit library** | **PRAW** vs **async-praw** | **Smaller surface**, matches **thread-off** style used elsewhere; **async-praw** deferred until concurrency proof needs it. |
| **Trends consumer** | **Synthesizer signal** vs **Reader input** | Trends is **numeric**, not quotable evidence; **Reader stays text-extraction**; avoids false **`ExtractedEvidence`** rows. |
| **Reader prompts** | **Single** updated prompt vs **per-source** prompts | **Preserves ADR 0011** one-call-per-question model; **one place** to enforce **XML untrusted blocks**. |
| **Source count v1** | **Three** (**Tavily + Reddit + Trends**) | Matches **.cursorrules** stack and **ADR 0004** Searcher intent **without** MVP-out-of-scope **news/Exa/Firecrawl** sprawl. |

### Open questions for human v1 → v2 revision

1. **Reddit hallucination:** Is **URL-only** validation enough, or should **substring checks** on **quoted Reddit excerpts** mirror Tavily **quote guards** — given Reddit's **shorter, informal** text?

2. **Mono-domain rule after Reddit:** Should **Reflector** treat **Reddit vs Tavily domains** as **distinct corroboration**, or **down-weight** same-thread **URL variants** so **`mono_domain`** is not **silent**?

3. **Schema brittleness:** If **PRAW** or **pytrends** return shape drift in the wild, do we **version `RedditResult` / `TrendsSeries`**, or **isolate mappers** in integrations behind **strict internal DTOs**?

4. **Partial-source observability:** What **run-level structured log** (besides per-question counts) best surfaces **"Tavily OK / Reddit down / Trends skipped"** for **support triage** without logging **content**?

5. **Budget enforcement:** Should **hard caps** (e.g. **max Reddit calls per run**) be **config-driven** first-class settings, or **code constants** until calibration completes?

---

*Document status: **DRAFT — pending human review.** v1 prepared for co-founder revision to v2; **not** APPROVED.*
