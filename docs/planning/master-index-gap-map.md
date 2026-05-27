# MASTER_INDEX — Vision-to-Engine Gap Map

**Purpose.** Translate the `MASTER_INDEX.docx` product vision (22 sections + 5 appendices, ~130 sub-analyses) into a build roadmap grounded in what the Fivvle research engine produces *today*. This is an internal planning artifact, not a user deliverable.

**How to read this.** Every section is scored on three axes:

- **Status** — `Produced` (engine emits this today), `Partial` (some underlying data exists but incomplete/stubbed), `Not built` (no research, schema, or synthesis targets this).
- **Stance** (per the agreed split) — `Sourced` (must be backed by a retrieved citation), `Inference` (LLM-reasoned from knowledge + web search, must carry an Appendix-E confidence label), or `Mixed`.
- **Quant/Chart** — whether the section yields chartable quantitative data, and if so the data's provenance and the confidence treatment its visual needs.

**Build-cost tiers.** `T1` = synthesis-only (new prompt + schema fields, no new data source). `T2` = moderate (new research questions + schema + synthesis, existing sources). `T3` = hard (requires a new external data source / integration the engine does not have).

---

## Engine ground truth (what exists today)

Current `ValidationReport` data areas: `research_questions`, `findings_per_question`, `competitors`, `reddit_signals` (stub), `search_trends` (wired to Google Trends but failing every run — never returned data), `news_signals`, `citations`, `clarity_score` (stub, never wired), `risks`, `market_summary`, `reflection_loops_used`.

Data sources: **Tavily** (working, solid) and **Google Trends via pytrends** (wired, flaky, currently 0 successful runs). No Crunchbase, no NAICS/industry-code lookup, no funding database, no regulatory database, no government-grant registry, no financial-data API. No agent frameworks (ADR 0004).

Implication: roughly 5–6 of 22 sections have any real engine output behind them today; the rest are greenfield.

---

## Section-by-section map

### Section 1 — Executive Summary
- **Status:** Partial. `market_summary` + risks + a verdict notion exist; the structured one-liner/problem/solution/segment/model breakdown and the opportunity/confidence scores do not.
- **Stance:** Mixed — summary is synthesis of sourced findings; opportunity/confidence scores are Inference.
- **Quant/Chart:** Opportunity score + confidence score are chartable (gauge / score bar). Both Inference → visuals must show confidence band, not a bare number.
- **Tier:** T1. Synthesis + a few schema fields; depends on §20 scoring existing.

### Section 2 — Idea Foundation Analysis
- **Status:** Partial. `RefinedIdea` (headline, one-liner, audience, value prop, risks) covers some of 2.1–2.2. Hidden-assumption mapping, founder-bias detection, founder-fit are Not built.
- **Stance:** Inference (bias detection, assumption confidence, founder-fit are model judgments; no external source).
- **Quant/Chart:** Assumption confidence levels chartable (low/med/high distribution). Inference → label as assumption-based.
- **Tier:** T1 for assumptions/bias (prompt + schema); founder-fit may need founder-intake data the product doesn't collect yet.

### Section 3 — Industry Identification & Classification
- **Status:** Not built.
- **Stance:** Mixed — industry *name*/lifecycle is Inference; NAICS/NIC/SIC codes are Sourced (must map to a real code registry, not hallucinate a number).
- **Quant/Chart:** Lifecycle stage chartable (stage marker). Low quant content.
- **Tier:** T3 for accurate code mapping (needs a NAICS/NIC lookup source — hallucinated codes are a trust hazard); T1 for lifecycle/characteristics as labeled inference.

### Section 4 — Problem Validation
- **Status:** Partial. `findings_per_question` + evidence atoms cover problem definition, severity, evidence sources. Frequency/urgency/economic-cost quantification and the problem-validation score are Not built.
- **Stance:** Sourced (evidence) + Inference (severity/urgency scoring, economic-cost estimate).
- **Quant/Chart:** Pain severity, frequency, problem-validation score → chartable (radar or score bars). Economic cost is Inference → confidence-labeled.
- **Tier:** T2. New research questions targeting frequency/cost + scoring synthesis.

