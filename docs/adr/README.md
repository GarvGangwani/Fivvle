# Architecture Decision Records

This directory contains a log of major architectural and product decisions made for Fivvle.io. Each ADR captures the context, the decision, and the reasoning at the moment it was made.

## Format

Each ADR follows the Michael Nygard format:

- **Title** — short noun phrase describing the decision
- **Status** — Proposed, Accepted, Superseded, Deprecated
- **Context** — what's going on, what forces are at play
- **Decision** — what we're doing about it
- **Consequences** — what becomes easier and harder as a result

## Index

| # | Title | Status | Date |
|---|---|---|---|
| 0001 | [Modular monolith over microservices](0001-modular-monolith.md) | Accepted | 2026-05 |
| 0002 | [FastAPI + Python over Node.js for backend](0002-fastapi-python-backend.md) | Accepted | 2026-05 |
| 0003 | [Cloud SQL Postgres direct over Firebase Data Connect](0003-cloud-sql-direct.md) | Accepted | 2026-05 |
| 0004 | [Multi-step single-agent research engine over multi-agent](0004-single-agent-research-engine.md) | Accepted | 2026-05 |
| 0005 | [Designer-built templates over AI-generated landing pages](0005-templates-not-ai-generated.md) | Accepted | 2026-05 |
| 0006 | [Video posting and comment harvesting deferred to v2](0006-video-posting-deferred.md) | Accepted | 2026-05 |
| 0007 | [No payments in MVP — free for everyone during launch phase](0007-no-payments-mvp.md) | Accepted | 2026-05 |
| 0008 | [Upgrade Next.js 14 → 15 and React 18 → 19 to Address Unpatched RSC DoS Vulnerabilities](0008-nextjs-15-upgrade.md) | Proposed | 2026-05 |
| 0009 | [Pluggable Research Dispatcher — In-Process for Dev, HTTP for Prod](0009-pluggable-research-dispatcher.md) | Accepted | 2026-05 |

## When to write a new ADR

Write one when you make a decision that:
- Will be hard to reverse later
- Future engineers will wonder "why?" about
- Has alternatives worth recording
- Affects the architecture, security model, or product scope

Don't write ADRs for routine implementation choices, library version updates, or anything that's obvious from the code.
