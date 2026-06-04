# Chat-Mode Refinement — Planning Document

**Status:** v1.1 DRAFT — codebase-audit-reconciled. Ready for Fivvle + Codex v2 APPROVED review.
**Phase:** Stage 2 (Refinement) trigger surface + service rework, gating frontend integration per `frontend-design-brief-v2.md` §2.
**Related ADRs (existing):** 0004, 0009, 0014, 0016, 0017, 0018.
**Related ADRs to write:** ADR 0019 — Chat-Mode Refinement & Auto-Dispatch.
**Supersedes:** v1 DRAFT of this doc + the earlier discarded `refinement-auto-fire.md`.
**Author:** Claude (architect); Fivvle (review); Codex (codebase verification, completed for v1.1).

---

## Changelog v1 → v1.1

- **§0 Pre-implementation blockers removed.** Codebase audit confirmed `ValidationReport` schema mostly matches `frontend-design-brief-v2.md` §4; Blocker A is a false alarm. Founder interviews skipped per Fivvle decision; archetypes treated as hypotheses validated post-launch via §6.4 (Blocker B).
- **Field names verified against ORM**: `research_error_detail`, `refinement_count`, `ExperimentStatus` enum values all confirmed.
- **§6.3 Sonnet fallback simplified**: `refinement_provider`/`refinement_model` already configurable via `.env` (config default is Sonnet; production runs Kimi via env override per ADR 0018). No new mechanism needed.
- **§7.5 plain chat scope confirmed in v1.** Frontend defaults Deep Research toggle to ON. Backend behavior unchanged.
- **§9 layering** updated to reflect that `/confirm` dispatch logic is currently inlined in the route handler, not extracted — Step 2 is a real new helper extraction.
- **§10 Step 3 calibration harness**: `run_eval.py` bypasses refinement entirely (creates Experiment rows with pre-baked `refined_idea`); refinement calibration needs a new harness, not an extension of the existing eval runner.
- **§12 Completion experience simplified**: no `chat_summary` field; static "Research is ready. → View report" message. Synthesizer prompt untouched.
- **§14**: O5 (plain chat) and O11 (`chat_summary`) resolved and removed.
- **New §0.1 Known-codebase-state**: surfaces stub HttpDispatcher and latent `synthesizer.py` constant inconsistency for Codex to track separately.

---

## 0.1 Known codebase state (informational; not blocking)

These came out of the audit. Surfaced for Codex / Fivvle awareness; this doc proceeds as if they exist.

1. **`HttpDispatcher` is a stub** (`backend/app/dispatchers/http.py`) — always raises `DispatchError`. Production chat-mode launch will need this implemented before deploying with `DISPATCHER_MODE=http`. Implementation is outside the scope of this doc; it's Cloud Function plumbing tracked separately.
2. **Latent inconsistency in `synthesizer.py`**: module-level `PROMPT_NAME = PROMPT_NAME_V2_CACHED` is dead — `synthesizer_service.py` overrides with `PROMPT_NAME_V3_CACHED`. Codex cleanup ticket; not blocking.
3. **`RefinedIdea` field caps have inline-comment vs code drift** (subheadline comment says 160 chars but `max_length=190`; risks comment says 200 but `max_length=250`). Cosmetic; not blocking.
4. **`/confirm` state-transition + dispatch logic is inlined** in `experiments.py` route handler. Step 2 of §10 extracts it.
5. **`run_eval.py` does NOT exercise the refinement service** — it seeds Experiments directly with pre-baked `refined_idea` from `tests.eval.ideas.EVAL_IDEAS`. The refinement-quality eval is a separate harness, not a flag on the pipeline runner.

---

## 1. What "good" looks like — five sample exchanges (hypothesis set)

Per Fivvle decision, v1 ships on this hypothesis set without pre-launch founder interviews. §6.4 quality observability validates archetypes against real founder behavior; archetypes are revised post-launch as data accumulates.

The refinement LLM decides per turn whether to clarify or finalize. **The decision is the completeness signal.** No external boolean gate.

### 1A — Vague idea

> **User:** "I want to build something for fitness people."
>
> **Assistant:** "What's the specific moment when one of these fitness people feels frustrated or stuck? Picture someone you know — what are they trying to do?"
>
> **User:** "I have a friend who does CrossFit. She's a coach. She spends 4 hours a week building workout programs for her clients in Excel and it's a mess."
>
> **Assistant:** "Got it — user is a CrossFit coach managing client programming; pain is the time + workflow. Before I research: just CrossFit coaches, or personal trainers broadly? And is the value 'faster to build' or 'better programs'?"
>
> **User:** "Just CrossFit coaches. Faster to build."
>
> **Assistant:** "Researching: a tool for CrossFit coaches that speeds up client program design — competing with Excel, Google Sheets, and existing coach tooling."
> **[Dispatch fires.]**

Design lessons: specific-person grounding unlocks 10× more useful answers than abstract "who's your target audience?"; two clarifying turns appropriate for genuinely vague ideas; finalization message states what's about to be researched *and what's excluded*.

### 1B — Overconfident specificity

> **User:** "I'm building an AI-powered Salesforce competitor for dentists in Toledo."
>
> **Assistant:** "Specific is good. Two things to nail down: (1) 'Salesforce competitor' is broad — patient management, marketing/CRM, operations, or all? (2) 'In Toledo' — beachhead, or is Toledo specifically different from dentists elsewhere?"
>
> **User:** "Patient management. Toledo is just where I'd start; my dad's a dentist there."
>
> **Assistant:** "Clear. Researching: a patient-management tool for small-practice dentists in the US; Toledo as beachhead, not market."
> **[Dispatch fires.]**

