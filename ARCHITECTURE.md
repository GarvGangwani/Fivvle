# Fivvle.io — MVP Architecture & UML Diagram Pack

**Version:** MVP 2.3 (final pre-build)
**Audience:** Engineering team (CTO/AI lead, backend co-founder, marketing/design lead, future hires)

All diagrams are written in Mermaid syntax. They render natively in GitHub, GitLab, Notion, VS Code (with the Mermaid extension), Obsidian, and most modern documentation platforms.

---

## MVP Scope (read this first)

**In scope:**
- AI idea refinement (cognitive validation)
- AI research engine — multi-step agentic workflow with 5 phases (planner, searcher, reader/extractor, reflector, synthesizer)
- Validation report with structured findings and citations
- Auto-generated, hosted, tracked landing pages (5 designer-built templates with bounded customization, ISR-cached)
- Page view + source tag + waitlist signup tracking
- Insight report combining research + landing page behavior
- Cost tracking infrastructure

**Out of scope for MVP (deferred):**
- Multi-platform video posting (Instagram, YouTube)
- Comment harvesting and AI comment analysis
- Pitch video upload and storage
- Social account OAuth
- Phone verification
- Payments — free for everyone in MVP
- Reddit posting (read-only research only)
- TikTok integration
- Custom domains per landing page
- Free-form HTML/CSS template editing
- AI-generated landing page layouts (templates with bounded customization only)
- Phase 2 research enhancements (Exa, Firecrawl, deep multi-loop reflection)

---

## Architectural Decision Record: Modular Monolith over Microservices

**Decision:** Fivvle MVP uses a modular monolith architecture, with targeted process-level extraction for long-running background jobs only.

**Status:** Decided May 2026.

**Rationale:**
- Microservices solve problems we don't have at our scale (independent team deploys, polyglot stacks, compliance boundaries)
- Microservices add costs we cannot afford (distributed system complexity, eventual consistency, 5-10x operational overhead, slower local dev, harder debugging)
- Real fault isolation comes from process separation for high-risk components, not splitting all services
- Industry precedent: Stripe, Linear, Notion, Shopify, Basecamp run modular monoliths at scales far larger than ours

**What we chose:**
- One FastAPI monolith on Cloud Run for user-facing API
- Cloud Functions for long-running background jobs (research engine, insight generator, auto-archive)
- One Postgres instance (Cloud SQL)
- Module boundaries inside the monolith enforced by code conventions
- Next.js frontend is its own deployment

**Process isolation:**

| Component | Process | Reason |
|---|---|---|
| Frontend (Next.js) | Vercel/Firebase Hosting | Different runtime, different scaling |
| Backend API (FastAPI) | Cloud Run | User-facing, low-latency |
| Research Engine | Cloud Function | 2-4 minute runs, must not block user requests |
| Insight Generator | Cloud Function | Background work, independent retry |
| Auto-archive | Cloud Function | Cron-driven |

**Triggers for future service extraction (NOT a microservices migration):**
- A specific component has fundamentally different scaling requirements
- A specific component has compliance boundaries
- Engineering team grows past 10+ engineers in independent product teams
- Production data shows a specific component as a recurring single point of failure

---

## Diagram Index

| # | Diagram | Purpose |
|---|---|---|
| 1 | Use Case Diagram | Actors and system boundaries |
| 2 | Class Diagram | Data model — implement as SQLAlchemy schema |
| 3 | Component Diagram | Software architecture |
| 4 | Deployment Diagram | Physical infrastructure |
| 5 | Trust Boundaries | Security boundaries between components |
| 6 | State Machine Diagram | Experiment lifecycle |
| 7 | Activity Diagram | End-to-end founder journey |
| 8a | Sequence — Idea refinement | Founder ↔ AI refinement loop |
| 8b | Sequence — Agentic research engine | Multi-phase research workflow |
| 8c | Sequence — Insight generation | Final report synthesis |

---

## 1. Use Case Diagram

