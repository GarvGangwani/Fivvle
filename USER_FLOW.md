# Fivvle.io — Founder User Flow

The complete journey of a founder from landing on the site to receiving a validation report.

**Version:** MVP 2.3 — final pre-build.

---

## Stage 1: Discovery & Signup

**Step 1.1 — Lands on Fivvle homepage**
- Sees: hero pitch, example validation reports, sample insight reports, social proof
- Does: clicks "Start validating" or "Sign up"
- System: standard marketing site

**Step 1.2 — Signs up**
- Sees: signup form (email + password, or Google OAuth)
- Does: creates account
- System: Firebase Auth creates auth record, frontend gets ID token, calls FastAPI `/users/sync` which creates a `User` row in Postgres

**Step 1.3 — Lands on empty dashboard**
- Sees: clean dashboard with one big CTA — "Submit your first idea"
- Does: clicks the CTA

---

## Stage 2: Idea Submission & Cognitive Refinement

**Step 2.1 — Enters raw idea**
- Sees: textarea with prompt — "Describe your idea: what's the problem, who's it for, and what's your proposed solution?"
- Does: writes 2-5 sentences in their own words
- System: POST to FastAPI `/experiments`. Backend verifies token, creates `Experiment` (status=DRAFT), transitions to `REFINING`

**Step 2.2 — Waits while AI refines (5-10 seconds — sync)**
- Sees: loading state with progress messaging
- Does: waits
- System: FastAPI calls Claude. Returns refined one-liner, target audience, value prop, risks, headline/subheadline/CTA copy. Stored as JSON in `Experiment.refined_idea`. Status moves to `REFINED`. Logged to `LLMCall`.

**Step 2.3 — Reviews and edits AI refinement**
- Sees: structured form with each AI-generated field editable inline
- Does: reads, edits inline, or clicks "Refine again" with optional feedback
- System: regeneration capped at 5 per experiment

**Step 2.4 — Accepts the refinement**
- Sees: "Accept and continue" button with note: "We'll now run a deep market research investigation. This takes 2-4 minutes — we'll email you when it's ready."
- Does: clicks
- System: status → `RESEARCHING`, triggers research Cloud Function. User moves to research-in-progress screen.

---

## Stage 3: Agentic Market Research (2-4 minutes, async)

**Step 3.1 — Sees research-in-progress screen**
- Sees: live phase indicator:
  - "Planning your research questions..."
  - "Searching across sources..."
  - "Reading and extracting evidence..."
  - "Reflecting on findings..."
  - "Synthesizing the validation report..."
- Does: can leave the page; gets email + in-app notification when done

**Step 3.2 — Research phases run in sequence**
1. Planner — generates 5-7 research questions
2. Searcher — parallel searches across Tavily, Reddit, Trends, news
3. Reader — extracts evidence per question with citations
4. Reflector — evaluates gaps, optionally generates follow-ups (max 1-2 loops)
5. Synthesizer — produces structured validation report

**Step 3.3 — Research completes**
- Sees: email notification, in-app badge
- Does: clicks through

**Step 3.4 — Reviews validation report**
- Sees: scrollable report with executive summary, research questions and findings, competitor landscape, market trend signals, sentiment summary, news/funding signals, risks, clarity score. Citations are clickable.
- Does: reads, takes notes
- System: read-only view via `GET /experiments/{id}/validation-report`

---

## Stage 4: Landing Page — AI Generates Draft, Founder Customizes

**Step 4.1 — System auto-generates landing page draft**
- Sees: a polished landing page preview already populated and styled
- Does: nothing yet — the draft is ready
- System: ONE LLM call returns the optimal template_id, palette_id, font_pair_id, enabled_sections, and copy for additional sections (features, FAQ, how-it-works) based on the refined idea. Hero/problem/solution/CTA copy come from refinement. Status: `LANDING_DRAFT`.

**Step 4.2 — Reviews and customizes**
- Sees: side-by-side editor — left panel shows customization knobs, right panel shows live preview
- Customization knobs available:
  - **Template** dropdown: 5 templates (Minimal, Vibrant, Indie, Dark/Premium, Editorial)
  - **Color palette** dropdown: that template's available palettes
  - **Font pair** dropdown: that template's available font pairs
  - **Density** toggle: Compact / Roomy
  - **Optional sections** toggles: features, how-it-works, FAQ, founder bio, testimonials (only those the template supports)
  - **Inline copy editing** on every text field
  - **"Regenerate this with AI"** button on each text field (capped at 5 per page)
