# ADR 0022 — Landing Page Generator Pipeline

**Status:** Proposed  
**Date:** 2026-06  
**Supersedes:** none (upon acceptance, updates the "ONE LLM call" contract in `ARCHITECTURE.md` § Landing Page Architecture)  
**Related:** ADR 0004 (multi-step pipeline principle), ADR 0005 (designer-built templates), ADR 0009 (pluggable dispatcher), ADR 0012 (overloaded-prompt lesson), ADR 0018 (Kimi k2.6 migration), ADR 0021 (insight generator pattern)

## Context

B3 landing page generation sits immediately after the research pipeline completes. `ARCHITECTURE.md` §6 defines the state transitions `RESEARCH_READY → LANDING_GENERATING → LANDING_DRAFT`, triggered automatically when the research engine finishes (Sequence 8b: `CF->>API: Trigger landing page generation`). The founder then reviews, edits, and publishes from `LANDING_DRAFT`.

`ARCHITECTURE.md` § Landing Page Architecture currently specifies a **single LLM call** that returns `template_id`, `palette_id`, `font_pair_id`, `enabled_sections`, and copy for optional sections (features, FAQ, how-it-works), with hero/problem/solution/CTA sourced from refinement. `USER_FLOW.md` Stage 3 echoes this contract.

The frontend/design team delivered a working prototype under `reference/backend/app/modules/landing_page_generator/`. That prototype implements a **multi-stage pipeline**:

1. Parse unstructured markdown validation report
2. **8 parallel LLM extractors** (offer, problem, customer, positioning, monetization, GTM, brand, proof)
3. **1 LLM strategist** (section sequence, messaging angle, copy framework, CTA strategy)
4. **1 LLM copy generator** (per-section conversion copy)
5. **Python theme applicator** (fixed designer template configs — colors, fonts, layout order — no LLM)

Three structural facts distinguish Fivvle's production path from the prototype:

- **Input is already structured.** The research pipeline emits a typed `ValidationReport` (Pydantic model). The prototype's 8 extractors exist solely to normalize unstructured markdown into `LandingPageInputModel`. That extraction step is unnecessary — the data is already structured.
- **Theme is not generative.** `ThemeGenerator` in the prototype is a pure Python function that looks up fixed designer template configs from a `TEMPLATES` dict and assembles `page_json`. No LLM is involved. This aligns with ADR 0005 (designer-built templates, bounded customization).
- **Single-call overload is a known failure mode.** Packing interpretation, strategy, template selection, and full copy generation into one prompt repeats the anti-pattern that caused Synthesizer citation hallucinations (ADR 0012): asking one LLM call to perform extraction, reasoning, and generation simultaneously overloads the model and degrades structured-output reliability.

The landing page generator must fit within the per-experiment cost budget ($1.50 target, `.cursorrules` Cost Tracking & Limits), log every LLM call to `LLMCall`, route through `client.py` only, and follow the pluggable dispatcher pattern established for research (ADR 0009) and insight (ADR 0021).

## Decision

Build the landing page generator as a **2-LLM-call + 1-Python-function pipeline**, adapted from the prototype but without the markdown parse/extract stages.

### Pipeline stages

**Stage 1 — Interpret + Strategize (1 LLM call)**

- **Input:** `ValidationReport` + `RefinedIdea` + `page_goal` (`waitlist` | `interest` | `contact`)
- **Output:** `LandingPageInputModel` (marketing intelligence derived from research) + `LandingPageStrategy` (section sequence, messaging angle, copy framework, CTA strategy)
- **Prompt:** `lp_strategist_v1` in `backend/app/llm/prompts/landing_page.py`
- **Phase:** `landing_page`
- **Provider/model:** per `Settings` (Kimi k2.6 per ADR 0018)
- **Logging:** `LLMCall` row with `prompt_name=lp_strategist_v1`, `phase=landing_page`

The strategist call replaces both the prototype's 8 parallel extractors and its separate strategist step. A single structured call maps the typed `ValidationReport` fields into `LandingPageInputModel` and simultaneously formulates conversion strategy. This is one cognitive task (understand the business → decide how to sell it), not two.

**Stage 2 — Generate Copy (1 LLM call)**

