# ADR 0002: FastAPI + Python over Node.js for Backend

**Status:** Accepted
**Date:** 2026-05

## Context

Initial planning assumed a Node.js / Next.js full-stack architecture using Server Actions and API Routes for backend logic. This was reconsidered after clarifying team composition:

- CTO is an AI/ML expert with strong Python skills
- Co-founder developer is a Python backend specialist
- Neither has shipped a non-trivial Next.js production app

The product's most complex component is an AI research engine: a multi-step agentic workflow doing prompt engineering, structured LLM outputs, web scraping orchestration, and synthesis of large amounts of data into reports. This work is heavily Python-ecosystem aligned.

## Decision

We will use **FastAPI on Python 3.11+** for the backend, hosted on **Google Cloud Run**.

- FastAPI for the user-facing API
- Python Cloud Functions for long-running background jobs (research engine, insight generator, auto-archive)
- SQLAlchemy 2.0 async + asyncpg for database access
- Alembic for migrations
- Pydantic v2 for request/response validation
- Instructor for structured LLM outputs
- Firebase Admin SDK (Python) for auth verification
- `uv` for package management
- Next.js + TypeScript remains for the frontend, but as UI-only, not full-stack

## Reasoning

**Team alignment matters more than theoretical stack purity:**
Two developers fighting an unfamiliar stack ship slowly. Two developers in their primary language ship fast. Speed-to-market beats stack elegance for an early-stage startup.

**Python's ecosystem is better suited to our hardest problem:**
- Anthropic SDK, Groq SDK, and Instructor are mature and idiomatic in Python
- LangChain and LangGraph (if ever needed) are Python-first
- pytrends, PRAW, scrapy, BeautifulSoup, and other research-engine adjacent tools are Python-native
- The AI/ML expertise on the team is already in Python

**FastAPI specifically over Django:**
Django is a full-stack framework with a built-in ORM, admin panel, and auth system. We're using Firebase Auth and Cloud SQL with SQLAlchemy. We'd be carrying Django's weight without using its main features. FastAPI is purpose-built for async API services and pairs cleanly with our Pydantic-heavy data layer.

**The hybrid alternative was considered and rejected:**
We considered keeping Next.js Server Actions for synchronous user-facing logic and using Python only for background jobs. This was rejected because:
- It splits business logic across two languages, doubling the surface area
- Auth verification logic would need to exist in both stacks
- Type definitions would need duplication
- The team isn't strong in Next.js, so the synchronous path would also be slow to build

**Cloud Run over Vercel/Railway/Render:**
- Native GCP integration with our other services (Cloud SQL, Cloud Functions, Secret Manager, Firebase)
- Single Google Cloud project for the whole backend
- Container-based deployment gives us flexibility
- Scales to zero, predictable pricing

## Consequences

**What becomes easier:**
- Building the AI research engine, prompts, and integrations
- Iterating on prompt engineering (where most product value lives)
- Hiring future engineers (Python is the dominant ML/AI language)
- Reusing code between FastAPI services and Cloud Functions

**What becomes harder:**
- Frontend ↔ Backend type sharing (we maintain types manually in TypeScript instead of inheriting from a shared codebase)
- Real-time/streaming features (FastAPI handles this, but Next.js Server Actions would have been more ergonomic)
- Frontend is now a separate deployment with its own concerns

**What we accept:**
- Two services to deploy and operate (one FastAPI on Cloud Run, one Next.js on Vercel/Firebase Hosting)
- Frontend types maintained separately from Pydantic schemas
- Some duplication of validation logic (Pydantic on backend, basic validation on frontend for UX)

## Related

- ADR 0001 (Modular Monolith)
- ADR 0003 (Cloud SQL Postgres direct over Firebase Data Connect)
