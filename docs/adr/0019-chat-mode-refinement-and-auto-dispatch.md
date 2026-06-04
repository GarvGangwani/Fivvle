# ADR 0019 — Chat-Mode Refinement & Auto-Dispatch

**Status:** Accepted
**Accepted:** 2026-06-04
**Date:** 2026-06-03
**Related:** ADR 0004 (research engine), ADR 0009 (dispatcher), ADR 0014 (prompt caching), ADR 0016 (synthesizer contract), ADR 0017 (quote guard), ADR 0018 (Kimi migration); planning doc `docs/planning/chat-mode-refinement.md`.

---

## Context

Refinement flow (USER_FLOW Stage 2; ARCHITECTURE.md Sequence 8a) is single-shot: `POST /experiments` runs one LLM call returning a complete `RefinedIdea`; the user clicks "Accept and continue"; `POST /experiments/{id}/confirm` transitions `REFINED → RESEARCHING` and dispatches via the ADR 0009 dispatcher. State-transition + dispatch logic is currently inlined in the `/confirm` route handler (audit confirmed at `backend/app/routers/experiments.py:171-230`).

`frontend-design-brief-v2.md` §2 replaces this with a chat-UI-native surface:
- Single Gemini-style chat handles both normal LLM conversation and Deep Research.
- Refinement is a 1–3 message exchange inside the chat, not a separate review screen.
- The "Deep Research" toggle is per-message intent; default ON.
- Pipeline auto-fires on refinement completion; no Accept button exists.
- ValidationReport renders in a side-panel canvas.

The backend has no concept of chat threads, multi-turn refinement, or auto-dispatch. The existing `/experiments` + `/refine` + `/confirm` surface does not express these requirements. The eval harness `backend/scripts/run_eval.py` bypasses HTTP entirely and seeds Experiments with pre-baked `refined_idea` (audit §12), so it is unaffected by this change.

## Decision

Introduce a chat-mode refinement surface per planning doc `docs/planning/chat-mode-refinement.md`:

1. **New endpoint `POST /chat/turn`** handles both `deep_research=true` (refinement) and `deep_research=false` (plain chat) in one surface.

2. **New data model:** tables `chat_threads`, `chat_messages`, `refinement_idempotency`. Two new columns on `experiments`: `thread_id` (UUID FK, nullable) and `dispatch_trigger` (enum: `user_confirm` | `auto_fire`, nullable). Existing `refinement_count` is reused as the per-experiment clarifying-turn counter.

3. **Refinement service reworked** to per-turn structured decision (`RefinementTurnDecision`: `decision ∈ {clarify, finalize}`, `assistant_message`, `clarifying_dimension`, optional `refined_idea`). The decision is the completeness signal; no external boolean gate. Anti-loop cap: 3 clarifying turns max, reset on `clarifying_dimension="pivot_resolution"`.

