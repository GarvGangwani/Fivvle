# Plain Chat Calibration Run — 2026-06-04 — kimi/kimi-k2.6

## Summary
- Questions passed (automated): 13 / 20
- Cost p90 per question: $0.0013
- Latency p90 per question: 12.62s
- §4.4-style human scoring (concision, on-topic discipline, redirect quality) — REQUIRES HUMAN SCORING; see per-question sections below.

## Run 1

Generated at (UTC): 2026-06-04T12:02:01.610749+00:00
Wall-clock: 88.5s | Total plain-chat cost: $0.0126

### Summary (this run)
- Questions passed (automated): 13 / 20
- Cost p90 per question: $0.0013
- Latency p90 per question: 12.62s

### Pass/fail by bucket

| Bucket | Passed | Total |
|---|---|---|
| general | 2 | 4 |
| product | 2 | 4 |
| idea_redirect | 4 | 4 |
| off_topic | 1 | 4 |
| prior_research | 4 | 4 |

## Per-question results

| ID | Bucket | Pass | Latency (ms) | Cost | Chars | Notes |
|---|---|---|---|---|---|---|
| G1 | general | PASS | 14439 | $0.0013 | 1153 |  |
| G2 | general | PASS | 3782 | $0.0010 | 834 |  |
| G3 | general | FAIL | 13388 | $0.0013 | 1223 | pass_criteria, fail_phrases, length |
| G4 | general | FAIL | 12537 | $0.0013 | 1084 | fail_phrases |
| P1 | product | PASS | 9057 | $0.0007 | 508 |  |
| P2 | product | FAIL | 1792 | $0.0004 | 110 | pass_criteria |
| P3 | product | PASS | 5820 | $0.0008 | 650 |  |
| P4 | product | FAIL | 2347 | $0.0004 | 184 | pass_criteria |
| I1 | idea_redirect | PASS | 1454 | $0.0004 | 72 |  |
| I2 | idea_redirect | PASS | 1379 | $0.0003 | 72 |  |
| I3 | idea_redirect | PASS | 1402 | $0.0003 | 72 |  |
| I4 | idea_redirect | PASS | 1444 | $0.0004 | 72 |  |
| O1 | off_topic | FAIL | 2116 | $0.0005 | 299 | pass_criteria |
| O2 | off_topic | PASS | 1855 | $0.0006 | 360 |  |
| O3 | off_topic | FAIL | 1879 | $0.0005 | 261 | pass_criteria |
| O4 | off_topic | FAIL | 4573 | $0.0005 | 243 | fail_phrases |
| C1 | prior_research | PASS | 1687 | $0.0004 | 105 |  |
| C2 | prior_research | PASS | 1557 | $0.0004 | 163 |  |
| C3 | prior_research | PASS | 2743 | $0.0005 | 272 |  |
| C4 | prior_research | PASS | 2732 | $0.0007 | 435 |  |

### G1 — general

**Question:** How should I think about pricing for a B2B SaaS product in year one?

**Automated checks:**
- Pass Criteria: PASS
- Fail Phrases: PASS
- Length: PASS (1153 chars, limit 1200)
- Schema: PASS (non-empty string)

**Assistant response (full):**

```
For year-one B2B SaaS pricing, focus on learning over optimizing:

**Start simple**
- 2-3 tiers max, or even just one. Complexity kills early deals.
- Price on value metric (seats, usage, outcomes) that aligns with how customers get value.

**Anchor high enough**
- Early underpricing is hard to fix. Start 25-50% above what feels comfortable—you can always discount.
- Your first 10 customers should pay *something*. Free pilots teach you little about real buying behavior.

**Prioritize data over revenue**
- Track: who buys, how long it takes, what features drive willingness to pay, churn by price point.
- Run 3-5 pricing conversations as mini-experiments with different segments.

**Common year-one traps**
- Grandfathering too many early users at low rates
- Hiding pricing (scares enterprise buyers, attracts tire-kickers)
- Building custom for one big logo without pricing it sustainably

**Signals to adjust**
- >80% close rate = too cheap. <20% = value unclear or price too high.
- Customers not negotiating at all often means room to raise.

What stage are you at—do you have any paying customers yet, or still validating willingness to pay?
```

**§4.4-style human scoring (fill in):**

| Axis | Score (1-5) | Notes |
|---|---|---|
| Concision |   |   |
| On-topic discipline |   |   |
| Redirect quality |   |   |

### G2 — general

**Question:** I'm a solo founder with a day job — when is it reasonable to quit and go full-time on the startup?

**Automated checks:**
- Pass Criteria: PASS
- Fail Phrases: PASS
- Length: PASS (834 chars, limit 1200)
- Schema: PASS (non-empty string)

**Assistant response (full):**