### 1C — Already-crisp idea

> **User:** "AI assistant for engineering managers that summarizes their team's PRs, Linear tickets, and Slack discussions into a weekly executive report. Target: EMs at 50–500-person eng orgs who spend 3+ hours every Friday writing status updates."
>
> **Assistant:** "Researching: an AI tool that aggregates GitHub, Linear, and Slack into weekly exec summaries for engineering managers at 50–500-person companies."
> **[Dispatch immediately. No clarifying turn.]**

### 1D — Internal contradiction

> **User:** "Free productivity app that competes with Notion, makes money from enterprise sales."
>
> **Assistant:** "That has a structural choice baked in: (a) free tier as top-of-funnel for enterprise upgrades — what Notion itself does — or (b) free forever for individuals, enterprise as a separate product? Those research differently."
>
> **User:** "Like Notion does. PLG into enterprise."
>
> **Assistant:** "Researching: a Notion-class productivity tool with PLG-to-enterprise motion. The comparable to study is Notion's own GTM history."
> **[Dispatch fires.]**

### 1E — Mid-stream pivot

> **User:** "AI tutor for high schoolers studying for the SAT."
>
> **Assistant:** "What's the gap with Khan Academy, Magoosh, the big test-prep companies? Cost, personalization, content quality, something else?"
>
> **User:** "Actually, never mind SAT — AP Bio specifically. My sister is taking it and the materials suck."
>
> **Assistant:** "Got it, pivoting. New scope: AI tutor for AP Biology, existing materials are weak. Quick check: just the student, or also parents/teachers buying it?"
>
> **User:** "Just the student."
>
> **Assistant:** "Researching: an AI tutor for AP Biology students, competing against existing AP prep."
> **[Dispatch fires.]**

### Cross-archetype invariants

Every assistant turn does exactly one of two things: ask a dimension-specific clarifying question, or finalize with "Researching: [reflected framing]". No filler. No "great question." Each turn carries information.

---

## 2. Per-turn LLM contract

**Per-turn input:**
- System prompt (§3, stable, cacheable per ADR 0014)
- Full refinement chat history (oldest → newest)
- Clarifying-turn counter (orchestrator-injected)

**Per-turn structured output** (Pydantic v2 via Instructor; ADR 0018 Kimi constraints respected):

```python
class RefinementTurnDecision(BaseModel):
    decision: Literal["clarify", "finalize"]
    assistant_message: str = Field(max_length=600)
    clarifying_dimension: Literal[
        "audience", "problem", "solution",
        "scope", "contradiction", "pivot_resolution", "other",
    ] | None = None
    refined_idea: RefinedIdea | None = None  # uses existing schema, audit-verified
    reasoning_trace: str = Field(max_length=400)  # internal, never user-facing
```

The `RefinedIdea` reference is the **existing schema** verified by audit: `refined_one_liner`, `target_audience`, `value_proposition`, `risks` (list of 3-5), `headline`, `subheadline`, `cta_text`. No schema changes proposed.

**Post-parse validation guards:**

- `decision="clarify"` ⇒ `clarifying_dimension` non-null, `refined_idea` null, `assistant_message` ends with `?`.
- `decision="finalize"` ⇒ `refined_idea` non-null, `clarifying_dimension` null, `assistant_message` starts with `"Researching:"` (case-insensitive).
- `assistant_message` does not contain banned filler phrases: `"great question"`, `"let me think"`, `"i'd love to help"`. Conservative list; expand only on calibration evidence.
- `reasoning_trace` dropped before serialization to chat; persists on `LLMCall` row for admin review.

**Anti-loop cap (orchestrator-enforced):**

- After 3 clarifying turns in this experiment, the next turn's user content includes: *"This is the fourth turn. Finalize on available signal; if information is genuinely missing, finalize with `research_limitations` noting the gap."*
- Counter resets when LLM emits `clarifying_dimension="pivot_resolution"`.
- Counter persists via existing `Experiment.refinement_count` column (audit confirms exists; reused — no new column).

---

## 3. Refinement prompt structure

Production sketch. Real prompt iteration in calibration per `procedure.md`.

### 3.1 System prompt (Zone A — stable, `ttl=1h`)

```
You are Fivvle's refinement assistant. Your job: take a founder's startup idea
from rough to researchable in at most three short turns, then hand off to the
research pipeline.

Per turn, you do exactly one of two things:

1. CLARIFY — ask ONE clarifying question (or a tightly-coupled pair) that
   targets a specific dimension: audience, problem, solution, scope,
   contradiction, pivot_resolution.

   Use specific-person and specific-moment grounding when the idea is abstract.
   ("Picture someone you know — what are they trying to do?" beats "who's
   your target audience?")

   Respect what's already specific. Don't re-ask what the user already said.

   Surface contradictions as the founder's choice between alternatives, not
   as flaws to fix.

2. FINALIZE — write a one-line "Researching: [reflected scope]" message that
   restates what's about to be researched in the founder's own framing, then
   emit the structured RefinedIdea with all required fields:
   refined_one_liner, target_audience, value_proposition, risks (3-5),
   headline, subheadline, cta_text.

   Finalize as soon as you have audience + value-prop + risks shape and no
   unresolved contradictions. Do not pad with clarifying questions when the
   idea is already clear.

   On pivot, reset scope. Acknowledge the pivot explicitly.

Never produce both. Never produce filler. Every turn carries information.

Hard ceiling: 3 clarifying turns. On turn 4, finalize on available signal.

Output is structured per the provided schema.
```