4. **New state transition `REFINING → RESEARCHING`** for the chat auto-fire path. The existing `REFINED → RESEARCHING` transition via `/confirm` is unchanged. The shared transition helper accepts:
   - source `REFINED` for both triggers,
   - source `REFINING` only when `trigger=auto_fire`,
   - source `RESEARCH_FAILED` only when `trigger=user_confirm` (preserves ADR 0009's re-dispatch path; auto-fire never silently retries failed runs).

5. **Extract `transition_to_researching_and_dispatch(experiment, trigger)` helper** from the currently-inlined `/confirm` logic. Both call sites (existing `/confirm` route and new chat service) share this helper. The `trigger` parameter is persisted on `Experiment.dispatch_trigger` for audit and observability.

6. **Coexistence:** `POST /experiments`, `POST /experiments/{id}/refine`, `POST /experiments/{id}/confirm`, `GET /experiments/{id}/research-status` remain unchanged for admin, eval, and any future non-chat callers. Chat-mode is founder-facing only.

7. **Plain chat** (`deep_research=false`) routes through `chat_service.reply()` with a scoped founder-context system prompt. It receives only `chat_messages` rows from the current thread; it does NOT receive ValidationReport content (prompt-injection avoidance per AGENTS.md). Cross-thread memory deferred to v2.

8. **Progressive rollout** via `AUTO_FIRE_CHAT_ENABLED` env var with five states: `off | shadow | cohort_10 | cohort_50 | on`. Production default `off`. Promotion criteria documented in planning doc §10 Step 7.

## Consequences

### Positive

- Frontend chat-UI integration unblocked; one stable contract for the frontend team to wire against (planning §7).
- Per-turn refinement with chat context enables sharper completeness judgment than single-shot. The LLM decides based on the actual conversation, not on schema-completeness heuristics.
- Shared `transition_to_researching_and_dispatch()` helper eliminates the existing duplicate-state-machine risk of having two dispatch call sites.
- Quality observability via `clarifying_dimension` distribution (planning §6.4) creates a post-launch feedback loop for the refinement archetype hypotheses, removing the need to block on founder interviews pre-launch.

### Negative

- New endpoint surface (`/chat/turn`) and three new tables (`chat_threads`, `chat_messages`, `refinement_idempotency`) to maintain.
- Per-turn refinement adds up to ~$0.006 per experiment worst case (modeled, planning §6.1) vs single-shot. Within `.cursorrules` $1.50 cap and AGENTS.md $4.50 ceiling.
- The chat refinement prompt is multi-turn and chat-context-aware — a new prompt to calibrate. New constant `refinement_v2_chat` lives alongside existing `refinement_v1` / `refinement_v1_retry`.
- ADR 0018 Kimi soft-judgment regression applies to the clarify/finalize decision (same class of judgment as the quote-fidelity regression that ADR documents). Mitigation: planning §4 calibration gate; `.env`-flip fallback to Sonnet for the refinement phase only (existing config-toggleable, no new mechanism).
- §1 refinement archetypes ship as author hypotheses, not founder-validated requirements (per Fivvle decision to skip pre-launch interviews). Post-launch quality observability is the validation loop.

### Neutral

- Existing `refine_idea()` service function, `/refine` and `/confirm` routes, and the `refinement_v1` prompt all remain in production for non-chat clients.
- ARCHITECTURE.md Sequence 8a gets a parallel diagram (8a-prime) for the chat path; the original diagram still correctly describes the non-chat path.
- `ValidationReport` schema is unchanged; chat completion message stays static ("Research is ready. → View report") with no `chat_summary` field added.

## Alternatives Considered

- **Extend `/refine` with an `auto_fire` boolean and a `complete` signal.** Rejected: frontend brief assumes a new surface with persistent thread state and multi-experiment-per-thread semantics; retrofitting the existing single-shot endpoint cannot express either. Discarded as the v1 DRAFT framing of this work (`refinement-auto-fire.md`, superseded).
- **Refinement service internally calls the dispatcher.** Rejected: couples two responsibilities; refinement becomes hard to unit-test in isolation. Single-responsibility layering (chat service orchestrates the transition based on refinement output) is cleaner.
- **Persistent `deep_research_intent` column on Experiment.** Rejected: frontend brief sends `deep_research` per-message; a persistent intent column would create a "auto-fire on turn 1 of a brand-new experiment from a prior session's toggle state" footgun.
- **No streaming in v1.** Accepted with explicit upgrade triggers (planning §11). Refinement-turn latency (~3–5s modeled, warm cache) is within standard chat-UI tolerance; streaming structured outputs through Instructor adds non-trivial plumbing.
- **No cancel-mid-research endpoint in v1.** Accepted. Frontend brief does not include cancel UI; auto-fire alone unblocks integration.
- **Add a `chat_summary` field to `ValidationReport` for the completion bubble.** Rejected for v1 (Fivvle decision); static "Research is ready." text ships. The canonical path if needed later is a synthesizer prompt bump (`synthesizer_v3_cached` → `synthesizer_v4_cached`) with the new field.

## Implementation

See `docs/planning/chat-mode-refinement.md` §10 for the ordered implementation steps and §13 for the AGENTS.md compliance mapping. Status moves from `Proposed` to `Accepted` after human review of v2 APPROVED planning doc.