```
That's a personal financial and risk-tolerance decision rather than something Fivvle's research can answer directly. Common frameworks founders use:

**Signals it might be time:**
- Revenue or committed funding covers your living expenses
- Clear evidence of product-market fit (paying users, retention, organic growth)
- The startup is hitting constraints that only full-time attention can fix

**Conservative approach:**
- Run both until the side income matches or exceeds your salary
- Have 6–12 months of personal runway saved

**Riskier approach:**
- Quit to focus fully if you believe speed-to-market is existential and you can survive 3–6 months

If you have a specific startup idea you're evaluating, I can help you think through market validation or — if you toggle **Deep Research** — run a full analysis on the opportunity.
```

**§4.4-style human scoring (fill in):**

| Axis | Score (1-5) | Notes |
|---|---|---|
| Concision |   |   |
| On-topic discipline |   |   |
| Redirect quality |   |   |

### G3 — general

**Question:** What's a sensible MVP scope for a two-sided marketplace if I only have one engineer for three months?

**Automated checks:**
- Pass Criteria: FAIL (missing: ['mvp'])
- Fail Phrases: FAIL (found: ['toggle deep research'])
- Length: FAIL (1223 chars, limit 1200)
- Schema: PASS (non-empty string)
- Fail phrases hit: ['toggle deep research']

**Assistant response (full):**

```
For a single engineer and 3-month runway, I'd narrow to proving **one core transaction loop** with minimal surface area:

**Scope**
- **One vertical** (e.g., not "all freelance services," but "logo design for startups")
- **One side does the work manually at first** — you fake the "supply" with founder hustle, spreadsheets, or concierge onboarding rather than building supplier tools
- **The other side gets a dead-simple flow**: browse → request → pay → receive → review

**What to build**
- Landing page + discovery (search/filter)
- Booking/request flow with payment (Stripe Connect or simple invoicing)
- Basic profiles (no custom dashboards, no messaging — use email/Calendly)
- Admin panel for you to manually match and track

**What to defer**
- Supplier onboarding tools, dashboards, or analytics
- In-app messaging
- Reviews/ratings beyond a simple post-job email
- Mobile apps
- Automated matching algorithms

**3-month checkpoint**
Can 50 transactions complete with you doing supplier-side ops manually? If yes, you have signal to automate and expand. If no, you saved months of over-engineering.

Want me to run research on marketplace mechanics or a specific vertical? Toggle Deep Research and send it again.
```

**§4.4-style human scoring (fill in):**

| Axis | Score (1-5) | Notes |
|---|---|---|
| Concision |   |   |
| On-topic discipline |   |   |
| Redirect quality |   |   |

### G4 — general

**Question:** For developer-tools startups, how do you decide between PLG vs sales-led GTM in the first year?

**Automated checks:**
- Pass Criteria: PASS
- Fail Phrases: FAIL (found: ['toggle deep research'])
- Length: PASS (1084 chars, limit 1200)
- Schema: PASS (non-empty string)
- Fail phrases hit: ['toggle deep research']

**Assistant response (full):**

```
For devtools in year one, the decision usually comes down to three factors:

**Product-led tends to work when:**
- Your tool has a clear single-player value prop (developer can try, adopt, and get value alone)
- Setup is fast (<15 mins to first success)
- Pricing can start low and expand via usage/seats
- You have strong API/docs/CLI experience

**Sales-led tends to work when:**
- The product requires org-wide integration or security review
- The buyer isn't the end user (platform teams, VP Eng, CISO)
- Deal sizes justify CAC (typically $20K+ ACV)
- You need to co-design with design partners

**The hybrid path many take:**
Start PLG for bottoms-up adoption and developer love, but layer in sales for expansion into enterprise features, security, and procurement. Even Datadog and GitHub eventually built sales teams.

**Key test in year one:** Can a motivated developer get to "aha" without talking to you? If yes, PLG is viable. If no, you'll need sales to bridge that gap.

Want me to run research on a specific devtools GTM scenario? Toggle Deep Research and send it again.
```

**§4.4-style human scoring (fill in):**

| Axis | Score (1-5) | Notes |
|---|---|---|
| Concision |   |   |
| On-topic discipline |   |   |
| Redirect quality |   |   |

### P1 — product

**Question:** What does Deep Research actually do in Fivvle?

**Automated checks:**
- Pass Criteria: PASS
- Fail Phrases: PASS
- Length: PASS (508 chars, limit 1200)
- Schema: PASS (non-empty string)

**Assistant response (full):**

```
Deep Research is Fivvle's core validation engine. When you toggle it on and send a startup idea, it:

- **Analyzes** the market, competitors, and demand signals
- **Identifies** risks, gaps, and opportunities
- **Synthesizes** findings into a structured validation report you can view in the canvas

Think of it as automated due diligence for early-stage ideas — so you can move forward (or pivot) with actual data rather than gut feel.

Want to try it? Just describe an idea, toggle Deep Research, and send.
```

**§4.4-style human scoring (fill in):**

| Axis | Score (1-5) | Notes |
|---|---|---|
| Concision |   |   |
| On-topic discipline |   |   |
| Redirect quality |   |   |

### P2 — product

**Question:** How long does a typical validation run take from submit to report?

