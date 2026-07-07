# Fivvle — Project Summary

*Written 2026-07-05, for founder reference and future discussion with Claude.*

---

## 1. What Fivvle Is

Fivvle is an **AI co-founder for validating startup ideas before you build anything real**.

A founder types in a raw idea. Fivvle then:

1. **Researches it** — an automated pipeline searches the real web, extracts and cites evidence, checks that evidence for contradictions and gaps, and reasons about it.
2. **Reports on it** — produces a structured Validation Report: market signals, competitor mentions, risks, six-dimension scores, and a recommendation (`proceed / iterate / pivot / kill / too_vague_to_recommend`), all backed by citations to real sources.
3. **Tests it in the real world** — auto-generates a hosted, trackable landing page so the founder can put the idea in front of actual people, and tracks page views and waitlist signups by traffic source.
4. **Closes the loop** — combines the original research with real behavioral data (did people actually sign up?) into an Insight Report that tells the founder whether the idea resonated.

**The pitch in one line:** turn "I have an idea" into a defensible, evidence-backed proceed/kill decision in days — without manually researching, building a landing page, or wiring up analytics yourself.

---

## 2. How It's Built

| Layer | Choice |
|---|---|
| Backend | FastAPI (Python 3.11+), modular monolith (deliberately not microservices) |
| Database | Postgres, SQLAlchemy 2.0 (async), Alembic migrations |
| Frontend | Next.js 15.5 / React 19, Tailwind |
| Auth | Firebase (client SDK + server-side Admin verification) |
| LLMs | Anthropic Claude (primary), Groq, OpenAI, Kimi — routed per pipeline phase |
| Search/data | Tavily (web search), Google Trends |
| Payments | Razorpay (credit-based wallet system) |
| Hosting | Cloud Run, with heavy jobs optionally offloaded to Cloud Functions |

Every LLM call is logged to a database table (tokens, cost, latency, which prompt, which phase) — cost and quality are tracked, not just fired-and-forgotten.

**Documentation is a genuine strength here.** There are 23 numbered Architecture Decision Records (`docs/adr/`), a prompt-tuning calibration log, and detailed architecture docs. Most non-obvious decisions in this codebase have a written "why" attached to them — this is unusually disciplined for a project at this stage.

---

## 3. The Core Pipeline (Research Engine)

This is the heart of the product — five phases, mostly automated:

1. **Planner** (LLM) — turns the raw idea into 5–7 concrete research questions.
2. **Searcher** (no LLM) — runs parallel web searches (Tavily) and pulls Google Trends data.
3. **Reader** (LLM) — one call per question, extracts cited evidence, with guardrails against the LLM inventing sources that don't exist.
4. **Reflector** (rule-based) — decides if the evidence is too thin or one-sided and triggers a re-search if so.
5. **Synthesizer** (LLM) — writes the final founder-facing Validation Report.

This pipeline has real guardrails around LLM hallucination (URL allow-listing, verbatim quote checking) — it's built to be trustworthy, not just to produce plausible-sounding text.

---

## 4. Feature Areas

- **Research Engine** — described above; the core product.
- **Business Construction Engine** *(new, in progress)* — a new deterministic layer sitting between Reflector and Synthesizer. It clusters evidence by theme (market, competition, customer, distribution, regulatory, product), detects contradictions, and produces founder-facing business components (positioning, pricing logic, customer definition, etc.).
- **Landing Page V1** — the current production system. Two LLM calls (strategy, then copy) fill in one of ~6 fixed designer templates. Layout is deliberately *not* AI-generated — this was an explicit design decision (ADR 0005) to bound cost and design risk.
- **Landing Page Runtime V2** *(new, in progress)* — a more ambitious, parallel pipeline (4 LLM calls: narrative → creative direction → visual composition → component planning) that appears to let the AI define page structure, not just copy. Fully isolated from V1 (separate table, routes, and frontend).
- **Insight Reports** — combines the original research with real landing-page traffic/signup data once enough visitors have come through, to tell the founder if the idea actually resonated in the wild.
- **Wallet, Coupons & Payments** *(newly shipped)* — a full credit-based monetization system: wallet balances, transaction ledger, coupon codes, and Razorpay-based credit-pack purchases with webhook idempotency.
- **Chat-driven UX** — the primary interface is now a persistent chat (not a form), with message editing/forking, a split-view report canvas, and a "distribute" section for sharing the landing page with tracked links.

---

## 5. Data Model (Simplified)

Everything hangs off an **Experiment** (one idea a founder is testing):

```
User
 └── Experiment (raw idea, refined idea, status)
      ├── ValidationReport   (the research output)
      ├── LandingPage        (V1)
      ├── LandingPageV2Spec  (V2, isolated)
      ├── InsightReport      (behavioral + research synthesis)
      ├── PageView / WaitlistSignup  (many, from the live landing page)
      └── ChatThread → ChatMessage   (the conversational refinement UI)

User
 └── Wallet → WalletTransaction
 └── Coupon → CouponRedemption
 └── PaymentOrder
```

`LLMCall` and `ExternalAPICall` are logged separately and survive experiment deletion, purely for cost auditing.

---

## 6. What's Been Happening Recently

Looking at commit history, three overlapping waves of work:

1. **A long UI/UX polish sprint** — brand identity, chat interface polish, dashboard/shell redesign, navigation.
2. **Research quality improvements** — better question coverage, less competitor-skewed reports, bugfixes in the Trends/search data pipeline.
3. **Chat-as-primary-interface redesign** — moving from a form-based flow to a persistent, ChatGPT-style conversation with a split-screen report view.
4. **Most recent shipped commit**: the entire wallet/coupons/Razorpay payment system — real monetization infrastructure, landed all at once.
5. **Report viewer (ReportCanvas) went through four rapid redesigns in a row** — independent scrolling → premium styling → minimal → "continuous document." This settled very recently, suggesting real design uncertainty that's now resolved.

**Currently in progress (uncommitted, not yet merged):**

- **Business Construction Engine** — a coherent, documented feature (matches `docs/BUSINESS_CONSTRUCTION_ENGINE_IMPLEMENTATION.md`), fully additive and backward-compatible with existing reports.
- **Landing Page Runtime V2** — the new parallel landing-page generation system described above, plus two new database migrations.
- **Export menu refactor** — the report's "Download" button became a dropdown with both HTML and Markdown export options.

---

## 7. Where Things Stand

Fivvle already has: a working, guardrailed research pipeline; a shipped landing-page system with real traffic tracking; a shipped payments/wallet system; and a documented, additive upgrade (Business Construction Engine) plus an experimental next-gen landing page system in flight. The engineering practice (ADRs, cost-tracking, backward-compatible schema changes) is notably more mature than the "MVP" framing in the older architecture docs suggests — the product has outgrown its own documentation in places (see the critique doc for specifics).

*A separate, more critical read of the current state is saved in `docs/FIVVLE_CRITIQUE.md` — worth reading before your next planning conversation.*