### Section 5 — Market Demand Signal Analysis
- **Status:** Partial-but-blocked. `search_trends` (Trends) and `reddit_signals` are the intended sources — Trends has **never returned data**, Reddit is deferred indefinitely (Responsible Builder Policy). Buyer-intent / job-market / adoption proxies Not built.
- **Stance:** Sourced (this section is the engine's strongest *sourced quantitative* opportunity — IF Trends works).
- **Quant/Chart:** **The highest-value chart in the whole report.** Trends time-series → line chart, regional interest → map/bar, seasonality → seasonal plot. All genuinely sourced numeric data. This is the section where charts are real, not decorative.
- **Tier:** T2, gated on the open Trends reliability bug. Reddit-dependent sub-parts are T3+ (commercial API approval, deferred). Until Trends returns data once, this section's charts cannot be validated.

### Section 6 — Market Size Analysis (TAM/SAM/SOM)
- **Status:** Not built.
- **Stance:** Inference (top-down/bottom-up models from reasoning + web-sourced inputs where available). Assumption table is the load-bearing trust mechanism.
- **Quant/Chart:** Core quantitative section — TAM/SAM/SOM funnel, sensitivity tornado, scenario (conservative/base/aggressive) bars, CAGR projection. **All Inference** → every chart must visibly carry assumptions + confidence. A polished TAM funnel with no assumption disclosure is the single most dangerous artifact in the report.
- **Tier:** T2 (Inference-allowed under split). Heavy schema (assumption tables, sensitivity ranges) + careful prompt discipline. Quantitative-but-inferred → confidence treatment is mandatory, not optional.

### Section 7 — Customer Analysis (ICP / personas)
- **Status:** Not built (RefinedIdea has a coarse target_audience only).
- **Stance:** Mixed — personas/journey Inference; willingness-to-pay signals Sourced if found.
- **Quant/Chart:** WTP signal distribution, switching-cost/adoption-barrier scores → chartable, mostly Inference.
- **Tier:** T1–T2. Mostly synthesis + schema.

### Section 8 — Competitor Intelligence ★ (recommended first vertical slice)
- **Status:** Partial. `competitors` is produced today. The matrix (§8.4: pricing/features/funding/geography/weakness), feature-gap, white-space, complaint-mining, moat, saturation score are mostly Not built.
- **Stance:** Sourced (competitor existence, pricing, features, complaints from web) + Inference (white-space, moat, saturation score).
- **Quant/Chart:** Competitor positioning map (2-axis scatter), feature-gap matrix (heatmap), saturation score (gauge). Positioning/features are Sourced → charts are real. **Closest section to a fully-sourced chart in the report.**
- **Tier:** T2. Builds directly on existing `competitors` output. Pricing/funding may need a source (T3) or labeled-inference fallback (T2). **This is the cleanest vertical slice to prove the full research→schema→synthesis→quant→chart pattern.**

### Section 9 — Product / MVP Analysis
- **Status:** Not built.
- **Stance:** Inference.
- **Quant/Chart:** Complexity score, time-to-MVP estimate, MoSCoW prioritization → chartable, Inference.
- **Tier:** T1.

### Section 10 — Team Requirements
- **Status:** Not built.
- **Stance:** Inference (+ Sourced for salary/cost benchmarks if a source is added).
- **Quant/Chart:** Team cost estimate, hiring-roadmap timeline → chartable; cost is Inference unless salary data sourced.
- **Tier:** T1 inference; T3 if real salary benchmarks required.

### Section 11 — Business Model Analysis
- **Status:** Not built.
- **Stance:** Inference (CAC/LTV/margin modeling) + Sourced (comparable pricing where found).
- **Quant/Chart:** Unit economics, CAC/LTV, margin, monetization score → all chartable, mostly Inference. Confidence labels mandatory.
- **Tier:** T2.

### Section 12 — Financial Forecast Framework
- **Status:** Not built. (Doc explicitly says "not fake numbers — scenario-based" — aligns with Inference + assumption discipline.)
- **Stance:** Inference (scenario models, not point predictions).
- **Quant/Chart:** Revenue/cost scenarios, burn, breakeven, sensitivity, gross-margin → the most chart-dense section. **All Inference.** Scenario bands, not single lines. Confidence/assumption disclosure is the whole game here.
- **Tier:** T2. Heavy schema + the strongest case for visible confidence treatment.

### Section 13 — Resource & Infra Cost Analysis
- **Status:** Not built.
- **Stance:** Inference (+ Sourced for cloud/tool pricing if a source is added).
- **Quant/Chart:** Cost breakdown (stacked bar), MVP vs production scale → chartable, Inference.
- **Tier:** T1–T2.

### Section 14 — Regulatory / Compliance Analysis
- **Status:** Not built.
- **Stance:** Sourced strongly preferred — regulatory claims are high-liability; labeled-inference is risky here even under the split. Recommend treating this as Sourced-only or heavily disclaimed.
- **Quant/Chart:** Compliance-burden score, risk map → chartable, but content is qualitative.
- **Tier:** T3 (needs a regulatory source) or T1 with strong "not legal advice" disclaimers. Product/legal decision.

### Section 15 — Government Schemes / Grants / Incentives
- **Status:** Not built.
- **Stance:** Sourced (specific grants/eligibility must be real; hallucinated grants are actively harmful to a founder acting on them).
- **Quant/Chart:** Low quant. Eligibility matrix.
- **Tier:** T3. Needs a grant/scheme registry or reliable web-sourcing with verification. High trust-stakes — do not allow inference.

### Section 16 — Funding Landscape Analysis
- **Status:** Not built.
- **Stance:** Sourced (sector funding trends, comparable raises, ticket sizes are factual claims) + Inference (investor-fit, fundability score).
- **Quant/Chart:** Sector funding trend (time-series), comparable-raise bars, ticket-size ranges, fundability gauge. Funding figures Sourced → charts real IF a source exists; otherwise labeled-inference.
- **Tier:** T3 for real comparables (needs Crunchbase-class source); T1 for fundability score as inference.

### Section 17 — Go-to-Market Analysis
- **Status:** Not built.
- **Stance:** Inference.
- **Quant/Chart:** Channel-fit scoring, growth-loop diagrams → mostly qualitative + some scores.
- **Tier:** T1.

### Section 18 — Strategic Frameworks (SWOT / PESTEL / Porter)
- **Status:** Not built.
- **Stance:** Inference (these are analytical frameworks, inherently model-reasoned).
- **Quant/Chart:** SWOT quadrant, Porter five-forces radar, positioning map → chartable as framework visuals (not data charts). Inference, labeled.
- **Tier:** T1. Pure synthesis from existing findings — among the cheapest sections to add and a good early win after the slice.

### Section 19 — Risk Engine
- **Status:** Partial. `risks` exists. The 7-category breakdown + severity matrix are Not built.
- **Stance:** Inference (risk identification + severity scoring).
- **Quant/Chart:** Risk severity matrix (likelihood × impact heatmap) → strong chart, Inference-scored.
- **Tier:** T1. Restructure existing risks output into categories + scores.

### Section 20 — Opportunity Scoring Engine
- **Status:** Not built (`clarity_score` is a never-wired stub).
- **Stance:** Inference (10 weighted dimensions: problem severity, demand, urgency, competition, founder-fit, feasibility, monetization, scalability, defensibility, fundability).
- **Quant/Chart:** **The report's signature visual** — 10-dimension radar + composite score gauge. Fully Inference → must show per-dimension confidence. Feeds §1 exec summary.
- **Tier:** T1 in mechanics (weighted formula + synthesis), but **depends on most other sections existing** to score them honestly. Build late, not early — scoring sections that aren't built yet would be fabrication.

### Section 21 — Action Roadmap
- **Status:** Not built.
- **Stance:** Inference.
- **Quant/Chart:** Timeline (30/90-day Gantt-style), experiment list → mostly qualitative.
- **Tier:** T1. Synthesis from the rest of the report.

### Section 22 — Final Verdict
- **Status:** Partial. A verdict notion exists in current synthesis.
- **Stance:** Inference (go/no-go judgment built on everything above).
- **Quant/Chart:** Verdict badge, upside/risk callouts.
- **Tier:** T1. Depends on §20.

---

## Appendices

### Appendix A — Methodology Notes
- **Status:** Not built. **Critical enabler.** Per-insight: data source, method, assumptions, confidence, freshness timestamp.
- **Tier:** T1 mechanically, but it requires every other section to *emit* provenance metadata — so it's a cross-cutting schema requirement, not a standalone section. **Design this contract early** (it's how the split stance becomes enforceable).

