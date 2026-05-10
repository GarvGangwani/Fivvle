# ADR 0001: Modular Monolith over Microservices

**Status:** Accepted
**Date:** 2026-05

## Context

Early in MVP planning the team considered organizing Fivvle as a microservices architecture. The reasoning was that microservices would give us:
- Better fault isolation if one component fails
- Easier scaling of individual components
- Cleaner code organization that new hires could understand
- An architecture that "looks production-grade"

Our actual situation:
- 2 active developers (one available immediately, one starting in two weeks)
- 1 marketing/design lead
- Targeting MVP launch in ~4 months
- Pre-revenue, pre-funding
- Single Python stack across the entire backend
- No compliance requirements that mandate data isolation
- Estimated initial scale: hundreds of users, not millions

## Decision

We will build Fivvle as a **modular monolith**, with targeted process-level extraction for long-running background jobs only.

Specifically:
- One FastAPI codebase on Cloud Run handles all user-facing API (auth, idea submission, refinement, landing pages, dashboard, analytics, insight viewer)
- Cloud Functions host long-running background work that genuinely needs process isolation: research engine (2-4 minute runs), insight generator, auto-archive
- Single Cloud SQL Postgres instance for all data
- Module boundaries inside the monolith are enforced by code conventions (services own logic, routers stay thin, integrations are isolated)
- Next.js frontend is its own deployment because it has different runtime needs

## Reasoning

**Microservices solve problems we don't have:**
- Independent team deploys → we have 2 developers
- Independent scaling → one Cloud Run instance handles our entire load
- Polyglot stacks → everything is Python
- Compliance boundaries → none exist

**Microservices add costs we cannot afford:**
- Distributed system complexity (network failures, retries, timeouts, eventual consistency)
- 5-10x operational overhead (multiple deploy pipelines, multiple monitoring dashboards, multiple sets of logs)
- Slower local development (8 services in docker-compose vs one process)
- Harder debugging across service boundaries
- Schema evolution becomes a multi-service coordination problem

**The fault isolation argument doesn't hold up under scrutiny:**
- Most outages come from shared dependencies (database, auth, deployment bugs) that splitting services doesn't address
- Microservices add new failure modes (network calls between services) that monoliths don't have
- Real fault isolation comes from process separation for high-risk components — which we already have for the research engine, insight generator, and auto-archive (they're Cloud Functions)

**Industry precedent supports this choice:**
- Stripe, Linear, Notion, Shopify, and Basecamp all run modular monoliths at scales far larger than ours
- Amazon Prime Video publicly migrated from microservices back to a monolith and improved both cost and reliability
- Segment publicly documented the same migration with the same outcome

## Consequences

**What becomes easier:**
- Local development: one repo, one `uv sync`, one `npm install`
- Debugging: stack traces span the whole flow, no service-boundary mysteries
- Refactoring across module boundaries: type-checked, no API versioning required
- Schema evolution: one migration, not coordinated across services
- New hire onboarding: one codebase to understand
- Shipping: features go out in one PR, not coordinated across multiple deploys

**What becomes harder:**
- Independent scaling of components (we have process-level isolation for background jobs, but the user-facing API scales as one unit)
- True team-level deployment independence (not relevant at our team size)
- Strict service boundary enforcement at runtime (we rely on code review and conventions)

**What we accept:**
- We will revisit this decision when scale or team size warrants it
- We rely on disciplined module boundaries instead of physical service boundaries
- If a specific component becomes a recurring failure mode or has fundamentally different scaling requirements, we will extract that one service — not migrate everything to microservices

## Triggers for future service extraction

We will consider extracting a specific service (NOT a full microservices migration) when one of these is true:
- A specific component has fundamentally different scaling requirements (e.g., research engine starts requiring GPU clusters)
- A specific component has compliance boundaries that require physical separation (e.g., payment data with PCI requirements)
- The engineering team grows past 10+ engineers organized into independent product teams with deploy coordination overhead
- Production data clearly shows a specific component as a recurring single point of failure that process isolation doesn't address

We will NOT extract services because:
- "It would feel more scalable"
- "Everyone else does microservices"
- "We might need it someday"

## Related

- ADR 0002 (FastAPI + Python over Node.js)
- ARCHITECTURE.md (Component Diagram, Deployment Diagram)
