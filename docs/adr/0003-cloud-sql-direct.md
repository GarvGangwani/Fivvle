# ADR 0003: Cloud SQL Postgres Direct over Firebase Data Connect

**Status:** Accepted
**Date:** 2026-05

## Context

Fivvle uses Firebase for authentication and is generally aligned with the Firebase / Google Cloud ecosystem. The natural-feeling default for the database would be either Firestore (NoSQL) or Firebase Data Connect (Firebase's PostgreSQL-backed product).

Important constraint: **Supabase is blocked in India** under Section 69A of the IT Act, ruling it out for our team operating from India.

We need to decide what database product to use given:
- A FastAPI Python backend (decided in ADR 0002)
- Relational data with frequent aggregate queries (per-source conversion rates, sentiment summaries, comment categorizations)
- Cost tracking that requires JOINs across tables
- A team that wants to stay in the Firebase / Google Cloud ecosystem operationally

## Decision

We will use **Cloud SQL for PostgreSQL accessed directly via SQLAlchemy 2.0 async + asyncpg**, NOT through Firebase Data Connect.

- Cloud SQL Postgres instance provisioned in the same Google Cloud project as our Firebase services
- SQLAlchemy 2.0 async + asyncpg for connection
- Alembic for migrations
- Firebase Auth, Firebase Storage, Firebase Cloud Functions remain in use — we are dropping only the Data Connect layer

## Reasoning

**Firebase Data Connect is wrong for a Python backend:**
Firebase Data Connect is a TypeScript-first GraphQL gateway over Cloud SQL. Its main value proposition is the generated, type-safe TypeScript client for Next.js apps. From a Python backend, we would:
- Talk to Data Connect's GraphQL endpoint instead of the underlying Postgres directly
- Add an extra network hop on every database operation
- Pay for a layer whose main benefit (TS client) we don't use
- Make ourselves dependent on a relatively new Firebase product with uncertain longevity

**Firestore is wrong for our data model:**
Firestore is document-oriented and schemaless. Our data is fundamentally relational:
- Users have experiments
- Experiments have validation reports, landing pages, page views, signups, insight reports
- We run constant aggregate queries (conversion rate by source tag, cost per experiment, sentiment by platform)
- Postgres handles this natively; Firestore makes it painful and expensive

**Direct Cloud SQL access gives us:**
- Real Postgres semantics: transactions, JOINs, indexes, foreign keys
- SQLAlchemy 2.0 async with asyncpg — performant, mature, well-documented
- Alembic for migration management
- Standard Postgres monitoring and operations
- Same Google Cloud project as Firebase Auth and Cloud Functions (single billing, single IAM context)

**Supabase was a natural alternative but is unavailable:**
- Supabase has been blocked in India since February 2026 under Section 69A of the IT Act
- Section 69A blocks have historically remained in place for years (e.g., TikTok)
- Building on Supabase from India would be a real ongoing risk

## Consequences

**What becomes easier:**
- Schema design follows standard Postgres patterns (no NoSQL workarounds)
- Aggregate queries for analytics and cost tracking are straightforward SQL
- Hiring future engineers: SQLAlchemy + Postgres is widely known
- Migrations via Alembic are battle-tested

**What becomes harder:**
- We don't get the auto-generated TypeScript client that Firebase Data Connect would provide
- Frontend types are maintained manually (matched to Pydantic schemas)

**What we accept:**
- One more piece of infrastructure to operate (Cloud SQL instance)
- Direct connection management instead of a managed gateway
- We are responsible for connection pooling tuning

## Related

- ADR 0001 (Modular Monolith — defines what data lives where)
- ADR 0002 (FastAPI + Python — the consumer of this database)