### Appendix B — Source Index
- **Status:** Produced. `citations` already exists and maps directly here.
- **Tier:** T1. Mostly a rendering of existing citation data.

### Appendix C — Raw Data Tables
- **Status:** Partial. Whatever sourced quant exists (Trends data, competitor raw) renders here.
- **Tier:** T1, grows with each quant section.

### Appendix D — Charts / Visuals
- **Status:** Not built. This is the **chart layer**, dependent on quantitative data existing first.
- **Tier:** T2 as a rendering capability, but per-chart cost lives in each data section. **Charts cannot precede their data.**

### Appendix E — AI Confidence Disclosure
- **Status:** Not built. **The trust backbone of the split stance.** Per-section: evidence-backed / inference-based / forecast-based / assumption-based.
- **Tier:** T1 mechanically, but — like Appendix A — it's a cross-cutting contract every section must feed. **Build the confidence-label schema before scaling sections**, or you'll retrofit it across 22 sections later.

---

## Cross-cutting findings

1. **Three sections carry the report's quantitative credibility, and two of three are Inference.** §5 (Demand, Sourced — but Trends is broken), §6 (Market Size, Inference), §12 (Financials, Inference), §20 (Scoring, Inference). The split stance makes this workable *only if* Appendix E confidence labeling is built first and rendered *on the charts themselves*, not just in prose.

