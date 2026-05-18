# Calibration Run: Reflector warm-up (Task F-1) — 2026-05-17 / executed 2026-05-18

**Phase:** Reflector (B3) + full five-phase research pipeline (end-to-end smoke)  
**Prompt version:** `reflector_query_refinement_v1` (plus `planner_v1`, `reader_v1`, `refinement_v1` / `refinement_v1_retry`, `synthesizer_v2`)  
**Anthropic balance at start (assumed checkpoint):** ~$4.64 remaining credit (see `docs/cost-ledger.md`; not re-verified immediately before this keystroke)  
**Tavily balance at start:** PAYG enabled (`ExternalAPICall.cost_usd` recorded for this run)  
**Ideas in calibration set:** **1** (single-idea warm-up only; procedure Steps 3–4 omitted by design)

---

## Ideas

1. **Target shape:** “Something to help freelancers be less lonely” — intentionally vague (no product, platform, or business model).  
2. **Submission note:** `POST /experiments` enforces `raw_idea.min_length=50` (`backend/app/schemas/experiment.py`). The exact 45-character prompt was **rejected with HTTP 422**. The successful run used a **minimal semantic padding** suffix (still vague) so the API would accept the payload. See `docs/calibration/runs/2026-05-17-reflector-warmup-stdout.txt` and “Anomalies” below.

---

## Idea 1: Freelancer loneliness — vague consumer angle

- **Status:** `RESEARCH_READY`
- **experiment_id:** `53724f06-cb83-4c8a-92bd-e493e994ac34`
- **Wall-clock (client smoke):** ~**560.74 s** (~9.3 min) — from `PIPELINE_WALL_SECONDS` footer in stdout capture; polling interval 8 s, terminal after poll 54/90.
- **DB `LLMCall.called_at` span (UTC):** `2026-05-18T05:21:38` .. `2026-05-18T05:30:48`
- **Anthropic cost (sum `LLMCall.cost_usd`, `experiment_id` scoped):** **$0.984777** (`n_llm=19`)
- **Tavily cost (sum `ExternalAPICall.cost_usd`, scoped):** **$0.528000** (`n_ext=33`)
- **Reflector-specific data:**
  - **`RESEARCH_REFLECTING` entered:** Yes (poll 8 onward; `research_reflecting_in_phases_completed=True`).
  - **`prompt_name=reflector_query_refinement_v1` rows:** **4** (matches four targeted `question_id`s).
  - **Refinement targeted `question_id`s:** **q1, q3, q4, q5** (from uvicorn structlog: four `reflector query refinement complete` lines).
  - **Refined queries emitted:** **3 per targeted question** (`refined_queries_count=3`), **12** Tavily task pairs; **12 succeeded, 0 failures** (`reflector partial re-search aggregate` log).
  - **`re_search_triggered`:** `True`; `questions_flagged_for_re_search=6`, `questions_scheduled_for_re_search=4`, `per_question_budget_exhausted_count=2`, `decision_method=rule_v1`.
  - **`citation_hydration_index` timing:** Built in orchestrator **after** Reflector merge (`build_citation_hydration_index(search_results)` on merged results). Reflector merge added material new Tavily payload (`per_question_new_tavily_hit_counts` peaked at **15** new hits for q1/q3/q4). Final report citations include domains/URLs consistent with that broader merged corpus (see “Reflector-specific observations”).
  - **Graceful degradation:** No Reflector exception surfaced; pipeline continued to `RESEARCH_SYNTHESIZING` and `RESEARCH_READY`. Matches ADR 0013 “never raises into orchestrator” intent for this path.
- **`ValidationReport` aggregates (smoke / API-facing):** `overall_recommendation='iterate'`, **`total_finding_count=20`**, **`total_citation_count=42`**.
- **Instrumentation oddity:** DB `validation_reports.reflection_loops_used` is **0** despite one refinement wave — likely a separate counter from “refinement waves used”; note for future wiring review (observation only).

### Reflector-specific observations