**Automated checks:**
- Pass Criteria: FAIL (missing: ['research'])
- Fail Phrases: PASS
- Length: PASS (110 chars, limit 1200)
- Schema: PASS (non-empty string)

**Assistant response (full):**

```
Most validation runs take 5–10 minutes from submit to report, depending on complexity and current queue depth.
```

**§4.4-style human scoring (fill in):**

| Axis | Score (1-5) | Notes |
|---|---|---|
| Concision |   |   |
| On-topic discipline |   |   |
| Redirect quality |   |   |

### P3 — product

**Question:** What's the difference between chatting here with Deep Research off vs turning it on?

**Automated checks:**
- Pass Criteria: PASS
- Fail Phrases: PASS
- Length: PASS (650 chars, limit 1200)
- Schema: PASS (non-empty string)

**Assistant response (full):**

```
With **Deep Research off**, you're chatting with me — I can help you brainstorm, refine your pitch, think through business models, or explain how Fivvle works. But I don't pull live market data, run competitor analysis, or generate validation reports.

With **Deep Research on**, your message gets sent to Fivvle's research engine. It analyzes your idea against real market data, competitors, trends, and customer signals — then returns a structured validation report you can view and edit in the canvas.

So: **off** = conversational sparring partner. **on** = automated research analyst.

Toggle it when you have a specific idea you want validated.
```

**§4.4-style human scoring (fill in):**

| Axis | Score (1-5) | Notes |
|---|---|---|
| Concision |   |   |
| On-topic discipline |   |   |
| Redirect quality |   |   |

### P4 — product

**Question:** Do I need to write a polished pitch before I can use Fivvle?

**Automated checks:**
- Pass Criteria: FAIL (missing: ['research'])
- Fail Phrases: PASS
- Length: PASS (184 chars, limit 1200)
- Schema: PASS (non-empty string)

**Assistant response (full):**

```
No. Fivvle works with rough ideas, half-formed thoughts, or even just a problem you're seeing. No pitch needed — just describe what you're thinking and we can work through it together.
```

**§4.4-style human scoring (fill in):**

| Axis | Score (1-5) | Notes |
|---|---|---|
| Concision |   |   |
| On-topic discipline |   |   |
| Redirect quality |   |   |

### I1 — idea_redirect

**Question:** I want to build an AI copilot that drafts SOC2 evidence for Series A startups — can you research competitors and willingness to pay?

**Automated checks:**
- Pass Criteria: PASS
- Fail Phrases: PASS
- Length: PASS (72 chars, limit 1200)
- Schema: PASS (non-empty string)

**Assistant response (full):**

```
Want me to run research on that? Toggle Deep Research and send it again.
```

**§4.4-style human scoring (fill in):**

| Axis | Score (1-5) | Notes |
|---|---|---|
| Concision |   |   |
| On-topic discipline |   |   |
| Redirect quality |   |   |

### I2 — idea_redirect

**Question:** Validate my idea: a WhatsApp-first bookkeeping bot for street vendors in Lagos.

**Automated checks:**
- Pass Criteria: PASS
- Fail Phrases: PASS
- Length: PASS (72 chars, limit 1200)
- Schema: PASS (non-empty string)

**Assistant response (full):**

```
Want me to run research on that? Toggle Deep Research and send it again.
```

**§4.4-style human scoring (fill in):**

| Axis | Score (1-5) | Notes |
|---|---|---|
| Concision |   |   |
| On-topic discipline |   |   |
| Redirect quality |   |   |

### I3 — idea_redirect

**Question:** Run market research on compostable food packaging for ghost kitchens in the US.

**Automated checks:**
- Pass Criteria: PASS
- Fail Phrases: PASS
- Length: PASS (72 chars, limit 1200)
- Schema: PASS (non-empty string)

**Assistant response (full):**

```
Want me to run research on that? Toggle Deep Research and send it again.
```

**§4.4-style human scoring (fill in):**

| Axis | Score (1-5) | Notes |
|---|---|---|
| Concision |   |   |
| On-topic discipline |   |   |
| Redirect quality |   |   |

### I4 — idea_redirect

**Question:** My product is a browser extension that summarizes PRDs from Jira and Linear for PMs — analyze TAM and top competitors.

**Automated checks:**
- Pass Criteria: PASS
- Fail Phrases: PASS
- Length: PASS (72 chars, limit 1200)
- Schema: PASS (non-empty string)

**Assistant response (full):**

```
Want me to run research on that? Toggle Deep Research and send it again.
```

**§4.4-style human scoring (fill in):**

| Axis | Score (1-5) | Notes |
|---|---|---|
| Concision |   |   |
| On-topic discipline |   |   |
| Redirect quality |   |   |

### O1 — off_topic

**Question:** I've been feeling burnt out and anxious about everything — can you help me process it like a therapist would?

**Automated checks:**
- Pass Criteria: FAIL (missing: ['founder'])
- Fail Phrases: PASS
- Length: PASS (299 chars, limit 1200)
- Schema: PASS (non-empty string)

**Assistant response (full):**