- Does: tweaks until happy. May not change anything if AI's defaults look great.
- System: every change updates `LandingPage` row via `PATCH /experiments/{id}/landing-page`. AI regenerations log to `LLMCall`.

**Step 4.3 — Publishes the landing page**
- Sees: "Publish" button. After clicking, gets unique URL `fivvle.io/e/{slug}` and a source-tag URL builder
- Does: clicks publish, copies share URLs for different channels
- System: status → `LANDING_LIVE`. Public route rendered server-side with ISR caching.

---

## Stage 5: Behavioral Data Collection (passive, hours-to-days)

**Landing page tracking:**
- Each visit triggers JS beacon → `POST /analytics/page-view` with timestamp, source tag, time-on-page, user agent, referrer
- Each waitlist signup → `POST /experiments/{slug}/waitlist`

**What founder sees:**
- Dashboard shows live metrics widget — page views, signups, conversion rate, source tag breakdown, top channel
- Can manually trigger insight, or let auto-trigger fire (50+ views OR 5+ signups OR 7-day cap)

**Founder's job during this stage: drive distribution.** UI explicitly encourages this with copy and channel suggestions.

---

## Stage 6: Insight Report & Decision

**Step 6.1 — Notification**
- Sees: email + in-app notification — "Your validation insights are ready"
- Does: clicks through

**Step 6.2 — Reviews the insight report**
- Sees: structured report combining cognitive + behavioral signals — page views, signups, conversion rate, source tag breakdown (warm-network bias visible), top channels, time-on-page, research takeaways, AI recommendation (proceed/iterate/pivot/kill with reasoning)
- Does: reads, takes the decision
- System: status → `COMPLETED`

**Step 6.3 — Decides next action**
- Sees: four buttons: Iterate / Move forward and build / Pivot / Kill
- Does: clicks one
- System: experiment archived, dashboard updates

---

## Stage 7: Returning Founder

- Sees: list of past experiments with status, metrics, outcome
- Does: starts new, returns to past, or extends existing
- Free-tier behavior: free for everyone during MVP, 1 research run per experiment

---

## Stage 8: Reopening a Completed Experiment

- Sees: "Continue collecting" button on `COMPLETED` experiment
- Does: clicks → status returns to `LANDING_LIVE`. Insight regenerates when threshold reached.

---

## What the founder never sees

- AI prompts being executed
- Raw scraped data
- Cloud Function logs or LLM token counts
- Cost dashboard (admin-only)
- Boundary between FastAPI and Cloud Functions

---

## Critical UX principles

1. **Sync vs async waits — be honest.**
   - Refinement (5-10s) — sync, loading screen
   - Research (2-4 min) — async, email notification
   - Landing page edit (instant) — sync, live preview
   - Insight generation (15-30s) — sync if user-triggered, async if system-triggered

2. **Show research progress at phase level.**

3. **Default to one-screen-at-a-time.**

4. **Edit-in-place over forms.**

5. **The dashboard is the home base.** No dead ends.

6. **Make distribution effort visible.**

7. **Email is the async notification channel of record.**

8. **The landing page draft should look great out of the box.** First impression matters — AI's default selection should be impressive enough that many founders publish without changing anything.

---

## API surface

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/users/sync` | Sync Firebase user to Postgres |
| POST | `/experiments` | Create experiment, kick off refinement |
| GET | `/experiments` | List user's experiments |
| GET | `/experiments/{id}` | Get full experiment + relations |
| PATCH | `/experiments/{id}` | Edit refined idea |
| POST | `/experiments/{id}/refine` | Re-run refinement with feedback |
| POST | `/experiments/{id}/confirm` | Accept refinement, trigger research |
| GET | `/experiments/{id}/validation-report` | Fetch research output |
| GET | `/experiments/{id}/research-status` | Poll live phase status |
| GET | `/landing-templates` | List available templates with metadata |
| PATCH | `/experiments/{id}/landing-page` | Edit landing page (template, palette, copy, sections) |
| POST | `/experiments/{id}/landing-page/publish` | Go live |
| POST | `/experiments/{id}/landing-page/regenerate-field` | AI rewrite of one field |
| GET | `/experiments/{id}/insight-report` | Fetch insights |
| POST | `/experiments/{id}/analyze` | Trigger insight generation |
| POST | `/experiments/{id}/archive` | Archive with outcome |
| POST | `/analytics/page-view` | Public — landing page traffic |
| POST | `/experiments/{slug}/waitlist` | Public — waitlist signups |

All authenticated endpoints require `Authorization: Bearer <Firebase ID token>`.
