# ADR 0009: Pluggable Research Dispatcher — In-Process for Dev, HTTP for Prod

**Status:** Accepted
**Date:** 2026-05

## Context

B2.4 wires up the trigger surface for the research engine: `POST /experiments/{id}/confirm` on FastAPI starts a 2-4 minute Planner → Searcher → Synthesizer pipeline that runs asynchronously and updates `Experiment.status` as it progresses. The endpoint must return immediately (202 Accepted) so the user can move to the research-in-progress screen described in USER_FLOW Stage 2.4.

ADR 0001 already committed us to running long-running background work as Cloud Functions, separate from the FastAPI process. ARCHITECTURE.md Sequence 8b shows this as `API->>CF: Trigger with experiment_id` — an HTTP-shaped handoff. ADR 0002 and `.cursorrules` rule out Celery, Redis, and message queues for MVP, so the trigger has to be either HTTP or in-process.

For production, the choice is straightforward: FastAPI POSTs to the Cloud Function's HTTPS endpoint with an OIDC token, the function runs in its own process with its own DB pool, and the 6-minute hard timeout (`.cursorrules` Operational Notes) lives inside the Cloud Function runtime.

For local development, the choice is less clear. The options are:

1. **HTTP-only.** Run `functions-framework --target=research_engine --port=8081` in a second terminal during dev. FastAPI POSTs to `http://localhost:8081`. Same shape as prod.

2. **In-process only.** No second process. FastAPI invokes the research engine as a Python coroutine via `asyncio.create_task` or `FastAPI BackgroundTasks`. Different shape from prod.

3. **Pluggable.** A dispatcher interface with two implementations. Selected by config. Both call the same `run_research_engine(experiment_id)` entry point.

The cost of the wrong choice is concrete. Prompt engineering — explicitly called out as Fivvle's differentiator in `.cursorrules` Quality Discipline — requires rapid iteration. If dev loops require keeping two terminals running, restarting functions-framework on every code change, and managing two sets of logs, prompt iteration slows down. That's a real cost on the work that determines whether the product is worth paying for.

But there's an opposite risk. The research engine holds a database session across the full pipeline, makes 4-6 LLM calls, hits Tavily ~14 times per run, and runs 2-4 minutes wall-clock. The behavior of that workload under Cloud Functions (own DB pool, own timeout, own memory limits, own concurrency model) is not the same as under FastAPI's `asyncio.create_task` (shared event loop, FastAPI's connection pool, no enforced timeout, killed if Cloud Run shuts down). Dev-only validation against the in-process shape can hide failures that only appear in prod.

## Decision

We will implement a **pluggable research dispatcher** with two implementations, selected at startup by the `DISPATCHER_MODE` environment variable.

- `DISPATCHER_MODE=in_process` (default) — invokes the research engine via `asyncio.create_task` inside the FastAPI process. Used for local dev and tests.
- `DISPATCHER_MODE=http` — POSTs to a configured Cloud Function HTTPS endpoint with an OIDC token. Used in production and any staging environment that mirrors prod.

Both implementations:
- Conform to a single `ResearchDispatcher` Protocol with a `dispatch(experiment_id: UUID) -> None` method
- Are constructed once at app startup and injected via FastAPI dependency
- Emit identical `structlog` fields and phase markers — same keys, same values, same order — so log queries work uniformly across environments
- Call the same `run_research_engine(experiment_id)` entry point inside the research engine module. The function's signature, behavior, DB session scoping, and timeout enforcement are identical regardless of which dispatcher invoked it.

The Cloud Function entry point (HTTP-triggered) is a thin wrapper that decodes the request, calls `run_research_engine`, and returns. No FastAPI dependencies, no shared imports beyond the research engine module itself.

Selection is explicit (env var), not implicit (e.g., "if running locally"). This is deliberate — a misconfigured staging environment that detects itself as "local" and silently switches to in-process would be exactly the kind of dev/prod divergence this ADR is trying to prevent.

## Reasoning

**Why pluggable instead of HTTP-only:**
HTTP-only forces every dev to run functions-framework on a second port, manage two sets of structured logs, and restart the function process on every code change. That friction lands on the work — prompt iteration — that determines product quality. For a 2-person team in a 4-month timeline, the friction matters.

**Why pluggable instead of in-process-only:**
The 2-4 minute workload holding a DB session, making 4-6 LLM calls in sequence, has materially different failure modes under Cloud Functions than under FastAPI's task system. If we only ever validate against the in-process shape, we will find prod-only bugs after launch. Pluggable means we can run the HTTP path in staging or even locally when we need to verify Cloud Function shape specifically.

**Why explicit env var instead of auto-detection:**
Auto-detection ("am I running on Cloud Run? then HTTP") fails silently when wrong. An env var fails loudly — a missing or misconfigured variable causes a clear startup error. The ops cost is one line in the deploy config; the safety gain is real.

**Why identical log fields across dispatchers:**
The single biggest risk of pluggable is "it worked in dev but not in prod, and I can't tell why because the logs look different." Forcing identical structlog shape across both paths means a query like `dispatcher=research phase=searching status=failed` works identically in dev logs and Cloud Logging. If a prod failure can be reproduced in dev, the log diff is signal, not noise.

**Why a Protocol instead of inheritance:**
`typing.Protocol` keeps the implementations decoupled from each other. The HTTP dispatcher doesn't need to know about in-process semantics, and vice versa. Adding a third dispatcher later (see "Triggers for future migration" below) is one new class, not a refactor of a base class.

**Why no message queue (Pub/Sub, Cloud Tasks):**
ADR 0001 and `.cursorrules` rule these out for MVP. The motivation behind that rule is that durable retries, dead-letter queues, and fan-out are features we don't yet need at our scale, and the operational complexity of running them is not yet justified. This ADR does not reverse that decision. It does, however, name the specific signal that would justify reversing it — see below.

## Consequences

**What becomes easier:**
- Local dev runs in one terminal. `uv run uvicorn app.main:app --reload` invokes the research engine in-process. Prompt iteration loop is tight.
- Tests don't need a second process. Unit tests use the in-process dispatcher by default and can be configured to use a fake dispatcher (records calls, doesn't execute) for endpoint-level tests.
- The Cloud Function entry point stays small (decode request, call entry point, return). Most of the surface lives in the research engine module, which is exercised by both dispatchers.
- Staging environments can run either mode by flipping one env var, useful when validating "does this prompt change break the Cloud Function shape specifically."