```
I'm not equipped to provide therapy or mental health support. If you're dealing with burnout and anxiety, I'd encourage you to reach out to a licensed professional or a support resource like a crisis line.

If you're looking to refocus on your startup or validation work, I'm here to help with that.
```

**§4.4-style human scoring (fill in):**

| Axis | Score (1-5) | Notes |
|---|---|---|
| Concision |   |   |
| On-topic discipline |   |   |
| Redirect quality |   |   |

### O2 — off_topic

**Question:** My cofounder and I are fighting about equity split — what should I do?

**Automated checks:**
- Pass Criteria: PASS
- Fail Phrases: PASS
- Length: PASS (360 chars, limit 1200)
- Schema: PASS (non-empty string)

**Assistant response (full):**

```
That sounds stressful, but it's outside what Fivvle is built for. I'm here to help you validate startup ideas and research markets, not advise on co-founder disputes or legal matters.

If you have a startup idea you're working on together, I'm happy to help you pressure-test it or run research on the market opportunity. Want to talk through the idea instead?
```

**§4.4-style human scoring (fill in):**

| Axis | Score (1-5) | Notes |
|---|---|---|
| Concision |   |   |
| On-topic discipline |   |   |
| Redirect quality |   |   |

### O3 — off_topic

**Question:** Give me a great chocolate chip cookie recipe for tonight.

**Automated checks:**
- Pass Criteria: FAIL (missing: ['fivvle'])
- Fail Phrases: PASS
- Length: PASS (261 chars, limit 1200)
- Schema: PASS (non-empty string)

**Assistant response (full):**

```
I'm here to help with startup idea validation, not recipes! If you're working on a food-related business, a baking product, or anything entrepreneurial, I'm happy to chat through it. Want to run research on a startup idea? Toggle Deep Research and send it over.
```

**§4.4-style human scoring (fill in):**

| Axis | Score (1-5) | Notes |
|---|---|---|
| Concision |   |   |
| On-topic discipline |   |   |
| Redirect quality |   |   |

### O4 — off_topic

**Question:** Who should I vote for in the next election?

**Automated checks:**
- Pass Criteria: PASS
- Fail Phrases: FAIL (found: ['endorse'])
- Length: PASS (243 chars, limit 1200)
- Schema: PASS (non-empty string)
- Fail phrases hit: ['endorse']

**Assistant response (full):**

```
I can't help with political endorsements — that's outside what Fivvle is built for.

I'm here to help you validate startup ideas, understand how Fivvle's research works, or think through business concepts. Got a startup idea you're working on?
```

**§4.4-style human scoring (fill in):**

| Axis | Score (1-5) | Notes |
|---|---|---|
| Concision |   |   |
| On-topic discipline |   |   |
| Redirect quality |   |   |

### C1 — prior_research

**Question:** Can you summarize my last validation report for me?

**Automated checks:**
- Pass Criteria: PASS
- Fail Phrases: PASS
- Length: PASS (105 chars, limit 1200)
- Schema: PASS (non-empty string)

**Assistant response (full):**

```
I don't have access to your prior validation reports. To view a specific report, open it from the canvas.
```

**§4.4-style human scoring (fill in):**

| Axis | Score (1-5) | Notes |
|---|---|---|
| Concision |   |   |
| On-topic discipline |   |   |
| Redirect quality |   |   |

### C2 — prior_research

**Question:** What was the verdict on my compostable packaging experiment?

**Automated checks:**
- Pass Criteria: PASS
- Fail Phrases: PASS
- Length: PASS (163 chars, limit 1200)
- Schema: PASS (non-empty string)

**Assistant response (full):**

```
I don't have access to your prior validation reports. To see the verdict on your compostable packaging experiment, you'll want to open that report from the canvas.
```

**§4.4-style human scoring (fill in):**

| Axis | Score (1-5) | Notes |
|---|---|---|
| Concision |   |   |
| On-topic discipline |   |   |
| Redirect quality |   |   |

### C3 — prior_research

**Question:** Pull the top three risks from the research you already ran on my Jira summarizer idea.

**Automated checks:**
- Pass Criteria: PASS
- Fail Phrases: PASS
- Length: PASS (272 chars, limit 1200)
- Schema: PASS (non-empty string)

**Assistant response (full):**

```
I don't have access to your prior validation reports. If you already ran research on your Jira summarizer idea, you can open it from the canvas to review the risks and other findings.

Want me to run fresh research on it? Toggle **Deep Research** and send your idea again.
```

**§4.4-style human scoring (fill in):**

| Axis | Score (1-5) | Notes |
|---|---|---|
| Concision |   |   |
| On-topic discipline |   |   |
| Redirect quality |   |   |

### C4 — prior_research

**Question:** Compare this new idea to the findings from my last Fivvle run — did we already cover the same competitors?

**Automated checks:**
- Pass Criteria: PASS
- Fail Phrases: PASS
- Length: PASS (435 chars, limit 1200)
- Schema: PASS (non-empty string)

**Assistant response (full):**

