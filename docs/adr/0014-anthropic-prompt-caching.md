# ADR 0014: Anthropic Prompt Caching for Research Engine Phases

**Status:** Accepted  
**Date:** 2026-05-18  

## Context

Per-run Anthropic spend is dominated by **Synthesizer** and **Reader** input tokens. The upcoming **multi-source Searcher** work will increase Reader payloads materially. [**ADR 0010**](0010-reader-output-schema.md)**–[**0013**](0013-reflector-decision-logic.md) establish Reader, Reflector, and Synthesizer contracts but **do not** specify **prompt caching**, cache **TTL**, or how **cached** input should appear in **`LLMCall`** and cost tooling.

Anthropic exposes **prompt caching** on the Messages API: breakpoints with `cache_control: {type: ephemeral, ttl}` discount **cache hits** (~10% of list input price for reads in our cost model) while **writes** carry **higher** per-token charges (1.25× for **5m** TTL, 2× for **1h** TTL on written portions — see `[docs/planning/prompt-caching.md](../planning/prompt-caching.md)` and provider docs).

Caching must respect **`.cursorrules`** (no model downgrade, full **LLMCall** logging, cost truth) and **AGENTS.md** (scraped/user content stays in **dynamic** segments after stable prefixes — **zones A/B/C** in the planning doc).

## Decision

Implement **Anthropic prompt caching plumbing** exclusively in **`backend/app/llm/client.py`** (extended `complete_structured()` with explicit **`cache_breakpoints`** and wire-format usage parsing). Use a **hybrid TTL strategy** where callers attach breakpoints: **`1h`** for **global/stable** prefixes (Zone A) and **`5m`** for **per-experiment stable** prefixes (Zone B), as described in the planning doc — **callers** choose TTL per breakpoint.

Extend **`LLMCall`** with **`cached_input_tokens`** (maps from API **`cache_read_input_tokens`**) and **`cache_creation_input_tokens`** (write volume from the API), while **`prompt_tokens`** remains **total** input for the call:

`prompt_tokens = input_tokens + cache_read_input_tokens + cache_creation_input_tokens`

(Anthropic’s **`input_tokens`** usage field is the **uncached tail** after the last cache breakpoint when caching is active; see provider documentation.)

**Legacy rows** keep **NULL** for the new columns; **aggregations** use **`COALESCE(column, 0)`** (see §15.1 in the planning doc). **No backfill** of historical rows.

## Reasoning

**Multi-source** Reader economics are **much safer** if shared stable prefixes stop being re-billed at full input rates on every fan-out call. Caching is **billing and plumbing** only: **no** change to model tier, output schemas, or trust boundaries if **Zone C** (dynamic / untrusted) content stays **after** the last experiment-stable breakpoint.

**Single wrapper** (`client.py`) preserves **ADR 0009** parity between in-process and HTTP dispatchers and **AGENTS.md** “all LLM calls through one module.”

**Explicit columns** (vs derive-only) support **audit**, **admin** cost views, and **circuit-breaker** truth as required by **`.cursorrules`**.

## Consequences

**Easier**

- Per-call and roll-up cost can reflect **cache read** discount and **write** multipliers using Anthropic **`usage`** (including **`cache_creation.ephemeral_5m_input_tokens`** / **`ephemeral_1h_input_tokens`** when present).
- Phase services can adopt caching incrementally by passing **`cache_breakpoints`** and splitting stable vs dynamic prompt segments (per planning doc) without new provider SDK call sites.

**Harder**

- Prompt assembly must respect **breakpoint order** and the **four-breakpoint** API limit; mistakes can cache **volatile** text or fragment discounts.
- **Write** costs can dominate **short** TTL windows or single-call phases — **`Refinement`**-style phases may skip caching (planning doc §15.1).

**Operational**

- `cost_ledger_audit.py` and future SQL aggregates **must** use **`COALESCE`** on new columns so **NULL** legacy rows behave as zero in **`SUM`**s.

## Related

- Planning: [`docs/planning/prompt-caching.md`](../planning/prompt-caching.md) (**APPROVED** v2)
- **ADR 0009** — pluggable research dispatcher (**identical behaviour** across transports)
- **ADR 0011** — Reader execution model (fan-out is the primary cache **read** amortization surface)
- **ADR 0012** — Synthesizer input contract (large stable prefix candidate)