2. **Charts cannot precede data.** Appendix D is a rendering capability; each chart's real cost is in producing trustworthy numbers in its source section. Building a chart library before the quant schema would plot fabrications.

3. **Two cross-cutting contracts gate everything: Appendix A (methodology/provenance) and Appendix E (confidence labels).** These are not "late appendices" — they are the schema discipline that makes the split stance enforceable. Design them before scaling sections, or pay a 22-section retrofit.

4. **Trust-critical Sourced-only sections** (no inference allowed): §14 Regulatory, §15 Grants, §3 industry codes, §16 funding comparables. Hallucinated content here doesn't just lower quality — a founder acting on a fake grant or a wrong regulation is real harm. These need real data sources (T3) or hard disclaimers.

5. **The engine's one genuinely-sourced quantitative win is blocked.** §5 Trends is the only place with real numeric sourced data today, and it has never successfully returned. Fixing the Trends reliability bug unblocks the report's most defensible chart — high leverage.

---

## Recommended build order

1. **Cross-cutting contracts first** — Appendix A (provenance metadata) + Appendix E (confidence labels) as schema additions every future section emits. Cheap now, ruinous to retrofit.
2. **Vertical slice: §8 Competitor Intelligence** — closest to shippable, builds on existing `competitors`, has the cleanest *sourced* chart (positioning map). Proves research → schema → synthesis → quant → chart end-to-end and becomes the replication template.
3. **Unblock §5 Trends** — fixes the report's best sourced chart; already an open engine bug.
4. **Cheap T1 synthesis sections** — §18 frameworks, §19 risk engine, §2 assumptions/bias. High perceived value, no new data sources.
5. **Inference quant sections with confidence discipline** — §6, §11, §12 — only after Appendix E is enforced.
6. **§20 scoring + §1/§22 verdict** — late, because honest scoring requires the scored sections to exist.
7. **T3 sourced sections** — §3 codes, §14 regulatory, §15 grants, §16 funding — each gated on a new data-source integration; sequence by product priority.

---

## What this map deliberately does NOT do

- It does not build a renderer. Most sections would render empty today.
- It does not expand the schema to 130 fields. The current `ValidationReportDraft` already strains Sonnet (the reason the Haiku swap failed on `max_length` overruns, 2026-05-27); a 130-field monolith would blow context and cost. Sections must be built incrementally, likely as separable sub-schemas.
- It does not produce a design mock. That is the frontend north-star for *after* the vertical slice proves the shape — building it now would make the vision look closer than it is.