- **Input:** `LandingPageInputModel` + `LandingPageStrategy`
- **Output:** `CopyOutput` — per-section copy keyed by section type: `hero`, `problem`, `features`, `comparison`, `proof`, `objections`, `faq`, `pricing`, `cta`
- **Prompt:** `lp_copy_v1`
- **Phase:** `landing_page`
- **Logging:** `LLMCall` row with `prompt_name=lp_copy_v1`, `phase=landing_page`

Copy generation is a separate call so the model can focus exclusively on direct-response writing given a fixed strategy, mirroring the Reader → Synthesizer split in the research engine (ADR 0004, ADR 0012).

**Stage 3 — Apply Theme (Python function, no LLM)**

- **Input:** `strategy.section_sequence` + `copy_output` + `template_id`
- **Output:** `page_json` — template config, color palette, typography, ordered sections with populated content
- **Implementation:** pure function in `backend/app/services/landing_page_theme.py` (ported from prototype `ThemeGenerator`)
- **Templates:** 6 fixed designer templates with stable IDs:

  | ID | Name |
  |---|---|
  | `dark-premium` | Dark Premium |
  | `bold-v1` | Bold V1 |
  | `minimal-v3` | Minimal v3 |
  | `editorial-saas` | Editorial SaaS |
  | `aether` | Aether |
  | `abstract` | Abstract |

  Template selection is part of Stage 1 strategy output (`template_id` on `LandingPageStrategy`) or a founder override at publish time; Stage 3 applies the chosen template's fixed palette, typography, and section ordering.

### State machine

Matches `ARCHITECTURE.md` §6 with an explicit failure path:

```
RESEARCH_READY → LANDING_GENERATING   (auto-trigger on research completion)
LANDING_GENERATING → LANDING_DRAFT    (pipeline success)
LANDING_GENERATING → RESEARCH_READY   (pipeline failure — founder can retry via re-trigger)
```

On failure, the experiment remains research-complete; no partial `LandingPage` row is persisted. The founder sees research results and can retry landing page generation without re-running research.

`LANDING_DRAFT` self-loops for founder edits (copy changes, template swap) per existing state machine. Publish transitions to `LANDING_LIVE`.

### Dispatcher

Follows ADR 0009 and ADR 0021 patterns:

- **`LandingPageDispatcher` Protocol** — `dispatch(experiment_id: UUID) -> None`
- **`InProcessLandingPageDispatcher`** — `asyncio.create_task` background task inside FastAPI; default for local dev (`DISPATCHER_MODE=in_process`)
- **Factory** — `get_landing_page_dispatcher()` selects implementation from `Settings.dispatcher_mode`
- **`HttpLandingPageDispatcher`** — deferred. Factory `http` branch raises `NotImplementedError` until frontend integration justifies Cloud Function deploy and idle Cloud SQL cost (same deferral rationale as ADR 0021 Step 7)

Both dispatchers call the same `run_landing_page_generator(experiment_id)` entry point. The dispatcher handles trigger and status transitions only; the orchestrator runs the 3-stage pipeline.

Trigger surface: research engine completion (Sequence 8b handoff) sets `LANDING_GENERATING` and calls `dispatcher.dispatch(experiment_id)`. Endpoint-level re-trigger from `RESEARCH_READY` is allowed for retry after failure.

### Section-level regeneration

Supported via `CopyGenerator.regenerate_section()` pattern from the prototype:

- **Input:** `LandingPageInputModel` + `LandingPageStrategy` + current `copy_json` + `section_type`
- **Output:** merged `copy_json` with only the requested section updated
- **Cost:** 1 additional LLM call per regeneration (`prompt_name=lp_copy_regen_v1` or reuse `lp_copy_v1` with regen context)
- **Cap:** 5 regenerations per page per `.cursorrules` / `ARCHITECTURE.md` Cost Tracking (enforced server-side on `LandingPage.regeneration_count`)

After copy regen, Stage 3 re-runs (Python only) to rebuild `page_json` with updated section content. No LLM call for theme re-application.

### Cost

Estimated **$0.02–0.05 per full landing page generation** at Kimi k2.6 pricing (2 structured-output calls, moderate token counts). Section regenerations add ~$0.01–0.02 each. Well within the $1.50 per-experiment budget alongside research (~$0.50–0.80) and optional insight (~$0.02).