```mermaid
flowchart LR
    Founder((Founder))
    Audience((Public<br/>Audience))
    Admin((Admin))
    LLMAPI((LLM APIs))
    SearchAPI((Search/Trends<br/>APIs))

    subgraph FV[Fivvle System]
        UC1[Sign Up / Authenticate]
        UC2[Submit Raw Idea]
        UC3[Review & Edit AI Refinement]
        UC4[View Validation Report]
        UC5[Choose Template & Customize Landing Page]
        UC6[Publish Landing Page]
        UC7[Share with Source Tags]
        UC8[View Live Metrics]
        UC9[View Insight Report]
        UC10[Iterate on Experiment]
        UC11[View Landing Page]
        UC12[Submit Interest / Waitlist]
        UC13[Moderate Content]
        UC14[View System Metrics & Cost Dashboard]
    end

    Founder --> UC1
    Founder --> UC2
    Founder --> UC3
    Founder --> UC4
    Founder --> UC5
    Founder --> UC6
    Founder --> UC7
    Founder --> UC8
    Founder --> UC9
    Founder --> UC10

    Audience --> UC11
    Audience --> UC12

    Admin --> UC13
    Admin --> UC14

    UC3 -.uses.-> LLMAPI
    UC4 -.uses.-> LLMAPI
    UC4 -.uses.-> SearchAPI
    UC9 -.uses.-> LLMAPI
```

---

## 2. Class Diagram

```mermaid
classDiagram
    class User {
        +UUID id
        +string firebase_uid
        +string email
        +string name
        +timestamp created_at
        +int credits_remaining
    }

    class Experiment {
        +UUID id
        +UUID user_id
        +string slug
        +text raw_idea
        +JSON refined_idea
        +enum status
        +timestamp created_at
        +timestamp updated_at
    }

    class ValidationReport {
        +UUID id
        +UUID experiment_id
        +JSON research_questions
        +JSON findings_per_question
        +JSON competitors
        +JSON reddit_signals
        +JSON search_trends
        +JSON news_signals
        +JSON citations
        +int clarity_score
        +JSON risks
        +text market_summary
        +int reflection_loops_used
        +timestamp generated_at
    }

    class LLMCall {
        +UUID id
        +UUID experiment_id
        +string phase
        +string provider
        +string model
        +string prompt_name
        +int prompt_tokens
        +int completion_tokens
        +decimal cost_usd
        +int latency_ms
        +string request_id
        +timestamp called_at
    }

    class ExternalAPICall {
        +UUID id
        +UUID experiment_id
        +string provider
        +string operation
        +int latency_ms
        +decimal cost_usd
        +bool success
        +timestamp called_at
    }

    class LandingPage {
        +UUID id
        +UUID experiment_id
        +string template_id
        +string palette_id
        +string font_pair_id
        +enum density
        +JSON enabled_sections
        +string headline
        +string subheadline
        +text problem_desc
        +text solution_desc
        +string cta_text
        +enum cta_type
        +JSON features
        +JSON how_it_works
        +JSON faq
        +JSON founder_bio
        +string slug
        +timestamp live_at
        +timestamp last_revalidated_at
    }

    class PageView {
        +UUID id
        +UUID experiment_id
        +string source_tag
        +timestamp ts
        +int time_on_page_sec
        +string user_agent
        +string ip_address
        +string referrer
    }

    class WaitlistSignup {
        +UUID id
        +UUID experiment_id
        +string email
        +string source_tag
        +timestamp ts
    }

    class InsightReport {
        +UUID id
        +UUID experiment_id
        +JSON traffic_summary
        +JSON conversion_by_source
        +JSON research_takeaways
        +text recommendation
        +enum recommendation_type
        +timestamp generated_at
    }

    User "1" --> "*" Experiment
    Experiment "1" --> "0..1" ValidationReport
    Experiment "1" --> "0..1" LandingPage
    Experiment "1" --> "*" PageView
    Experiment "1" --> "*" WaitlistSignup
    Experiment "1" --> "0..1" InsightReport
    Experiment "1" --> "*" LLMCall
    Experiment "1" --> "*" ExternalAPICall
```