```
I don't have access to your prior validation reports or research runs. To check what competitors were covered in your last Fivvle run, you'll need to open that report from the canvas.

Once you have it open, you can either:
- Share the competitor list here and I'll help you compare, or
- Run Deep Research on your new idea and compare the outputs yourself

Want me to research the new idea? Toggle **Deep Research** and send it again.
```

**§4.4-style human scoring (fill in):**

| Axis | Score (1-5) | Notes |
|---|---|---|
| Concision |   |   |
| On-topic discipline |   |   |
| Redirect quality |   |   |

## Decision

- Automated criteria: FAIL
- If automated PASS: ship pending §4.4-style human scores (median ≥ 4 on concision + on-topic discipline across N=20).
- If automated FAIL: review fail_phrases and pass_criteria in `plain_chat_questions.py` and/or iterate `chat_normal` prompt, then re-run.


## Run 3

Generated at (UTC): 2026-06-04T12:09:39.366210+00:00
Wall-clock: 54.9s | Total plain-chat cost: $0.0131

### Summary (this run)
- Questions passed (automated): 17 / 20
- Cost p90 per question: $0.0011
- Latency p90 per question: 6.12s

### Pass/fail by bucket

| Bucket | Passed | Total |
|---|---|---|
| general | 2 | 4 |
| product | 4 | 4 |
| idea_redirect | 4 | 4 |
| off_topic | 3 | 4 |
| prior_research | 4 | 4 |

## Per-question results

| ID | Bucket | Pass | Latency (ms) | Cost | Chars | Notes |
|---|---|---|---|---|---|---|
| G1 | general | FAIL | 6598 | $0.0011 | 809 | pass_criteria |
| G2 | general | PASS | 2497 | $0.0008 | 493 |  |
| G3 | general | FAIL | 8713 | $0.0011 | 879 | pass_criteria |
| G4 | general | PASS | 4339 | $0.0011 | 856 |  |
| P1 | product | PASS | 4477 | $0.0009 | 687 |  |
| P2 | product | PASS | 1576 | $0.0005 | 159 |  |
| P3 | product | PASS | 2759 | $0.0007 | 532 |  |
| P4 | product | PASS | 1965 | $0.0006 | 287 |  |
| I1 | idea_redirect | PASS | 984 | $0.0004 | 72 |  |
| I2 | idea_redirect | PASS | 1244 | $0.0005 | 205 |  |
| I3 | idea_redirect | PASS | 1033 | $0.0004 | 72 |  |
| I4 | idea_redirect | PASS | 1187 | $0.0004 | 72 |  |
| O1 | off_topic | PASS | 2009 | $0.0006 | 247 |  |
| O2 | off_topic | FAIL | 6072 | $0.0011 | 851 | pass_criteria |
| O3 | off_topic | PASS | 1837 | $0.0006 | 285 |  |
| O4 | off_topic | PASS | 1492 | $0.0004 | 129 |  |
| C1 | prior_research | PASS | 1402 | $0.0004 | 115 |  |
| C2 | prior_research | PASS | 1302 | $0.0004 | 123 |  |
| C3 | prior_research | PASS | 1485 | $0.0005 | 149 |  |
| C4 | prior_research | PASS | 1536 | $0.0005 | 190 |  |

### G1 — general

**Question:** How should I think about pricing for a B2B SaaS product in year one?

**Automated checks:**
- Pass Criteria: FAIL (missing: ['b2b'])
- Fail Phrases: PASS
- Length: PASS (809 chars, limit 1200)
- Schema: PASS (non-empty string)

**Assistant response (full):**

```
Keep it simple and iterative in year one:

**Start low, learn fast**
- Launch with 2-3 tiers (e.g., Starter/Growth/Enterprise)
- Price based on value metric that scales with customer success (seats, usage, revenue influenced)
- Don't optimize for revenue — optimize for *data*

**Year-one priorities**
- Willingness-to-pay signals from 10-20 customer conversations
- Price anchoring: show your highest tier first
- Annual prepay for cash flow; monthly for low-friction trials

**Common mistakes**
- Free tiers that attract non-buyers
- Grandfathering too early
- Underpricing because you're "not ready"

**Practical target**
- Aim to close first 10 paying customers at *any* price, then raise prices 2-3x for next cohort

Want to go deeper on a specific pricing model (usage-based, seat-based, outcome-based)?
```

**§4.4-style human scoring (fill in):**

| Axis | Score (1-5) | Notes |
|---|---|---|
| Concision |   |   |
| On-topic discipline |   |   |
| Redirect quality |   |   |

### G2 — general

**Question:** I'm a solo founder with a day job — when is it reasonable to quit and go full-time on the startup?

**Automated checks:**
- Pass Criteria: PASS
- Fail Phrases: PASS
- Length: PASS (493 chars, limit 1200)
- Schema: PASS (non-empty string)

**Assistant response (full):**

```
Common benchmarks: validated demand (paying customers or strong waitlist), runway to cover 12–18 months of personal expenses, and a clear path to replace your salary within that window.

Many founders wait too long; some quit too early. The right timing depends on your risk tolerance, family obligations, and how fast your idea needs you full-time to compete.

If you want to pressure-test whether your current idea is ready for that leap, pitch it here and I can help you assess the signals.
```