### Build components (implementation map)

Mirroring ADR 0021's numbered component list:

1. **Schemas** (`backend/app/schemas/landing_page.py`) — `LandingPageInputModel`, `LandingPageStrategy`, `CopyOutput`, `PageJson`. Pydantic `extra="forbid"`, `schema_version: Literal[1]`.
2. **Prompts** (`backend/app/llm/prompts/landing_page.py`) — `lp_strategist_v1`, `lp_copy_v1`. Zone A/B/C cache layout where applicable. Security notice for any embedded research content.
3. **VR mapper** (inside strategist service or prompt builder) — deterministic pre-processing of `ValidationReport` + `RefinedIdea` into prompt context; no separate LLM extractors.
4. **Orchestrator** (`backend/app/services/landing_page_service.py`) — runs Stage 1 → 2 → 3, persists `LandingPage` row (`copy_json`, `page_json`, `template_id`, `strategy_json`), transitions status.
5. **Theme applicator** (`backend/app/services/landing_page_theme.py`) — port of prototype `ThemeGenerator.theme_to_page_json()`; `TEMPLATES` dict is the single source of truth for palette/typography.
6. **Dispatcher** (`backend/app/dispatchers/landing_page.py`) — Protocol + in-process impl + factory.
7. **Trigger wiring** — research engine completion handler + optional `POST /experiments/{id}/generate-landing-page` retry endpoint (202 Accepted).

## Reasoning

### Why 2 LLM calls, not 1

The `ARCHITECTURE.md` "ONE LLM call" contract conflates three distinct cognitive tasks:

1. **Interpretation** — map research findings to marketing intelligence (who is the customer, what is the offer, what objections exist)
2. **Strategy** — decide section sequence, messaging angle, copy framework (PAS vs AIDA), CTA approach, template fit
3. **Copy generation** — write conversion copy for 6–9 sections with specific tone and framework constraints

ADR 0012 documented the cost of conflating extraction and synthesis in a single Synthesizer call: citation hallucination, rate-limit failures, and degraded structured-output reliability. The landing page generator faces the same risk if one call must interpret a full `ValidationReport`, formulate strategy, select a template, and write all section copy.

Splitting into **strategist (interpret + plan)** and **copy generator (execute plan)** gives each call a bounded, testable responsibility. Calibration can gate each prompt independently. Retries target the failing stage without re-running the other.

Stage 1 combines interpretation and strategy in one call (not two) because they share the same input context and produce a coherent plan — the prototype's strategist already consumed the full `LandingPageInputModel`. The anti-pattern is adding copy generation to that same call, not combining interpret + strategize.

### Why 2 LLM calls, not 11

The prototype runs 8 parallel extractors + 1 strategist + 1 copy generator = 10 LLM calls (11 if counting a separate template-selection call). That architecture exists because the prototype's input is **unstructured markdown** from a design-tool export. Each extractor normalizes one slice of the report into a typed sub-model.

Fivvle's input is a **`ValidationReport` Pydantic model** — claims, competitors, signals, recommendation, confidence labels, all typed and validated. The strategist prompt receives `ValidationReport.model_dump_json()` (optionally compressed, as insight does for Zone B) plus `RefinedIdea` and `page_goal`, and emits `LandingPageInputModel` as part of its structured output. No parallel extractors, no markdown parser, no `SectionRouter`.

Removing 8 LLM calls saves ~$0.15–0.30 per page and 30–60 seconds latency with no loss of input fidelity — the structured report is strictly richer than markdown sections routed to extractors.

### Why theme is Python, not LLM

ADR 0005 committed to designer-built parameterized templates. The prototype's `ThemeGenerator` demonstrates the correct implementation: a `TEMPLATES` dict with fixed `color_palette`, `typography`, and `visual_style` per template ID. `theme_to_page_json()` merges strategy-driven section order with copy content — deterministic, testable, zero token cost.

An LLM "theme generation" call would produce variable palettes and fonts, violating ADR 0005's bounded customization model, introducing accessibility/contrast risk, and costing tokens for output that a dict lookup provides exactly. The strategist may recommend a `template_id`; Python applies it.