---

## 3. Component Diagram

```mermaid
flowchart TB
    subgraph Client[Client Layer]
        Browser[Web Browser]
    end

    subgraph FE[Frontend - Next.js on Vercel/Firebase Hosting]
        UI[Next.js App<br/>React Components]
        FBAuthClient[Firebase Auth Client SDK]
        APIClient[FastAPI HTTP Client]
        LandingRender[Public Landing Pages<br/>5 templates, ISR-cached]
    end

    subgraph BE[Backend - FastAPI on Cloud Run]
        AuthMW[Auth Middleware]
        Routers[FastAPI Routers]

        subgraph Services[Services]
            ExpSvc[Experiment Service]
            RefineSvc[Refinement Service]
            LandingSvc[Landing Page Service<br/>incl. AI template selection]
            InsightSvc[Insight Service]
            AnalyticsSvc[Analytics Service]
            CostSvc[Cost Tracking Service]
        end

        LLMClient[LLM Client]
        Integrations[Integrations: Tavily, Trends, Reddit]
    end

    subgraph BG[Background Jobs - Cloud Functions]
        ResearchEngine[Research Engine 5-phase]
        InsightFn[Insight Generator]
        AutoArchiveFn[Auto-Archive]
    end

    subgraph Data[Data Layer]
        Postgres[(Cloud SQL Postgres)]
        FBAuth[(Firebase Auth)]
    end

    Browser --> UI
    Browser --> LandingRender
    UI --> FBAuthClient
    FBAuthClient -.token.-> APIClient
    APIClient -->|HTTPS + Bearer| AuthMW
    LandingRender -->|page view beacon| AnalyticsSvc

    AuthMW --> Routers
    Routers --> ExpSvc
    Routers --> RefineSvc
    Routers --> LandingSvc
    Routers --> InsightSvc
    Routers --> AnalyticsSvc

    ExpSvc --> Postgres
    RefineSvc --> LLMClient
    LandingSvc --> LLMClient
    LandingSvc --> Postgres
    InsightSvc --> LLMClient
    AnalyticsSvc --> Postgres

    Routers -.triggers.-> ResearchEngine
    ResearchEngine --> LLMClient
    ResearchEngine --> Integrations
    InsightFn --> InsightSvc
    AutoArchiveFn --> ExpSvc

    AuthMW <--> FBAuth
```

---

## 4. Deployment Diagram

```mermaid
flowchart TB
    subgraph UD[User Device]
        BR[Web Browser]
    end

    subgraph FEHost[Frontend Hosting]
        NextApp[Next.js App<br/>SSR + ISR]
        CDN[Edge CDN]
    end

    subgraph BEHost[Cloud Run]
        FastAPIApp[FastAPI Container]
    end

    subgraph GCP[Google Cloud Platform]
        CloudSQL[(Cloud SQL Postgres)]
        FBAuthSvc[Firebase Auth]
        CFunc[Cloud Functions]
        CSched[Cloud Scheduler]
        SecretMgr[Secret Manager]
    end

    subgraph External[External Services]
        ClaudeAPI[Anthropic Claude]
        GroqAPI[Groq]
        TavilySearch[Tavily]
        GTrends[Google Trends]
        RedditPublic[Reddit Free Tier]
    end

    BR <-->|HTTPS| CDN
    CDN <-.->|origin fetch| NextApp
    BR <-->|HTTPS| FastAPIApp
    NextApp <-.token.-> FBAuthSvc
    NextApp <-->|HTTPS + Bearer| FastAPIApp

    FastAPIApp <-->|asyncpg| CloudSQL
    FastAPIApp <-->|Admin SDK| FBAuthSvc
    FastAPIApp <-->|reads| SecretMgr
    FastAPIApp -.triggers.-> CFunc

    CSched -->|cron| CFunc
    CFunc <--> CloudSQL
    CFunc <-->|reads| SecretMgr

    FastAPIApp --> ClaudeAPI
    FastAPIApp --> GroqAPI
    CFunc --> ClaudeAPI
    CFunc --> TavilySearch
    CFunc --> GTrends
    CFunc --> RedditPublic
```