- **Did Reflector run?** Yes — sustained `RESEARCH_REFLECTING` phase; partial re-search and second-pass Reader on four questions; **`reflector phase complete`** with `total_partial_tavily_tasks_succeeded=12`.
- **Which ADR 0013 disjunct(s) fired?** Per-question trigger labels are emitted at **DEBUG** (`reflector signal snapshot`: `trigger_gap_note`, `trigger_sparse_atoms`, `trigger_mono_domain`). Local uvicorn log level for this run did not retain those lines. **Inference from INFO logs:**
  - **gap_note:** Strong — **six** reader completions logged `has_evidence_gap=True`; synthesizer logged `questions_with_gap_note=6`. This aligns with evidence-gap notes driving re-search.
  - **sparse_atoms:** Unlikely on first-pass extractions as logged — **all seven** questions had **`extracted_evidence_count` ≥ 3** (minimum q6 at 3; threshold is ≤2 atoms).
  - **mono_domain:** **Possible** for a subset (rule fires when ≥2 atoms share one domain), **not confirmed** without DEBUG snapshots.
- **Did refinement queries run through Tavily successfully?** Yes — **zero** failures in partial re-search aggregate.
- **Hydration after merge:** Orchestrator builds the hydration index **after** Reflector returns merged `search_results`. Empirically, citations include **Reddit + niche guides + marketplaces** (example domains in report: `reddit.com`, `leapers.co`, `investors.upwork.com`, `arc.dev`, …), consistent with Tavily-first evidence rather than generic filler only.
- **Orchestrator exceptions:** None attributed to Reflector; Reader logged quote-hallucination threshold events on **q2, q3, q7** during both passes — pipeline still completed.

### Quality assessment (informal vs rubric themes)

- **Citation quality:** Strong when present — claims tie to **specific URLs** (Reddit threads, freelance blogs, vendor pages) with titles and domains; example finding ties **Focusmate** critiques to multiple independent sources.
- **Specificity:** Mostly avoids empty platitudes; discusses **named products** (coworking apps, marketplaces) and **concrete user complaints**. Some executive framing still reads like synthesis across weak TAM quantification (see limitations).
- **Investigability / hallucination of specificity:** The refinement wave steered queries toward **coworking / isolation / community tools** without inventing a founder’s nonexistent product; remaining vagueness shows up honestly in **research_limitations** (missing TAM splits, no startup case studies for “loneliness” angle, no WTP signal).
- **Coverage:** Findings span **competition, distribution, community products, WTP gaps** — appropriate breadth for a deliberately underspecified idea.
- **Honesty:** **`research_limitations`** explicitly calls out unanswered quantitative and WTP questions rather than fabricating precision — good alignment with the honesty criterion.

### Anomalies observed

- **422 on first smoke attempt:** Exact user string (45 chars) tripped Pydantic **`min_length=50`** on `ExperimentCreate`. Documented; successful run used padded **`RAW_IDEA` (111 chars)** — see stdout timing footer.
- **`reflection_loops_used=0`:** Does not match intuitive “one refinement wave” language — logging/schema drift observation only.
- **Long synthesizer phase:** ~5.7 minutes logged (`latency_ms≈344275`), consistent with very large `prompt_tokens≈48733` / `completion_tokens≈17013` on **`synthesizer_v2`**.

---

## Overall phase quality assessment (warm-up scope)

### What worked

- Rule-based Reflector gate fired, capped to **four** questions, ran **four** successful structured refinement LLM calls, executed **twelve** Tavily tasks without failures, merged results, re-ran Reader on affected questions, and handed off to Synthesizer — **end-to-end path validated**.
- Tavily PAYG spend is now visible in **`ExternalAPICall`** for this experiment — cost ledger reconciliation is meaningful for external API for the first time in local calibration.

### What didn’t work / gaps

- **Disjunct forensics** require DEBUG logging or persisted decision payloads — operators cannot see **which** OR-branch fired from INFO alone.
- **Reader quote hallucination guard** tripped on multiple questions; quality concern for Reader calibration, separate from Reflector correctness.

### Open questions for the next iteration

- Should **`reflection_loops_used`** mirror Reflector refinement waves when `max_refinement_waves≥1`?
- Should **`POST /experiments`** accept calibrated ultra-vague prompts under length 50 for internal testing (separate product decision)?

---

## References

- Procedure template: `docs/calibration/procedure.md` (Steps 1–2 header + per-idea template; Steps 3–7 out of scope for this warm-up).
- ADR: `docs/adr/0013-reflector-decision-logic.md`
- Prior blocked attempt context: `docs/calibration/runs/2026-05-16-reflector-warmup-blocked.md`
- Audit trail log: `docs/calibration/runs/2026-05-17-reflector-warmup-stdout.txt`