### Why in-process dispatcher first

Same rationale as ADR 0009 and ADR 0021: local dev runs in one terminal, prompt iteration stays fast, tests avoid a second process. HTTP Cloud Function deploy deferred until frontend integration proves the idle-cost tradeoff is worth it.

## Consequences

**What becomes easier:**

- **Calibration per stage.** Strategist and copy prompts can be frozen, versioned, and evaluated independently (`lp_strategist_v1`, `lp_copy_v1`).
- **Predictable cost and latency.** 2 LLM calls + instant Python theme assembly; no 8-way parallel fan-out.
- **Prototype reuse.** `lp_strategist.py`, `copy_generator.py`, and `theme_generator.py` port directly; orchestrator simplifies (no markdown parse, no extractors).
- **Failure isolation.** Strategist failure does not waste a copy call; copy failure does not re-run strategist. Section regen targets one section.
- **ADR 0005 alignment.** Templates remain designer-controlled; AI fills copy within fixed layouts.

**What becomes harder:**

- **`ARCHITECTURE.md` drift until accepted.** The "ONE LLM call" text in § Landing Page Architecture and `USER_FLOW.md` Stage 3 must be updated when this ADR is accepted. Until then, this ADR documents the intended replacement.
- **Template ID reconciliation.** `ARCHITECTURE.md` lists 5 MVP templates (`minimal`, `vibrant`, `indie`, `premium-dark`, `editorial`); the prototype defines 6 (`dark-premium`, `bold-v1`, etc.). Implementation must map designer deliverables to the `TEMPLATES` dict IDs. Frontend `LandingPageProps` interface may need extension for prototype section types (`comparison`, `objections`, `pricing`) beyond the current optional sections.
- **Two prompts to maintain** instead of one — mitigated by ADR 0004's established multi-step discipline.
- **Two dispatcher implementations** (eventually) to keep behaviorally identical — mitigated by shared `run_landing_page_generator()` entry point.

**What we accept:**

- Landing page generation adds ~$0.02–0.05 to per-experiment cost beyond research — acceptable within $1.50 budget.
- `HttpLandingPageDispatcher` is not built for MVP; in-process mode carries the same mid-pipeline loss risk as research/insight if FastAPI restarts during generation.
- Strategist output (`LandingPageInputModel`) is LLM-derived from `ValidationReport` — not a mechanical field mapping. Prompt discipline and Pydantic validation are the guardrails; no separate extractor validation layer.
- Failure returns to `RESEARCH_READY` rather than a dedicated `LANDING_FAILED` state — keeps the state machine minimal; research results remain the primary artifact and retry does not require a new status enum value.

## Deferred (intentional)

- **HttpLandingPageDispatcher + Cloud Function deploy.** Deferred per ADR 0021 rationale; `DISPATCHER_MODE=http` raises `NotImplementedError`.
- **Prompt calibration / freeze.** `lp_strategist_v1` and `lp_copy_v1` require eval runs on the frozen research eval set before promotion to FROZEN status.
- **ARCHITECTURE.md §6 failure edge.** Add `LANDING_GENERATING → RESEARCH_READY` to the mermaid diagram on acceptance.
- **Template count alignment.** Reconcile 5-template `ARCHITECTURE.md` catalog with 6 prototype templates when designer handoff finalizes.

## Related

- ADR 0004 — Multi-step single-agent pipeline principle (applied to landing page generation)
- ADR 0005 — Designer-built templates; AI selects and populates, does not generate layouts
- ADR 0009 — Pluggable dispatcher (`in_process` / `http`)
- ADR 0012 — Overloaded single-prompt failure mode (Synthesizer lesson)
- ADR 0018 — Kimi k2.6 as default LLM provider
- ADR 0021 — Insight generator architecture (dispatcher deferral pattern, service component layout)
- `ARCHITECTURE.md` §6 (state machine), §8b (research completion triggers landing page generation)
- `.cursorrules` — Landing Page Template Implementation, 5 regeneration cap per page, $1.50 per-experiment budget
- `reference/backend/app/modules/landing_page_generator/` — prototype pipeline (adapt, do not copy verbatim)