### 3.2 Per-turn user content (Zone C — dynamic, uncached)

```
<chat_history>
[user]: {message_1}
[assistant]: {message_1}
...
[user]: {latest_message}
</chat_history>

Clarifying turns used so far: {n}

Read the chat history. Decide: clarify or finalize. If n ≥ 3, finalize.
```

### 3.3 ADR 0014 cache breakpoint walkthrough

| Zone | Content | Breakpoint | TTL |
|---|---|---|---|
| A | System prompt (§3.1) — stable across all experiments, all users | After system prompt | 1h |
| B | Chat history when length > ~1000 tokens — stable within a refinement, grows monotonically | After chat history | 5m |
| C | Latest user message + turn counter | None (uncached tail) | — |

Two breakpoints; ≤ 4 API limit. Two budget remaining.

Moonshot caching not yet wired in `cost.py` per ADR 0018; breakpoint structure stays correct regardless.

### 3.4 Model + provider config

- Default per audit: `refinement_provider="anthropic"`, `refinement_model="claude-sonnet-4-6"`.
- Production override per ADR 0018: `refinement_provider="kimi"`, `refinement_model="kimi-k2.6"`.
- Both paths go through the existing `client.py` wrapper. Kimi adapter forces `temperature=0.6`, `thinking=disabled`. Sonnet path uses per-call temperature config.
- Prompt name: `refinement_v2_chat` (new constant in `backend/app/llm/prompts/refinement.py` alongside existing `refinement_v1` and `refinement_v1_retry`).

---

## 4. Quality criteria + eval

### 4.1 Per-archetype pass criteria

| Archetype | Turn 1 | Subsequent | Finalization |
|---|---|---|---|
| 1A vague | `clarify`, dimension ∈ {`problem`, `audience`}, uses specific-person grounding | Each turn targets a new dimension | Names scope AND excludes |
| 1B overconfident | `clarify`, dimension ∈ {`scope`, `contradiction`}, no re-asking | ≤ 1 clarifying turn | Distinguishes beachhead from market |
| 1C crisp | `finalize` on turn 1 | n/a | Reflects founder framing verbatim where possible |
| 1D contradiction | `clarify`, dimension = `contradiction`, framed as alternatives | ≤ 1 turn after resolution | Picks resolved option |
| 1E pivot | Post-pivot turn emits `pivot_resolution`, counter resets | Post-pivot turns target new direction | Scope matches post-pivot direction |

### 4.2 Cross-archetype hard rules