---

## 5. Trust Boundaries

```mermaid
flowchart TB
    subgraph Untrusted[UNTRUSTED ZONE]
        User[User Browser<br/>Treat all input as hostile]
        PublicAudience[Public Landing Page Visitors<br/>Unauthenticated]
        ScrapedContent[Scraped Web Content<br/>May contain prompt injection]
    end

    subgraph SemiTrusted[SEMI-TRUSTED ZONE]
        Frontend[Next.js Frontend<br/>NO secrets, NO API keys]
    end

    subgraph Trusted[TRUSTED ZONE - Backend Only]
        FastAPI[FastAPI Backend<br/>Holds all API keys]
        CFunctions[Cloud Functions<br/>Least-privilege service accounts]
        LLMs[LLM API Calls<br/>Receive structured prompts<br/>NO Fivvle credentials]
    end

    subgraph Secrets[SECRETS ZONE]
        SecretMgr[Google Secret Manager]
    end

    subgraph Storage[STORAGE]
        DB[(Cloud SQL)]
    end

    User -->|HTTPS| Frontend
    Frontend -->|Firebase ID Token| FastAPI
    PublicAudience -->|HTTPS, rate-limited| FastAPI

    FastAPI -.reads.-> SecretMgr
    CFunctions -.reads.-> SecretMgr
    FastAPI <--> DB
    CFunctions <--> DB

    FastAPI --> LLMs
    CFunctions --> LLMs

    ScrapedContent -.input data only.-> LLMs
    LLMs -.text response only.-> CFunctions
```

**Trust boundary rules:**

| Boundary | Rule |
|---|---|
| Browser → Frontend | All user input treated as hostile |
| Frontend → Backend | Every authenticated request requires verified Firebase ID token |
| Backend → External APIs | API keys read from Secret Manager, never hardcoded |
| Backend → Database | Parameterized queries only |
| Cloud Function → Database | Least-privilege service accounts |
| LLM ← Scraped Content | Prompts treat scraped content as data, not instructions |
| LLM → System | LLMs return text, code decides actions, LLMs cannot call Fivvle endpoints |
| Frontend → External APIs | NEVER |
| Frontend → LLMs | NEVER (streaming through backend) |
| Frontend → Database | NEVER |
| Frontend secrets | NEVER (only Firebase client config, which is public identifiers) |

---

## 6. State Machine Diagram

```mermaid
stateDiagram-v2
    [*] --> DRAFT: User creates experiment

    DRAFT --> REFINING: Submit raw idea
    REFINING --> REFINED: AI returns output
    REFINING --> DRAFT: AI error / cancel

    REFINED --> REFINING: User requests re-refine
    REFINED --> RESEARCHING: User accepts refinement

    RESEARCHING --> RESEARCH_PLANNING: Engine starts
    RESEARCH_PLANNING --> RESEARCH_SEARCHING: Questions generated
    RESEARCH_SEARCHING --> RESEARCH_READING: Searches complete
    RESEARCH_READING --> RESEARCH_REFLECTING: Initial findings extracted
    RESEARCH_REFLECTING --> RESEARCH_SEARCHING: Need more (max 1-2 loops)
    RESEARCH_REFLECTING --> RESEARCH_SYNTHESIZING: Findings sufficient
    RESEARCH_SYNTHESIZING --> RESEARCH_READY: Report generated
    RESEARCHING --> RESEARCH_FAILED: Any phase errors
    RESEARCH_FAILED --> RESEARCHING: Retry

    RESEARCH_READY --> LANDING_GENERATING: Auto-generate page
    LANDING_GENERATING --> LANDING_DRAFT: AI selects template, populates copy

    LANDING_DRAFT --> LANDING_LIVE: User publishes
    LANDING_DRAFT --> LANDING_DRAFT: User edits copy or swaps template

    LANDING_LIVE --> LANDING_LIVE: Collecting traffic + signups
    LANDING_LIVE --> ANALYZING: Threshold or 7-day cap or manual

    ANALYZING --> COMPLETED: Insight report generated
    ANALYZING --> ANALYZING: Retry on failure

    COMPLETED --> ARCHIVED: User archives or auto-archive
    COMPLETED --> LANDING_LIVE: User reopens to collect more

    ARCHIVED --> [*]
```