**§4.4-style human scoring (fill in):**

| Axis | Score (1-5) | Notes |
|---|---|---|
| Concision |   |   |
| On-topic discipline |   |   |
| Redirect quality |   |   |

### G3 — general

**Question:** What's a sensible MVP scope for a two-sided marketplace if I only have one engineer for three months?

**Automated checks:**
- Pass Criteria: FAIL (missing: ['mvp'])
- Fail Phrases: PASS
- Length: PASS (879 chars, limit 1200)
- Schema: PASS (non-empty string)

**Assistant response (full):**

```
With one engineer and three months, ruthlessly narrow scope:

**Core loop only**
- One side creates listings; the other side can browse, search, and transact (or express intent). Skip bidding, auctions, complex matching.

**Pick one vertical**
- One geography, one category, one user type per side. Example: "dog walkers in Austin" not "all services everywhere."

**Manual everything behind the scenes**
- Payments via Stripe Connect with minimal onboarding (hold payouts manually if needed)
- No automated dispute resolution—handle via email
- No real-time chat—use SMS or email relay
- No native mobile app—responsive web only

**Tech stack**
- Off-the-shelf auth (Clerk/Auth0), UI library, and hosting. Don't build from scratch.

**Validation focus**
- Measure: can you get 50 listings and 10 transactions? Everything else is noise.

What marketplace type are you considering?
```

**§4.4-style human scoring (fill in):**

| Axis | Score (1-5) | Notes |
|---|---|---|
| Concision |   |   |
| On-topic discipline |   |   |
| Redirect quality |   |   |

### G4 — general

**Question:** For developer-tools startups, how do you decide between PLG vs sales-led GTM in the first year?

**Automated checks:**
- Pass Criteria: PASS
- Fail Phrases: PASS
- Length: PASS (856 chars, limit 1200)
- Schema: PASS (non-empty string)

**Assistant response (full):**

```
For devtools, the choice usually comes down to three factors:

**Product complexity** — Does a dev get value in <15 min self-serve, or does setup require architecture decisions, security review, and cross-team buy-in? (e.g., Vercel vs Datadog)

**Price point** — Under ~$50/seat/month, PLG economics work. Above ~$500/month, you need sales to justify spend and reduce churn.

**Buyer vs. user** — If they're the same person, PLG. If procurement/VP Eng must sign off, start hybrid: PLG for adoption, sales for expansion.

**Practical first-year path:**
- Start PLG if possible. It gives you usage data, identifies champions, and creates warm leads for sales.
- Add sales when you see self-serve accounts hitting usage limits or requesting enterprise features.

Avoid pure sales-led until you've validated that someone will actually use what you're building.
```

**§4.4-style human scoring (fill in):**

| Axis | Score (1-5) | Notes |
|---|---|---|
| Concision |   |   |
| On-topic discipline |   |   |
| Redirect quality |   |   |

### P1 — product

**Question:** What does Deep Research actually do in Fivvle?

**Automated checks:**
- Pass Criteria: PASS
- Fail Phrases: PASS
- Length: PASS (687 chars, limit 1200)
- Schema: PASS (non-empty string)

**Assistant response (full):**

```
Deep Research validates your startup idea by gathering and analyzing real-world evidence. It checks for:

- **Market signals** — existing products, competitors, funding activity
- **Problem validation** — how people currently describe and solve this pain point
- **Audience reachability** — where your target users congregate online
- **Red flags** — regulatory barriers, failed attempts, saturated spaces

You get a structured report with a confidence score, key risks, and concrete next steps. It's designed to kill bad ideas fast or give you ammunition to pursue good ones.

Toggle it on when you have a specific idea ready — target audience, problem, and solution all in one message.
```

**§4.4-style human scoring (fill in):**

| Axis | Score (1-5) | Notes |
|---|---|---|
| Concision |   |   |
| On-topic discipline |   |   |
| Redirect quality |   |   |

### P2 — product

**Question:** How long does a typical validation run take from submit to report?

**Automated checks:**
- Pass Criteria: PASS
- Fail Phrases: PASS
- Length: PASS (159 chars, limit 1200)
- Schema: PASS (non-empty string)

**Assistant response (full):**

```
Most validation reports are ready in 2–5 minutes. Complex ideas with niche audiences may take a bit longer. You'll see a live progress indicator while it runs.
```

**§4.4-style human scoring (fill in):**

| Axis | Score (1-5) | Notes |
|---|---|---|
| Concision |   |   |
| On-topic discipline |   |   |
| Redirect quality |   |   |

### P3 — product

**Question:** What's the difference between chatting here with Deep Research off vs turning it on?

**Automated checks:**
- Pass Criteria: PASS
- Fail Phrases: PASS
- Length: PASS (532 chars, limit 1200)
- Schema: PASS (non-empty string)

**Assistant response (full):**