**What becomes harder:**
- Two code paths to keep behaviorally identical. If the in-process dispatcher gets a feature (e.g., progress callbacks) and the HTTP one doesn't, dev/prod diverge silently. Mitigation: both implementations call the same `run_research_engine` entry point; the dispatchers themselves only handle the trigger, not the work.
- Dev can pass without ever exercising the HTTP path. Mitigation: before any production deploy, run the eval set (`backend/tests/eval/`) at least once with `DISPATCHER_MODE=http` against a local functions-framework instance. This is a checklist item, not an automated gate, for MVP.
- One more environment variable to manage in deploy configs.

**What we accept:**
- The in-process dispatcher does not provide durable retries. If FastAPI restarts mid-pipeline (Cloud Run instance recycle, deploy, OOM), the in-flight research run is lost and the experiment is stuck in a mid-pipeline state. The HTTP dispatcher has the same vulnerability for in-flight runs but is otherwise isolated from FastAPI's lifecycle. Both vulnerabilities are documented as a known limitation in B4 follow-up scope — recovery for stuck experiments lives there, not here.
- B2.4 implements only failure detection (`/confirm` on `RESEARCH_FAILED` is allowed and re-dispatches), not background recovery. A pipeline that dies between phase transitions without writing the failure state remains stuck until manually nudged.
- Logging fields are enforced by convention and code review, not by a base class. A future contributor adding a new structlog field on one dispatcher but not the other will pass tests but break log queries. Mitigation: the field set is documented in `app/dispatchers/README.md` (created in B2.4) and reviewed on PRs touching either dispatcher.

## Triggers for future migration to Pub/Sub or Cloud Tasks

We will consider migrating the HTTP dispatcher to a durable queue (Cloud Tasks or Pub/Sub) — and file a new ADR superseding this one — when one of these is true:

- Production data shows research runs are being lost or stuck due to mid-pipeline FastAPI/Cloud Function failures at a rate users notice (more than ~1% of runs)
- Founders report seeing experiments stuck in `RESEARCHING` or `RESEARCH_SYNTHESIZING` and expecting them to recover automatically
- We add a second background workload (insight generator in B4, auto-archive) and the operational cost of running ad-hoc recovery scripts for both becomes meaningful
- We hit a request volume where the synchronous HTTP dispatch from FastAPI becomes a latency problem for the `/confirm` endpoint

We will NOT migrate to a queue because:
- "Cloud Tasks looks nice"
- "Pub/Sub is the Google Cloud-native answer"
- "We might want fan-out someday"

The queue migration is a real operational addition (a new managed service, IAM, monitoring, dead-letter handling, retry policy tuning). It is worth doing once we have evidence it solves a problem we actually have.

## Related

- ADR 0001 (Modular Monolith — established the principle that background work runs as Cloud Functions, not in FastAPI; this ADR specifies the trigger shape)
- ADR 0002 (FastAPI + Python — rules out Celery and Redis, which is part of why pluggable is the right MVP answer)
- ADR 0004 (Multi-Step Single-Agent Research Engine — the workload this dispatcher triggers)
- ARCHITECTURE.md Sequence Diagram 8b (Agentic Research Engine — shows the API → Cloud Function handoff this ADR makes concrete)
- `.cursorrules` Build Order step B2 ("wrapped as a Cloud Function") and Operational Notes (6-minute timeout, Cloud Functions deploy)
- USER_FLOW.md Stage 2.4 (the user-facing contract this dispatcher serves)