---

## 7. Activity Diagram

```mermaid
flowchart TD
    Start([Founder lands on Fivvle]) --> SignUp[Sign up / Log in]
    SignUp --> NewExp{New experiment?}
    NewExp -->|Yes| EnterIdea[Enter raw idea]
    NewExp -->|No| Dash[View Dashboard]
    Dash --> SelectExp[Select existing experiment]

    EnterIdea --> AIRefine[AI refines idea]
    AIRefine --> ReviewRefine{User satisfied?}
    ReviewRefine -->|No| EditOrRegen[Edit fields or regenerate]
    EditOrRegen --> AIRefine
    ReviewRefine -->|Yes| TriggerResearch[Trigger agentic research engine]

    TriggerResearch --> Plan[Phase 1: Planner]
    Plan --> Search[Phase 2: Parallel searches]
    Search --> Read[Phase 3: Reader extracts evidence]
    Read --> Reflect[Phase 4: Reflector evaluates]
    Reflect --> NeedMore{Need more data?}
    NeedMore -->|Yes, max 1-2 loops| Search
    NeedMore -->|No| Synth[Phase 5: Synthesizer]

    Synth --> ValReport[Validation Report ready]
    ValReport --> Notify[Notify founder via email]
    Notify --> ReviewReport[Founder reviews report]

    ReviewReport --> AISelect[AI selects best template + palette + sections]
    AISelect --> AutoLanding[Landing page draft generated]
    AutoLanding --> CustomizeLP[Founder customizes via knobs]
    CustomizeLP --> ReviewLanding{Founder approves?}
    ReviewLanding -->|No| EditCopy[Edit / swap template]
    EditCopy --> ReviewLanding
    ReviewLanding -->|Yes| PublishPage[Page goes live ISR-cached]

    PublishPage --> ShareLinks[Founder copies source-tagged URLs]
    ShareLinks --> Wait[Founder shares + drives traffic]
    Wait --> Collect[System collects views + signups]
    Collect --> Threshold{Threshold reached?}
    Threshold -->|No| Wait
    Threshold -->|Yes| RunInsight[Generate insight report]

    RunInsight --> ShowReport[Display report]
    ShowReport --> Decision{Founder decides next}
    Decision -->|Iterate| EnterIdea
    Decision -->|Proceed| End([Move forward])
    Decision -->|Pivot| End
    Decision -->|Kill| End
```

---

## 8a. Sequence — Idea Refinement

```mermaid
sequenceDiagram
    actor F as Founder
    participant FE as Frontend
    participant FB as Firebase Auth
    participant API as FastAPI
    participant ES as Experiment Service
    participant RS as Refinement Service
    participant LLM as Claude
    participant Cost as Cost Tracker
    participant DB as Postgres

    F->>FE: Submit raw idea
    FE->>FB: Get ID token
    FB-->>FE: ID token
    FE->>API: POST /experiments + Bearer token
    API->>API: Verify token
    API->>ES: create_experiment(user_id, raw_idea)
    ES->>DB: INSERT experiment (DRAFT)
    ES->>DB: UPDATE status=REFINING
    ES->>RS: refine_idea(raw_idea)
    RS->>LLM: structured prompt
    LLM->>Cost: log call
    LLM-->>RS: refined output
    RS-->>ES: refined_idea JSON
    ES->>DB: UPDATE refined_idea, status=REFINED
    ES-->>API: experiment payload
    API-->>FE: 200 OK
    FE-->>F: Editable refinement form

    alt User edits or regenerates
        F->>FE: "refine again" with feedback
        FE->>API: POST /experiments/{id}/refine
        API->>RS: refine with feedback
        RS->>LLM: prompt with prior + feedback
        LLM->>Cost: log call
        LLM-->>RS: new output
        RS-->>API: updated
        API-->>FE: payload
    end

    F->>FE: Accept
    FE->>API: POST /experiments/{id}/confirm
    API->>DB: UPDATE status=RESEARCHING
    API->>API: Trigger research function (async)
    API-->>FE: 200 OK
```