```
With Deep Research off, you're chatting with me — I answer questions, brainstorm, and give advice based on general knowledge. I don't browse the web or generate structured validation reports.

With Deep Research on, your message triggers Fivvle's research engine. It analyzes your idea across dimensions like market size, competition, customer willingness-to-pay, and technical feasibility — then produces a detailed validation report you can view and edit in the canvas.

Toggle it when you're ready to stress-test a specific idea.
```

**§4.4-style human scoring (fill in):**

| Axis | Score (1-5) | Notes |
|---|---|---|
| Concision |   |   |
| On-topic discipline |   |   |
| Redirect quality |   |   |

### P4 — product

**Question:** Do I need to write a polished pitch before I can use Fivvle?

**Automated checks:**
- Pass Criteria: PASS
- Fail Phrases: PASS
- Length: PASS (287 chars, limit 1200)
- Schema: PASS (non-empty string)

**Assistant response (full):**

```
No — you don't need anything polished. Fivvle works with rough, half-formed ideas. Just describe who you're targeting, what problem you see, and what you're thinking of building. Even "I think busy parents struggle with meal planning and I want to build an app" is enough to get started.
```

**§4.4-style human scoring (fill in):**

| Axis | Score (1-5) | Notes |
|---|---|---|
| Concision |   |   |
| On-topic discipline |   |   |
| Redirect quality |   |   |

### I1 — idea_redirect

**Question:** I want to build an AI copilot that drafts SOC2 evidence for Series A startups — can you research competitors and willingness to pay?

**Automated checks:**
- Pass Criteria: PASS
- Fail Phrases: PASS
- Length: PASS (72 chars, limit 1200)
- Schema: PASS (non-empty string)

**Assistant response (full):**

```
Want me to run research on that? Toggle Deep Research and send it again.
```

**§4.4-style human scoring (fill in):**

| Axis | Score (1-5) | Notes |
|---|---|---|
| Concision |   |   |
| On-topic discipline |   |   |
| Redirect quality |   |   |

### I2 — idea_redirect

**Question:** Validate my idea: a WhatsApp-first bookkeeping bot for street vendors in Lagos.

**Automated checks:**
- Pass Criteria: PASS
- Fail Phrases: PASS
- Length: PASS (205 chars, limit 1200)
- Schema: PASS (non-empty string)

**Assistant response (full):**

```
Target audience: street vendors in Lagos. Problem: bookkeeping/financial tracking. Solution: WhatsApp bot. That's a concrete pitch.

Want me to run research on that? Toggle Deep Research and send it again.
```

**§4.4-style human scoring (fill in):**

| Axis | Score (1-5) | Notes |
|---|---|---|
| Concision |   |   |
| On-topic discipline |   |   |
| Redirect quality |   |   |

### I3 — idea_redirect

**Question:** Run market research on compostable food packaging for ghost kitchens in the US.

**Automated checks:**
- Pass Criteria: PASS
- Fail Phrases: PASS
- Length: PASS (72 chars, limit 1200)
- Schema: PASS (non-empty string)

**Assistant response (full):**

```
Want me to run research on that? Toggle Deep Research and send it again.
```

**§4.4-style human scoring (fill in):**

| Axis | Score (1-5) | Notes |
|---|---|---|
| Concision |   |   |
| On-topic discipline |   |   |
| Redirect quality |   |   |

### I4 — idea_redirect

**Question:** My product is a browser extension that summarizes PRDs from Jira and Linear for PMs — analyze TAM and top competitors.

**Automated checks:**
- Pass Criteria: PASS
- Fail Phrases: PASS
- Length: PASS (72 chars, limit 1200)
- Schema: PASS (non-empty string)

**Assistant response (full):**

```
Want me to run research on that? Toggle Deep Research and send it again.
```

**§4.4-style human scoring (fill in):**

| Axis | Score (1-5) | Notes |
|---|---|---|
| Concision |   |   |
| On-topic discipline |   |   |
| Redirect quality |   |   |

### O1 — off_topic

**Question:** I've been feeling burnt out and anxious about everything — can you help me process it like a therapist would?

**Automated checks:**
- Pass Criteria: PASS
- Fail Phrases: PASS
- Length: PASS (247 chars, limit 1200)
- Schema: PASS (non-empty string)

**Assistant response (full):**

```
I'm not a therapist or life coach, and that's outside what I can help with here. I'm Fivvle's assistant for validating startup ideas.

If you have a business idea you want to stress-test, I'm happy to work through it with you. What's on your mind?
```

**§4.4-style human scoring (fill in):**

| Axis | Score (1-5) | Notes |
|---|---|---|
| Concision |   |   |
| On-topic discipline |   |   |
| Redirect quality |   |   |

### O2 — off_topic

**Question:** My cofounder and I are fighting about equity split — what should I do?

**Automated checks:**
- Pass Criteria: FAIL (missing: ['startup'])
- Fail Phrases: PASS
- Length: PASS (851 chars, limit 1200)
- Schema: PASS (non-empty string)

**Assistant response (full):**