- **Sharpness:** `assistant_message` ≤ 400 chars on calibration set (schema cap 600 for slack).
- **No filler:** banned-phrase list (§2) zero hits.
- **Anti-loop:** zero exchanges exceed 3 clarifying turns. Forced-finalize on turn 4 produces `RefinedIdea` with non-empty `research_limitations` reference in `value_proposition` or similar appropriate field. (Existing `RefinedIdea` has no `research_limitations` field — that's on `ValidationReport`. Mitigation: forced-finalize includes a flag in the assistant message text like "research will need to fill in [gap]." Calibration to confirm phrasing.)
- **Schema integrity:** zero `RefinementTurnDecision` validation errors after first calibration pass. If miss rate > 5%, re-calibrate caps per `procedure.md`.

### 4.3 Cost criteria

- Per-turn refinement p90 cost ≤ $0.005 on Kimi (derivation §6).
- Cumulative refinement p90 ≤ $0.015 per experiment.
- Total per-experiment p90 (refinement + pipeline) ≤ $0.75 (current pipeline P90 is $0.71 per ADR 0018).

### 4.4 Quality criteria beyond schema/cost

Human reviewer scores each archetype's run on a 1–5 scale on three axes:

| Axis | What it measures |
|---|---|
| **Insight** | Did the clarifying question (or finalization) name something the founder hadn't articulated but recognized as true? |
| **Sharpness** | Was the question a single targeted strike, or generic / list-y? |
| **Reflection accuracy** | On finalize, does the "Researching:" line accurately restate the founder's intent? |

Target: median ≥ 4 on all three axes across the eval set.

### 4.5 Eval set size

Ships at N=5 (the §1 archetypes). Founder interviews deferred per Fivvle decision; archetype expansion happens post-launch based on §6.4 quality signals. If 1A-1E pass §4.1 + §4.2 + §4.4 on calibration, ship. Real-founder failure modes (a sixth archetype) get added as they surface in production.

### 4.6 Calibration harness (new — not via `run_eval.py`)

Per audit: `run_eval.py` bypasses refinement entirely (seeds pre-baked `refined_idea`, calls pipeline directly). Refinement calibration needs its own harness.

**New file:** `backend/scripts/run_refinement_calibration.py`. Responsibilities:
- Loads N=5 archetype fixtures from `backend/tests/eval/refinement_archetypes.py` (new file; user-message scripts for each archetype, including multi-turn).
- Calls `refinement_service.run_turn()` repeatedly to walk each archetype's turn sequence.
- Records each turn's `RefinementTurnDecision`, latency, cost, and structured trace.
- Emits calibration report to `docs/calibration/runs/YYYY-MM-DD-refinement-chatmode.md` with pass/fail per §4.1 + §4.2 + §4.4.
- Writes audit rows under the existing eval user (`eval@fivvle.internal`).

No HTTP requests; calls services directly like `run_eval.py` does for the pipeline.

---

## 5. Failure-quality design

Engineer-facing errors translate to honest user-facing chat messages.

### 5.1 Translation table

| Engineer surface | User chat message | Retry affordance |
|---|---|---|
| `Tavily429`, `TavilyRateLimit` | "Search is busy right now. Try again in a couple of minutes?" | Retry → `/confirm` re-dispatch |
| `TavilyAllFailed` | "I couldn't get search results to back this up — usually transient. Retry?" | Retry |
| Planner LLM error / timeout | "I had trouble setting up the research questions. Let me try that again?" | Retry |
| `SynthesizerHallucinatedCitation` | "The research came back with sources I don't trust. Rather try again than show shaky." | Retry |
| `quote_hallucination_rate exceeded` (ADR 0017) | "Some evidence came through fuzzy — research went through but flagged a few quotes. View report?" | View only (READY state) |
| Cost ceiling $4.50 (AGENTS.md) | "This run hit our budget cap — something went sideways. We're looking. Try again?" | Retry + admin alert |
| Refinement LLM timeout | "Got tied up thinking — retry?" | Retry current turn |
| Refinement validation error | "Something didn't parse on my side. Try once more?" | Retry + Sentry capture |
| Unknown / catch-all | "Research didn't complete this time. Retry, or try a slightly different framing?" | Retry |

### 5.2 Implementation

- `app/services/error_translation.py`: pure function `engineer_error → UserFacingError(message: str, retry_action: Literal["retry_pipeline", "retry_refinement_turn", "none"])`.
- Translation table is data, not branching code — testable, A/B-able.
- Reads `Experiment.research_error_detail` (audit-confirmed name) when translating.
- Sentry capture stays in engineer-error layer. Translation is purely UX.

---

## 6. Cost model

Derivation from ADR 0018 Kimi pricing (uncached; Moonshot caching not yet in `cost.py`):

- Input: $0.95 / 1M tokens
- Output: $4.00 / 1M tokens

### 6.1 Refinement turn token estimates

System prompt (§3.1) ≈ 350 tokens. Per-turn user content grows with conversation:

| Turn | Input tokens | Output tokens | Cost (uncached) |
|---|---|---|---|
| 1 | ~500 (system + first message + counter) | ~250 (decision JSON) | **$0.0015** |
| 2 | ~900 (history grew by ~200) | ~250 | **$0.0019** |
| 3 | ~1300 | ~350 (finalize includes RefinedIdea) | **$0.0026** |
| **3-turn worst case** | | | **$0.0060** |

### 6.2 Per-experiment and per-thread totals

| Scenario | Refinement | Pipeline | Total |
|---|---|---|---|
| Crisp idea (1C, 1 turn) | $0.0015 | $0.59 mean / $0.71 P90 | **$0.59 / $0.71** |
| Vague idea (1A, 3 turns) | $0.0060 | $0.59 / $0.71 | **$0.60 / $0.72** |
| Pivot then research | $0.0040 | $0.59 / $0.71 | **$0.59 / $0.72** |
| Thread with 3 separate ideas | $0.012 | 3 × $0.71 = $2.13 | **$2.14 P90** |

All within `.cursorrules` $1.50 per-experiment target. Per-thread cumulative is observable (§6.4) but no hard cap for v1.

### 6.3 Sonnet fallback for refinement (simpler than v1 thought)

Audit confirms: `refinement_provider` and `refinement_model` are already configurable in `config.py`. ADR 0018 calibration ran with Kimi via `.env` override. If §4.4 quality scores fail on Kimi, refinement reverts to Sonnet via `.env`:

```env
refinement_provider=anthropic
refinement_model=claude-sonnet-4-6
```

No code change. No new mechanism. Cost delta on fallback: refinement turns ~3× cost (~$0.003 → ~$0.01 per turn); per-experiment worst case ~+$0.03. Stays within budget.

**Gate:** §4 calibration runs on Kimi first. If §4.4 medians fail, recalibrate on Sonnet. Ship whichever passes.

### 6.4 Quality observability (production signals beyond cost)

| Signal | Detects |
|---|---|
| Refinement turn-count distribution (histogram) | Spike in 3-turn = over-clarifying; spike in 1-turn = force-finalizing |
| User reply length to clarifying questions (median / p90 chars) | Long replies = question landed; short replies = annoying |
| "View report" click-through rate | Low CTR = report quality suspect |
| Canvas dwell time | Low dwell = report didn't justify the chat investment |
| Dispatch-to-completion latency | Drift = pipeline performance regression |
| `dispatch_trigger` ratio (`auto_fire` vs `user_confirm`) | Should be ~100% auto-fire for chat clients, ~100% user-confirm for admin/eval |
| Per-archetype implicit identification | Track `clarifying_dimension` distribution per first-turn; surfaces real founder archetype distribution that may diverge from §1 hypotheses |

All queries over existing tables + new fields in §8. No new tables.

The last signal is the explicit feedback loop on §1 archetypes per Fivvle decision (Q1=b): hypothesis-set ships, real-founder distribution observed in production.

---

## 7. Endpoint contract

Derived from §2 + §5 + `frontend-design-brief-v2.md` §4. Frontend integration depends on exact match.

### 7.1 `POST /chat/turn`

Authenticated. Handles `deep_research=true` (refinement) and `deep_research=false` (plain chat) in one surface.

**Request:**

```json
{
  "thread_id": "uuid | null",
  "experiment_id": "uuid | null",
  "message": "string (max 4000 chars; untrusted per AGENTS.md)",
  "deep_research": true,
  "idempotency_key": "client uuid (required when deep_research=true)"
}
```

Semantics:
- `thread_id=null` → backend creates new thread, returns id
- `experiment_id=null AND deep_research=true` → continues the most recent `REFINING` experiment in thread if updated within 30 minutes; else creates new
- `experiment_id` provided → must be owned, in thread, status `REFINING`; otherwise 409
- `idempotency_key` → deduplicates against `(thread_id, idempotency_key)` for 24h

**Response (200):**

```json
{
  "thread_id": "uuid",
  "message_id": "uuid",
  "experiment_id": "uuid | null",
  "assistant_message": "string",
  "turn_kind": "normal_chat | refinement_clarify | refinement_finalize",
  "clarifying_dimension": "audience | problem | solution | scope | contradiction | pivot_resolution | other | null",
  "pipeline_dispatched": "bool",
  "dispatched_at": "iso8601 | null",
  "experiment_status": "DRAFT | REFINING | RESEARCH_PLANNING | ... | RESEARCH_FAILED | null",
  "research_error_detail": "string | null"
}
```

**`research_error_detail`** — name verified against `Experiment` ORM column (audit §3).

**Errors:**

| Status | Cause |
|---|---|
| 401 | Missing/invalid Firebase token |
| 403 | Thread or experiment not owned |
| 409 | `experiment_id` provided but status invalid for refinement |
| 422 | Schema validation failure |
| 429 | Per-user rate limit (60/min auth per `.cursorrules`) |
| 500 | Internal — body includes `request_id`, no PII |

Synchronous return. Phase-level progress via existing `GET /experiments/{id}/research-status` polling.

### 7.2 Coexistence with existing endpoints

Unchanged, kept for admin / eval / future API consumers:
- `POST /experiments` — explicit create (returns `ExperimentResponse` per audit §11)
- `POST /experiments/{id}/refine` — single-shot legacy (returns `ExperimentResponse`)
- `POST /experiments/{id}/confirm` — explicit dispatch + `RESEARCH_FAILED` re-dispatch (ADR 0009; audit §9 confirms inlined logic)
- `GET /experiments/{id}/research-status` — phase polling (frontend brief §4)

`run_eval.py` continues bypassing HTTP entirely (audit §12): creates Experiment rows directly with pre-baked `refined_idea`, calls `run_research_engine_pipeline()` directly. Chat-mode addition does not change this.

### 7.3 Frontend toggle default behavior (per Fivvle decision)

- **Default state of Deep Research toggle: ON.** New chat sessions open with DR on, so casual first-time use defaults to "I want this researched."
- Frontend MUST display the toggle state clearly so users always know whether their next message will trigger research (cost-bearing) or plain chat (cheap).
- Backend behavior is identical regardless of default: the `deep_research` boolean rides each message; backend reads it per-turn.
- A toggle change in the middle of a refinement does not retroactively cancel the in-flight refinement experiment. If the user toggles DR off mid-clarification, the next message routes to plain chat; the in-flight `REFINING` experiment remains until the 30-minute window expires or the user explicitly abandons it (no-op for v1; admin observability picks up the abandoned-experiment rate).

---

## 7.5 Plain chat (`deep_research=false`)

Half the chat surface. Per Fivvle decision (Q2=a), in v1 scope.

### 7.5.1 Purpose

Founder asks general questions in the same chat where they validate ideas: clarifications about the product, startup-related questions, brainstorming. Scoped to founder context; not general-purpose ChatGPT.

### 7.5.2 System prompt sketch (Zone A, cacheable)

```
You are Fivvle's chat assistant. The user is a founder using Fivvle to
validate startup ideas. They may ask you general questions, work through
ideas conversationally, or ask about how Fivvle's research works.

You answer concisely. You do not perform research — that's what the "Deep
Research" toggle is for. If the user describes a startup idea in a way that
sounds like they want it researched, gently suggest: "Want me to run
research on that? Toggle Deep Research and send it again."

You do not have access to the user's prior validation reports. If they ask
about a specific report, suggest they open it from the canvas.

You are not a therapist, life coach, or general-purpose assistant. If the
conversation drifts off-topic, gently redirect.
```

### 7.5.3 Memory model

- Plain chat receives **only `chat_messages` rows from the current thread** where `role IN ('user', 'assistant')` AND `turn_kind IN ('normal_chat', 'refinement_clarify', 'refinement_finalize')`.
- Does **NOT** receive: prior `ValidationReport` content, system-generated dispatch/progress/completion messages, or content from other threads.
- Reason: ValidationReports contain Tavily-derived text. Feeding into plain-chat prompts re-introduces prompt injection (AGENTS.md). v1 sidesteps. v2 may route report content through `<scraped_content>` wrappers.

### 7.5.4 Cost / model

- Same `client.py` wrapper.
- Phase name `chat_normal` in cost ledger (distinct from `refinement`).
- Calibration before launch: 20 founder-shaped questions hand-written, scored for concision + non-overreach + correct redirect on idea-shaped inputs.

### 7.5.5 Out of scope for v1 plain chat

- Cross-thread memory
- Attachments (brief Screen B shows "+"; backend returns 400 for v1)
- Voice input (brief shows mic; out of v1 backend scope)

---

## 8. Data model

Three new tables, three new columns. All additive; single Alembic revision.

```sql
CREATE TABLE chat_threads (
  id          UUID PRIMARY KEY,
  user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  title       TEXT NULL,  -- template-derived: first 40 chars of first user message, sanitized
  created_at  TIMESTAMP NOT NULL DEFAULT NOW(),
  updated_at  TIMESTAMP NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_chat_threads_user_id ON chat_threads(user_id);

CREATE TABLE chat_messages (
  id                    UUID PRIMARY KEY,
  thread_id             UUID NOT NULL REFERENCES chat_threads(id) ON DELETE CASCADE,
  role                  chat_role_enum NOT NULL,
  content               TEXT NOT NULL,
  experiment_id         UUID NULL REFERENCES experiments(id) ON DELETE SET NULL,
  turn_kind             chat_turn_kind_enum NULL,
  clarifying_dimension  VARCHAR(40) NULL,
  created_at            TIMESTAMP NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_chat_messages_thread_id ON chat_messages(thread_id, created_at);
CREATE INDEX idx_chat_messages_experiment_id ON chat_messages(experiment_id);

CREATE TABLE refinement_idempotency (
  thread_id        UUID NOT NULL,
  idempotency_key  TEXT NOT NULL,
  response_payload JSONB NOT NULL,
  experiment_id    UUID NULL REFERENCES experiments(id) ON DELETE SET NULL,
  created_at       TIMESTAMP NOT NULL DEFAULT NOW(),
  PRIMARY KEY (thread_id, idempotency_key)
);
CREATE INDEX idx_refinement_idempotency_created_at ON refinement_idempotency(created_at);
-- TTL: daily cron deletes rows older than 24h
```

`chat_turn_kind_enum`: `'normal_chat'`, `'refinement_clarify'`, `'refinement_finalize'`, `'dispatch_announce'`, `'pipeline_progress'`, `'pipeline_complete'`, `'pipeline_failed'`.

**New columns on `experiments`:**

| Column | Type | Default | Purpose |
|---|---|---|---|
| `thread_id` | UUID NULL REFERENCES chat_threads(id) | null | Links experiment to chat thread. Null for non-chat (admin, eval — audit §12 confirms eval bypasses chat). |
| `dispatch_trigger` | ENUM('user_confirm','auto_fire') NULL | null | Audit field. |

`refinement_count` (audit §3) already exists on `experiments`. Reused as the per-experiment turn counter; no new column needed. The §2 anti-loop cap reads this.

`research_error_detail` (audit §3) already exists. No change.

Down migration is real and tested.

---

## 9. Architecture layering

```
HTTP:                 POST /chat/turn (thin router)
                              │
Chat service:         chat_service.handle_turn(payload, user)
                              │
        ┌─────────────────────┼──────────────────────┐
        │                     │                      │
Refinement service:   Plain-chat path:       Experiment lifecycle:
.run_turn(thread,     .reply(thread,         .create_or_continue(
 history,              history)               user, thread)
 latest_message)              │                      │
        │              LLM wrapper            State helper (NEW):
        │              (client.py)            transition_to_researching
        │                                     _and_dispatch(experiment,
        │                                     trigger="auto_fire")
        │                                              │
        │                                     Dispatcher (ADR 0009)
        │
   LLM wrapper (client.py)
```

**Decision:** refinement service produces a decision; chat service orchestrates based on it. Refinement service does NOT call dispatch directly. Single responsibility per layer.

**`transition_to_researching_and_dispatch()`** is a real new function. Per audit §9, the existing `/confirm` route inlines: status check → clear `research_error_detail` on RESEARCH_FAILED → set status RESEARCHING → flush + commit → call `dispatcher.dispatch()` → return `ConfirmResearchResponse`. The extraction is Step 2 of §10; both `/confirm` and chat service call the new helper. Trigger label (`user_confirm` | `auto_fire`) is the parameter that distinguishes call sites.

**State guards preserved exactly:** the audit confirms `_CONFIRM_ALLOWED_STATUSES = {REFINED, RESEARCH_FAILED}` for the inlined route. The extracted helper must accept REFINED for both triggers, and RESEARCH_FAILED only for `user_confirm` (re-dispatch via /confirm). Auto-fire from chat path enters from `REFINING → RESEARCHING` directly when the refinement service emits `finalize`; the helper accepts REFINING as a valid source state when `trigger=auto_fire`. Codify in the helper's first guard.

---

## 10. Implementation order

ADR 0019 first per `.cursorrules`. Each step is its own commit with `git diff --stat` + content greps + full pytest green before the next.

**Step 0 — Write ADR 0019.**
- Status: Proposed. Documents the trigger-surface reversal for the chat path, ChatSession introduction, per-turn refinement supersession, and the REFINING → RESEARCHING auto-fire transition.
- Status → Accepted only after human sign-off.

**Step 1 — Alembic migration + schema (§8).**
- Three new tables + two new columns on experiments (`thread_id`, `dispatch_trigger`). `refinement_count` and `research_error_detail` reused as-is.
- Up + down both tested; pytest green.

**Step 2 — Extract `transition_to_researching_and_dispatch()` helper.**
- Pure refactor from currently-inlined logic in `experiments.py:171-230` (audit §9).
- Existing `/confirm` tests pass unchanged after the route delegates to the helper.
- New unit tests: `user_confirm` from REFINED, `user_confirm` from RESEARCH_FAILED (re-dispatch), `auto_fire` from REFINING, invalid-state rejection. `auto_fire` from RESEARCH_FAILED rejected (chat-mode does not silently retry failed runs; user uses retry affordance which calls /confirm).

**Step 3 — Refinement service rework (the moat).**
- New `RefinementTurnDecision` schema (§2), prompt constant `refinement_v2_chat` in `app/llm/prompts/refinement.py` (§3), `refinement_service.run_turn()`.
- LLM call through `client.py` per ADR 0018 + 0014.
- **Calibration against §1 N=5 BEFORE merge** via the new harness `backend/scripts/run_refinement_calibration.py` (§4.6). Writes to `docs/calibration/runs/YYYY-MM-DD-refinement-chatmode.md`. Pass: §4.1, §4.2, §4.4 (median ≥ 4 on insight/sharpness/reflection accuracy), §4.3 (cost).
- **§6.3 fallback gate:** if §4.4 fails on current production model (Kimi per env), flip `.env` to Sonnet and re-run calibration. Whichever passes ships.
- Legacy `refine_idea()` and `/refine` endpoint untouched.

**Step 4 — Failure-message translation (§5).**
- `app/services/error_translation.py`. Reads `Experiment.research_error_detail` (audit-confirmed).
- Unit-tested against translation table.

**Step 5 — Chat service + endpoint (§7, §7.5).**
- `chat_service.handle_turn()` per §9 layering.
- `POST /chat/turn` route in new `backend/app/routers/chat.py`.
- Idempotency check against `refinement_idempotency`.
- Plain chat path with §7.5 system prompt + memory scope.
- Integration tests covering: new-thread DR turn, in-thread DR continuation, finalize+dispatch, dispatch failure rollback (status reverts from RESEARCHING to REFINED, `research_error_detail` populated), idempotency replay, plain-chat path, plain-chat redirect on idea-shaped input, error translation surfaced in response.

**Step 6 — Quality observability (§6.4).**
- New cost-ledger queries + signal queries on existing tables + new columns.
- Admin endpoint extensions.

**Step 7 — Progressive rollout.**
- `AUTO_FIRE_CHAT_ENABLED` env var: `off | shadow | cohort_10 | cohort_50 | on`.
  - `off`: `/chat/turn` returns 404.
  - `shadow`: endpoint accepts requests, runs refinement, **does NOT auto-dispatch**; logs what would have happened. Compare to control.
  - `cohort_10`: 10% of new chat-enabled experiments use auto-fire; rest see "Accept and continue" affordance backed by `/confirm`.
  - `cohort_50`: 50%.
  - `on`: 100%.
- Promote based on §6.4 quality signals + `dispatch_trigger` ratio + completion-rate parity.

**Step 8 — Documentation closeout.**
- `ARCHITECTURE.md` Sequence 8a-prime (chat trigger). Stale class diagram updated to match actual `ValidationReport` schema (audit §1).
- `USER_FLOW.md` Stage 2 updated to chat-UI-native model with toggle-default-ON note.
- ADR 0019 → Accepted (human action).

---

## 11. Streaming — explicit decision

**Decision: synchronous response in v1. SSE upgrade is v1.5, gated on observed latency complaints.**

Refinement turn modeled at ~3–5s end-to-end on Kimi (warm cache, ~250-token output). Frontend brief §4 explicitly accepts "frontend polls or subscribes" — polling is fine. SSE adds keep-alive, reconnection, partial-response handling on both sides; Instructor structured-output streaming is non-trivial.

**Trigger for SSE upgrade:**
- p50 refinement latency > 6s in production for 2 consecutive weeks, OR
- Founder feedback flags chat-turn latency as friction (via future feedback mechanism), OR
- Plain-chat path proves to need streaming (free-form text streams more naturally than structured refinement).

---

## 12. Completion experience

When pipeline reaches `RESEARCH_READY`, the polling endpoint returns the completed status. The frontend renders a new assistant message:

```
[assistant, turn_kind="pipeline_complete"]:
"Research is ready. → View report"
```

Static text. No LLM-generated summary in the bubble. Per Fivvle decision (Q3=b): synthesizer prompt unchanged; no new `chat_summary` field on `ValidationReport`. The "View report" affordance opens the canvas with the existing `ValidationReport` (audit §1 confirms all expected sections present).

If a future iteration wants a summary line in the chat bubble, the canonical place is to add a synthesizer-emitted `chat_summary` field — bumping prompt version from `synthesizer_v3_cached` to `synthesizer_v4_cached`. Deferred until founder UX data shows the static line is insufficient.

**Pipeline-failed equivalent:**

```
[assistant, turn_kind="pipeline_failed"]:
"{translated_error_message_from_§5.1}

→ Retry  → Try a different framing"
```

`Retry` calls `POST /experiments/{id}/confirm` (re-dispatch path; ADR 0009 invariant preserved).

---

## 13. Security mapping (AGENTS.md compliance)

| AGENTS.md rule | This doc's compliance |
|---|---|
| LLM outputs never become side effects | Refinement decision parses to Pydantic; orchestrator decides dispatch in code, not LLM (§9 layering) |
| Untrusted content XML-wrapped | `<chat_history>` wrapper in §3.2; plain chat scope (§7.5.3) prevents Tavily-derived report content from re-entering LLM prompts |
| Every authenticated endpoint verifies Firebase token | `POST /chat/turn` carries existing auth middleware (`Depends(get_current_user)`) |
| Every resource-ID endpoint verifies ownership | Thread + experiment ownership both checked (§7.1 error matrix) |
| Idempotency on external mutations | `refinement_idempotency` table; required for `deep_research=true` |
| Cost circuit breaker | $4.50 per-experiment hard limit (AGENTS.md) still applies; refinement adds ≤ $0.006 to that envelope |
| No user content in structlog | `chat_messages.content` in DB only; logs use `message_id` + truncated hash |
| LLM-generated content rendered as plain text | Frontend brief §2 implies canvas renders sanitized; `assistant_message` is plain text, no markdown rendering except where explicitly designed |
| `dangerouslySetInnerHTML` never used with LLM output | Frontend-side contract; this doc designs no HTML-embedding fields |

---

## 14. Open questions (v2 APPROVED resolution)

Down to seven after Q1/Q2/Q3 resolution.

| # | Question | Default |
|---|---|---|
| O1 | 30-min in-flight refinement continuation window — right TTL? | Yes for v1. Recalibrate after 50 real sessions. |
| O2 | Pivot resets turn counter, or accumulates? | Resets. Counter persists on existing `Experiment.refinement_count` column. |
| O3 | `clarifying_dimension` exposed to frontend? | Yes. Trivial leak; enables visual cues. |
| O4 | Banned-phrase list hard-coded or LLM-tunable? | Hard-coded v1. Expand only on calibration evidence. |
| O6 | Idempotency TTL 24h? | Yes. |
| O7 | `chat_threads.title` LLM-generated or template? | Template (first 40 chars sanitized). |
| O8 | Refinement turn cap 3, configurable? | No. Hard-code. |
| O9 | Per-thread cumulative cost hard cap? | No. Observability only (§6.4). |
| O10 | Attachments in v1? | No. Backend 400s with "coming soon." |
| O13 (new) | Should the frontend toggle-state default-ON apply per-session or per-user (sticky)? | Per-session for v1. Sticky preferences are a future feature. |

(O5 and O11 resolved per Fivvle decision; removed.)

---

## 15. Risks accepted

- **Kimi soft-judgment regression (ADR 0018) may affect refinement.** Mitigated by §4.4 quality gate and §6.3 Sonnet `.env`-flip fallback (already a configurable mechanism, no new code).
- **§1 archetypes are author hypotheses; not founder-validated** (per Fivvle decision Q1=b). Mitigated by §6.4 quality observability post-launch, especially `clarifying_dimension` distribution surfacing real archetype mix.
- **No streaming in v1.** Mitigated by §11 trigger conditions for SSE upgrade.
- **No cross-thread plain-chat memory.** Intentional. v2 work with proper untrusted-content discipline.
- **HttpDispatcher stub.** Production deployment requires real implementation before chat-mode goes live; tracked outside this doc.
- **Founder-feedback collection mechanism not designed in this doc.** v2 work item.

---

## 16. What remains beyond this doc's reach

Closed in v1.1 (was open in v1):
- ~~Codebase verification~~ — completed (audit).
- ~~Founder UX validation~~ — deferred per Q1=b; post-launch observability per §6.4.

Still open:
- **Real Kimi calibration** — §4 + §6.3 gate runs in Step 3. Establishes which model ships.
- **Plain-chat calibration** — §7.5.4. 20 hand-written questions, scored before launch.
- **Frontend integration testing** — frontend team builds against §7 contract; staging-environment shadow-mode session (Step 7 `shadow`) to verify wire compatibility.
- **HttpDispatcher implementation** — prerequisite for production deployment of chat-mode if/when `DISPATCHER_MODE=http` is needed. Currently a stub.

---

## 17. Related

- ADR 0004 — Multi-Step Single-Agent Research Engine
- ADR 0009 — Pluggable Research Dispatcher (audit confirmed inlined `/confirm`; helper extraction is Step 2)
- ADR 0014 — Anthropic Prompt Caching (§3.3 zone discipline; LLMCall cache columns audit-confirmed)
- ADR 0016 — Synthesizer Five-Field Contract (`synthesizer_v3_cached` is active per audit)
- ADR 0017 — Reader Near-Match Quote Guard (§5.1 failure translation)
- ADR 0018 — Kimi K2.6 Migration (§3.4 constraints; §6 cost math; §6.3 Sonnet fallback via existing config)
- ADR 0019 (to write) — Chat-Mode Refinement & Auto-Dispatch
- `ARCHITECTURE.md` Sequence 8a + class diagram (both updated in Step 8)
- `USER_FLOW.md` Stage 2 (updated in Step 8)
- `frontend-design-brief-v2.md` §2 + §4 (consumer contract; field names match actual `ValidationReport`)
- `.cursorrules` Quality Discipline
- `procedure.md` (calibration discipline; §4.6 new refinement harness follows the same pattern)
- `llm-schema-calibration.md` (recalibrate-against-measurement precedent)