---

## 8b. Sequence — Agentic Research Engine

```mermaid
sequenceDiagram
    participant API as FastAPI
    participant CF as Research Cloud Function
    participant Planner as Phase 1: Planner
    participant Searcher as Phase 2: Searcher
    participant Reader as Phase 3: Reader
    participant Reflector as Phase 4: Reflector
    participant Synth as Phase 5: Synthesizer
    participant LLM as Claude
    participant Tavily as Tavily
    participant Trends as Google Trends
    participant Reddit as Reddit
    participant Cost as Cost Tracker
    participant DB as Postgres
    actor F as Founder

    API->>CF: Trigger with experiment_id
    CF->>DB: SELECT experiment + refined_idea
    CF->>DB: UPDATE status=RESEARCH_PLANNING

    CF->>Planner: plan(refined_idea)
    Planner->>LLM: prompt → research questions
    LLM->>Cost: log
    LLM-->>Planner: 5-7 questions
    Planner-->>CF: questions
    CF->>DB: UPDATE status=RESEARCH_SEARCHING + STORE questions

    par Q1 search
        CF->>Searcher: search(q1)
        Searcher->>Tavily: query
    and Q2 search
        CF->>Searcher: search(q2)
        Searcher->>Tavily: query
    and Trends
        Searcher->>Trends: query
    and Reddit
        Searcher->>Reddit: query
    end
    Searcher-->>CF: aggregated findings
    CF->>DB: UPDATE status=RESEARCH_READING

    loop For each question
        CF->>Reader: extract(q, raw)
        Reader->>LLM: extract evidence + citations
        LLM->>Cost: log
        LLM-->>Reader: structured findings
    end
    Reader-->>CF: findings_per_question
    CF->>DB: UPDATE status=RESEARCH_REFLECTING

    CF->>Reflector: reflect(questions, findings)
    Reflector->>LLM: gaps?
    LLM->>Cost: log
    LLM-->>Reflector: decision

    alt Wants more (max 1-2 loops)
        Reflector-->>CF: follow-ups
        CF->>DB: UPDATE status=RESEARCH_SEARCHING
        Note over CF: Loop back to Phase 2
    else Sufficient
        Reflector-->>CF: proceed
        CF->>DB: UPDATE status=RESEARCH_SYNTHESIZING
    end

    CF->>Synth: synthesize(findings, citations)
    Synth->>LLM: generate report with citations
    LLM->>Cost: log
    LLM-->>Synth: ValidationReport JSON

    CF->>DB: INSERT validation_report
    CF->>DB: UPDATE status=RESEARCH_READY
    CF->>API: Trigger landing page generation

    API-->>F: Email — research and page ready
```

---

## 8c. Sequence — Insight Generation

```mermaid
sequenceDiagram
    participant Trig as Trigger
    participant CF as Insight Cloud Function
    participant IS as Insight Service
    participant DB as Postgres
    participant LLM as Claude
    participant Cost as Cost Tracker
    actor F as Founder

    Trig->>CF: Trigger with experiment_id

    CF->>DB: SELECT validation_report
    CF->>DB: SELECT page_views by source_tag
    CF->>DB: SELECT signups by source_tag
    CF->>DB: COMPUTE conversion rates

    CF->>IS: synthesize(research, traffic, conversions)
    IS->>LLM: combine signals
    LLM->>Cost: log
    LLM-->>IS: insight report JSON

    CF->>DB: INSERT insight_report
    CF->>DB: UPDATE status=COMPLETED
    CF-->>F: Notify
```

