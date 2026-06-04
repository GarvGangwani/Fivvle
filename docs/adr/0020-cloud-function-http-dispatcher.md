# ADR 0020 — Cloud Function HTTP Dispatcher Wiring

**Status:** Accepted
**Accepted:** 2026-06-04
**Date:** 2026-06-04
**Related:** ADR 0009 (pluggable dispatcher), ADR 0019 (chat-mode auto-fire)

---

## Context

ADR 0009 defined the dispatcher abstraction: `in_process` for dev/local, `http` for staging/prod. `InProcessDispatcher` is implemented and used in development. `HttpDispatcher` is a stub at `backend/app/dispatchers/http.py` that always raises `DispatchError`. The Cloud Function receiver that `HttpDispatcher` would POST to has not been created.

Production deployment of chat-mode (ADR 0019) and the existing `/confirm` route is blocked. Every dispatch in `DISPATCHER_MODE=http` fails immediately. Local dev works only because `DISPATCHER_MODE=in_process` is the default.

The pipeline entry point is `run_research_engine_pipeline(experiment_id, sessionmaker)` per audit — single experiment ID, function manages its own DB session via the passed sessionmaker.

## Decision

Implement HTTP dispatch as two coordinated artifacts:

**1. HttpDispatcher client** (`backend/app/dispatchers/http.py`)
- POST to `RESEARCH_ENGINE_URL` with JSON body `{"experiment_id": "<uuid>"}`.
- Auth: GCP OIDC bearer token, audience = `RESEARCH_ENGINE_URL` (overridable via optional `OIDC_AUDIENCE` config). Token minted via `google.oauth2.id_token.fetch_id_token`.
- Client timeout: 10 seconds for the POST. Pipeline runs async server-side; client does not wait for completion.
- Success: HTTP 2xx (202 expected). Anything else → `DispatchError`.
- No retry. Caller handles retry via the existing `RESEARCH_FAILED` → `/confirm` re-dispatch path.

**2. Cloud Function receiver** (new package `functions/research_engine/`)
- HTTP-triggered (2nd gen Cloud Functions, which run on Cloud Run).
- Verifies OIDC via GCP IAM (function deployed with `--no-allow-unauthenticated`; only the FastAPI service account holds `roles/cloudfunctions.invoker`).
- Decodes `experiment_id`, calls `init_engine()` for its own DB pool, fires `asyncio.create_task(run_research_engine_pipeline(experiment_id, sessionmaker))`, returns `("", 202)` immediately.
- Configured with `--no-cpu-throttling` so the background task continues after response. CPU stays allocated to the container during background work.
- Timeout: `--timeout 540s` (9 minutes, the 2nd gen HTTP maximum). Pipeline target is ≤6 minutes per `.cursorrules` Operational Notes.

**Dependency change:** `google-auth` (currently transitive via `firebase-admin`) is promoted to a direct dependency in `backend/pyproject.toml` for OIDC ID-token minting in the dispatcher.

**Config additions** (`backend/app/config.py`):
- `oidc_audience: str | None = None` — optional override for OIDC audience. When unset, audience defaults to `research_engine_url`.

**IAM model** (operator action, not code):
- FastAPI Cloud Run service account: `roles/cloudfunctions.invoker` on the research-engine function.
- Cloud Function service account: identical permissions to those in AGENTS.md "Cloud Function service accounts" section — SELECT/UPDATE on own Experiment, INSERT on ValidationReport / LLMCall / ExternalAPICall, nothing else.

## Consequences

### Positive
- Production deployment of `DISPATCHER_MODE=http` becomes possible. Chat-mode (ADR 0019) and `/confirm` work in staging/prod.
- Identical pipeline behavior in dev and prod (same `run_research_engine_pipeline` entry, same DB schema, same observability via LLMCall rows).
- Tight wire contract; mockable for tests.
- Cloud Function IAM model is least-privilege per AGENTS.md.

### Negative
- Fire-and-forget after 202: if the Cloud Function container exits mid-pipeline (force-kill, region failure, billing issue), the experiment is stuck in `RESEARCHING` with no completion event. Recovery: manual status reset to `RESEARCH_FAILED` via admin, then user retries via `/confirm`. No automated watchdog in MVP.
- No retry on the wire — relies on user-driven retry. A flaky CF endpoint produces visible 502s to the founder.
- `google-auth` promoted to direct dep; backend dep footprint grows by what was already transitively installed (no real install-size delta).
- Cost: `--no-cpu-throttling` means CPU is billed during background work, not just request handling. Modeled cost-per-pipeline impact: small (~10% of CF cost line; the LLM calls dominate).

### Neutral
- Existing factory selection (`backend/app/dispatchers/factory.py`) is unchanged. The stub HttpDispatcher class body is replaced; constructor signature can be modified to accept the audience override.
- Cloud Function source lives in a separate top-level directory; deploy is a separate `gcloud functions deploy` from the FastAPI Cloud Run deploy.
- `RESEARCH_ENGINE_URL` in the `_SECRET_ENV_NAMES` redaction list in `research_engine_service.py` is technically wrong (URL is not a secret) but harmless — defer cleanup.

## Alternatives Considered

- **Cloud Tasks queue between FastAPI and CF.** More resilient — durable queue, automatic retries, no container-kill risk. Rejected for MVP because it adds GCP infrastructure setup (queue creation, IAM, deploy automation) without proportional founder-facing value. Revisit when stuck-experiment rate becomes a real production signal.
- **Synchronous CF (hold HTTP connection for 5–7 minutes).** Rejected: blocks a FastAPI worker per dispatch for minutes; defeats the async-pipeline design; conflicts with chat-turn latency expectations (planning §11).
- **Dedicated Cloud Run worker service consuming from a queue.** Heavier infra. Reserved for post-MVP scale.
- **Skip OIDC; use a shared secret header.** Rejected — AGENTS.md mandates service-to-service auth via GCP-native mechanisms.

## Implementation

Three steps. Each commits independently after green pytest.

1. **Backend: HttpDispatcher client + config + deps + tests** (this commit set updates `backend/`).
2. **Cloud Function receiver package** (`functions/research_engine/main.py` + `requirements.txt` + `.gcloudignore`).
3. **Deploy runbook** (`docs/runbooks/research-engine-cloud-function.md`) documenting `gcloud functions deploy` flags, IAM bindings, and env-var configuration.

Status moves to Accepted after human review and a successful staging dispatch.