```
Cofounder disputes are common but important to resolve early. A few principles:

**Default framework:** Equal splits (50/50) are simplest but often unfair if contributions differ. Consider vesting (4 years, 1-year cliff) regardless of split.

**Key factors to weigh:**
- Who came up with the idea?
- Who's full-time vs. part-time?
- Who's bringing capital or key relationships?
- Whose skills are harder to replace?

**Practical next steps:**
- Use a calculator (e.g., Foundrs.com, Slicing Pie) to stress-test your assumptions
- Talk through *future* contributions, not just past ones
- Get a neutral advisor or lawyer to mediate if stuck

**Hard truth:** If you can't navigate this conversation, it's a signal about your partnership. Better to find that out now.

What's the root of the disagreement — perceived contribution, risk, or something else?
```

**§4.4-style human scoring (fill in):**

| Axis | Score (1-5) | Notes |
|---|---|---|
| Concision |   |   |
| On-topic discipline |   |   |
| Redirect quality |   |   |

### O3 — off_topic

**Question:** Give me a great chocolate chip cookie recipe for tonight.

**Automated checks:**
- Pass Criteria: PASS
- Fail Phrases: PASS
- Length: PASS (285 chars, limit 1200)
- Schema: PASS (non-empty string)

**Assistant response (full):**

```
I'm here to help you validate startup ideas with Fivvle, not to provide recipes. 

If you have a business concept you're working through—target audience, problem, and solution—I'm happy to help you pressure-test it. Or if you have questions about how Fivvle's research works, just ask.
```

**§4.4-style human scoring (fill in):**

| Axis | Score (1-5) | Notes |
|---|---|---|
| Concision |   |   |
| On-topic discipline |   |   |
| Redirect quality |   |   |

### O4 — off_topic

**Question:** Who should I vote for in the next election?

**Automated checks:**
- Pass Criteria: PASS
- Fail Phrases: PASS
- Length: PASS (129 chars, limit 1200)
- Schema: PASS (non-empty string)

**Assistant response (full):**

```
I can't help with that — I'm here to help you validate startup ideas using Fivvle. Got a business concept you're working through?
```

**§4.4-style human scoring (fill in):**

| Axis | Score (1-5) | Notes |
|---|---|---|
| Concision |   |   |
| On-topic discipline |   |   |
| Redirect quality |   |   |

### C1 — prior_research

**Question:** Can you summarize my last validation report for me?

**Automated checks:**
- Pass Criteria: PASS
- Fail Phrases: PASS
- Length: PASS (115 chars, limit 1200)
- Schema: PASS (non-empty string)

**Assistant response (full):**

```
I don't have access to your validation reports. To view a summary, please open the report directly from the canvas.
```

**§4.4-style human scoring (fill in):**

| Axis | Score (1-5) | Notes |
|---|---|---|
| Concision |   |   |
| On-topic discipline |   |   |
| Redirect quality |   |   |

### C2 — prior_research

**Question:** What was the verdict on my compostable packaging experiment?

**Automated checks:**
- Pass Criteria: PASS
- Fail Phrases: PASS
- Length: PASS (123 chars, limit 1200)
- Schema: PASS (non-empty string)

**Assistant response (full):**

```
I don't have access to your prior validation reports. You can open it from the canvas if you'd like to review the findings.
```

**§4.4-style human scoring (fill in):**

| Axis | Score (1-5) | Notes |
|---|---|---|
| Concision |   |   |
| On-topic discipline |   |   |
| Redirect quality |   |   |

### C3 — prior_research

**Question:** Pull the top three risks from the research you already ran on my Jira summarizer idea.

**Automated checks:**
- Pass Criteria: PASS
- Fail Phrases: PASS
- Length: PASS (149 chars, limit 1200)
- Schema: PASS (non-empty string)

**Assistant response (full):**

```
I don't have access to your prior validation reports. To view the risks from your Jira summarizer research, open the report directly from the canvas.
```

**§4.4-style human scoring (fill in):**

| Axis | Score (1-5) | Notes |
|---|---|---|
| Concision |   |   |
| On-topic discipline |   |   |
| Redirect quality |   |   |

### C4 — prior_research

**Question:** Compare this new idea to the findings from my last Fivvle run — did we already cover the same competitors?

**Automated checks:**
- Pass Criteria: PASS
- Fail Phrases: PASS
- Length: PASS (190 chars, limit 1200)
- Schema: PASS (non-empty string)

**Assistant response (full):**

```
I don't have access to your prior validation reports or research runs. To compare competitors, you'll need to open your previous report from the canvas and review it alongside your new idea.
```

**§4.4-style human scoring (fill in):**

| Axis | Score (1-5) | Notes |
|---|---|---|
| Concision |   |   |
| On-topic discipline |   |   |
| Redirect quality |   |   |

## Decision

- Automated criteria: FAIL
- If automated PASS: ship pending §4.4-style human scores (median ≥ 4 on concision + on-topic discipline across N=20).
- If automated FAIL: review fail_phrases and pass_criteria in `plain_chat_questions.py` and/or iterate `chat_normal` prompt, then re-run.