---

## Cost Tracking Architecture

`LLMCall` and `ExternalAPICall` tables capture every paid operation. Per-experiment cost rollups, per-user lifetime cost tracking, daily spend dashboards. Build from day one.

**Per-experiment cost target: under $1.50.**

Soft limits enforced in code:
- Max 5 refinement regenerations per experiment
- Max 5 landing page field regenerations per page
- Max 1-2 reflection loops in research engine
- Hard timeout on research engine: 6 minutes

---

## Landing Page Architecture (Final Plan)

### Template Catalog (5 templates for MVP)

| ID | Name | Best for | Mood |
|---|---|---|---|
| `minimal` | Minimal | B2B SaaS, productivity, dev tools | Confident, premium, understated |
| `vibrant` | Bold/Vibrant | Consumer, design-forward | Energetic, modern |
| `indie` | Indie | Solo founder projects, side projects | Authentic, approachable |
| `premium-dark` | Dark/Premium | Dev tools, AI products | Sleek, technical |
| `editorial` | Editorial | Content-first, social impact | Thoughtful, narrative |

### Props interface (every template implements this)

```typescript
// frontend/components/landing-templates/types.ts

export type LandingPageProps = {
  headline: string;
  subheadline: string;
  problem: string;
  solution: string;
  ctaType: 'waitlist' | 'interest' | 'contact';
  ctaText: string;
  palette: string;
  fontPair: string;
  density: 'compact' | 'roomy';
  features?: Array<{ title: string; description: string; icon?: string }>;
  howItWorks?: Array<{ step: number; title: string; description: string }>;
  faq?: Array<{ question: string; answer: string }>;
  founderBio?: { name: string; bio: string; photoUrl?: string; twitterHandle?: string };
  testimonials?: Array<{ quote: string; author: string; role?: string }>;
  poweredByFivvle: boolean;
  experimentSlug: string;
};

export type TemplateMetadata = {
  id: string;
  name: string;
  description: string;
  bestFor: string[];
  palettes: Array<{ id: string; name: string; preview: string }>;
  fontPairs: Array<{ id: string; name: string; preview: string }>;
  supportsSections: Array<'features' | 'howItWorks' | 'faq' | 'founderBio' | 'testimonials'>;
};
```

### AI's bounded role

ONE LLM call returns: `template_id`, `palette_id`, `font_pair_id`, `enabled_sections`, and copy for the additional sections (features, FAQ, how-it-works). Hero/problem/solution/CTA come from refinement.

### Customization model

Founder can: swap template, change palette, change font pair, toggle density, toggle optional sections, edit any text inline, click "regenerate this with AI" on any field (capped at 5 per page).

### Rendering

- Public landing pages use Incremental Static Regeneration (ISR)
- `revalidate: 60` and on-demand `revalidatePath()` on copy changes
- Cached at CDN edge

### Stack for templates

- React (Server Components default), Next.js 14+ App Router
- TypeScript strict mode
- Tailwind CSS only — no styled-components, no CSS modules, no plain CSS files
- No UI libraries (no shadcn/ui, Radix, Headless UI, MUI, etc.)
- Icons: `lucide-react` only
- Fonts: `next/font/google`
- Images: `next/image`
- Animations: Tailwind utilities first; Framer Motion only if needed
- Forms: plain HTML elements styled with Tailwind
- Accessibility: semantic HTML, alt text, keyboard-accessible, WCAG AA contrast

---

## How to use this document

1. **Open in Mermaid-compatible editor.** GitHub renders inline.
2. **Class Diagram → SQLAlchemy models.** Use Alembic for migrations.
3. **State Machine → Python Enum.** Match diagram exactly.
4. **Sequence Diagrams → API + service code.** When implementing, the diagram is the spec.
5. **Trust Boundaries → security review checklist.**
6. **Update as you build.** Living document.
