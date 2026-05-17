# Eval Set Discipline — Planning Document

**Status:** APPROVED — co-founder reviewed, decisions resolved, implementation prompt pending.
**Phase:** Pre-launch research-engine quality gate (discipline precedes automation).
**Related ADRs to write:** ADR **0014** — Eval Set Discipline (see §12 for sequencing caveat if ADR slots 0014–0015 are claimed first by another in-flight artifact).
**Authors:** Cursor Composer (planning artifact); human co-founder (approval for v2+).

---

## 1. Problem Statement

Calibration sessions to date (`docs/calibration/runs/`) are valuable **warm-ups**: they prove a specific pipeline run can succeed on **one founder idea at a time**. They **do not** answer whether the system generalizes across the **distribution** of founder ideas Fivvle will see after launch.

**One-off runs don’t substitute for an eval portfolio.** Passing on two or three accidentally familiar shapes (often B2B- or Tavily-shaped) hides silent failure modes on consumer, marketplace, regulated, long-tail Reddit-only, or intentionally vague submissions. Shipping without eval discipline carries **asymmetric downside**: founders experience “empty confidence” reports; the team loses weeks re-learning that quality was **narrow** rather than **broad**.

**Product contract.** Founders only pay when reports are **useful**. Usefulness cannot be delegated to vibes. Eval discipline defines **measurable** expectations (coverage of risks, citations, honesty on thin evidence, cost and latency envelopes) before friends-and-circle launch — so prompt engineering remains the differentiator **and** is **measured repeatedly**, not celebrated from a handful of anecdotes.

This document defines **repeatable production readiness**; **implementation** of scripts, migrations of existing fixtures, and the **ten** curated IDs are **out of scope** here (see §14).

---

## 2. Constraints (Non-Negotiable)

The following rules apply to this discipline and any future automation derived from it.

| Source | Constraint |
| --- | --- |
| `.cursorrules` — Eval methodology | Maintain an eval set in `backend/tests/eval/` of **10–20** founder ideas with **tiered gold-standard outcomes** (`GoldStandard` + `rubric.py`; §4) (fixture IDs **§14**). |
| `.cursorrules` — Eval methodology | **Run eval before shipping any prompt change** (planner, reader, reflector, synthesizer, search adaptation). |
| `.cursorrules` — Quality discipline | **Prompt engineering is the differentiator**; eval is how that differentiation is **measured** over time — not displaced by architectural churn. |
| `AGENTS.md` — Logging hygiene | Gold-standard artefacts may embed **example** founder prose. Treat synthetic eval ideas **as-if real** for privacy discipline: **never** log eval idea text verbatim in **production** telemetry. Eval execution is **CI/dev-local** priority; structured logs remain aggregate/safe-metadata only where idea text could leak. |
| `AGENTS.md` — Database / Functions | Production research persists **INSERT** paths for **`LLMCall`** and **`ExternalAPICall`** (Cloud Function IAM). **`test_eval_data_integrity.py`** does **not** invoke the orchestrator — it validates fixtures only; **confirmation** that a future **`run_eval.py`** persists the same audit rows awaits implementation. Until otherwise designed, assume **eval runs that hit real APIs SHOULD write audit rows** for cost and safety parity with `.cursorrules` / `AGENTS.md` expectations. |
| `AGENTS.md` — Circuit breakers | Eval runs count toward experiment-level safeguards when tied to real experiment rows; **`run_eval.py` design MUST NOT** circumvent cost-based halts (`3×` target, `30` LLM calls) in a way that masks runaway loops. Prefer **explicit eval experiment_id prefix / synthetic attribution** so ops can filter dashboards (§10). |
| Budget — pipeline economics | **Full eval passes are expensive.** Planning assumption: roughly **10 ideas × ~US$1.62 per full pipeline invocation** raw API spend order-of-magnitude (align with calibrated multi-phase runs — supersede stale “per-idea \$0.30–\$0.80” README figures once B5 is steady). Cadence MUST respect envelopes; `.cursorrules` keeps **mean run cost toward ~\$1.50** as the product north star — eval interprets regressions vs that target (§5–§7). |
| `ADR 0001` — Modular monolith | Eval artefacts and runners live **inside the backend repo** (`backend/tests/eval/`, `backend/scripts/`), **not** a separate eval microservice. |

---

## 3. Eval Set Composition

### 3.1 Size target

`.cursorrules` allows **10–20** ideas. **v1 target:** **10** ideas — the **current curated set** in `backend/tests/eval/ideas.py`, already enforced by `test_eval_data_integrity.py`. **Floor = 10:** do not shrink below this while the integrity tests and gold fixtures assume ten entries. **Expansion to 12–20** is allowed when a **category bucket is underweight** (or when multi-source calibration demands more Reddit- / Trends-shaped coverage), but it is **not** required for v1 approval.

### 3.2 Category buckets

**Six buckets** fit the **existing ten** ideas without forcing an artificial twelfth slot: **four buckets at 2 ideas**, **two buckets at 1 idea** (underweights called out for future expansion).

| Bucket | Why it belongs | Failure mode surfaced if missing | v1 ideas (`ideas.py` id) — count |
| --- | --- | --- | --- |
| **B2B SaaS / professional tools** | Tavily and trade press excel here — the “easy” control bucket; includes the **deliberately vague** honesty check (`vague-ai-productivity`) tagged `b2b-saas`. | Over-weighting hides consumer/marketplace gaps; missing vague case loses **fabrication** detection. | `slack-hr-bot`, `vague-ai-productivity` — **2** |
| **Consumer & creator economy** | Everyday and **creator** ideas where community and adoption narratives dominate. | False confidence from generic SEO; misses affiliate / audience dynamics. | `fitness-accountability`, `newsletter-affiliate` — **2** |
| **Marketplace / two-sided platforms** | Liquidity, trust, and two-sided dynamics — not single-vendor SaaS stories. | One-sided SaaS metaphors substitute for marketplace risks. | `video-editor-marketplace`, `mechanic-marketplace` — **2** |
| **Developer tools / technical products** | Docs-heavy, HN-shaped discourse; different specificity bar than HR SaaS. | Shallow tool tables; missed ecosystem / integration risks. | `observability-timeline` — **1** (expand first when growing the set) |
| **Regulated / vertical specialist** | Healthcare and fintech move slowly; easy to **over-claim** regulatory certainty. | Unearned decisive tone; fabricated compliance detail. | `tax-loss-harvesting`, `medication-adherence` — **2** |
| **Social impact / civic** | Non-profit / migration-adjacent framing; **evidence and liability** patterns differ from pure commercial SaaS. | Missed stakeholder and trust dynamics typical of impact ideas. | `visa-deadline-tracker` — **1** (expand second when growing the set) |

Rationale **per bucket** stays in the **Why / Failure mode** columns. **v1 total = 10.** When expanding toward 12–20, **add ideas that shore up the two single-idea buckets** before doubling down on B2B.

### 3.3 Curation method

**v1 authority:** The **ten** IDs are **already chosen** and validated in-repo; **replacements** remain **human co-founder** decisions (idea text itself stays **§14 exclusions** for this planning doc).

**Governance:**

- Publish a **coverage checklist** against the table above before freezing each **eval set version**.

- Any **replacement or addition** after v1 MUST pass a **balance review** (“Did we silently slide back to mostly `b2b-saas` because it passes easiest?”).

- **Anti-pattern:** Letting Tavily-strong ideas crowd out Reddit- or Trends-shaped cases **after multi-source lands** invalidates historical baselines — treat deliberate rebalance like a semantic version bump (`EVAL_SET_SCHEMA v2`).

---

## 4. Gold-Standard Reports — How Built

### 4.1 Hybrid gold model (three tiers)

Eval uses a **hybrid** — not a single artefact — so measurement stays **stable** without **full-report JSON diffing**.

**Tier 1 — `backend/tests/eval/gold_standards.py` (`GoldStandard`)**  
The **primary authored gold**: human-written **`must_surface`**, **`should_surface`**, and **`must_not_invent`** strings. This is the **correct** granularity for “did the produced `ValidationReport` **mention** this competitor, risk, or phrase?” via **substring / text-match** (and related checks), without requiring the model to reproduce any fixed wording. **`gold_standards.py` is canonical v1 authorship** — not interim, not legacy.

**Tier 2 — `backend/tests/eval/rubric.py` (five 1–5 criteria)**  
Human **qualitative** grading (`citation_quality`, `specificity`, `investigability`, `coverage`, `honesty`). **`rubric.py` is canonical v1 for Tier 2.** Used for **weekly / pre-release human review only** — **mandatory averaged grading pre-release**; **optional weekly** when bandwidth allows. **Not** wired to automated per-commit pass/fail.

**Tier 3 — Gold-independent objective metrics**  
Derived from **pipeline validity and counters** only: e.g. **`RESEARCH_READY` rate**, **citation hallucination rate**, **mean cost**, **latency**, **Reader URL hallucination guard trip rate**, **schema / structural validity** of phase outputs. **No gold file required.** **Automated per-commit gates** (including orchestration **smoke** — §6) use **Tier 3 only** for pass/fail.

**Explicitly out of scope for v1:** hand-authoring **full `ValidationReport` JSON** per idea as “gold.” That path is **enormous effort**, **brittle** under natural LLM phrasing drift, and invites **gold-vs-actual diff hell**. The product does **not** need exact-shape diffing as a measurement strategy.

### 4.2 Authoring rules (Tier 1 + Tier 2)

- **Tier 1:** **Human-authored only** in `GoldStandard`. LLM-authored “gold” **collapses measurement into self-reference**. Keep **must** items **specific enough to test** (named entities, concrete risks) but **phrase-agnostic** in how the report satisfies them.

- **Tier 2:** Graders use **`rubric.py`** definitions; increment **`RUBRIC_VERSION`** when criterion text changes so scores stay comparable.

### 4.3 Storage layout

**Canonical layout (existing modules):**

| Module | Role |
| --- | --- |
| `backend/tests/eval/ideas.py` | `EvalIdea` rows: `raw_idea`, `refined_idea`, `domain`, `notes`. |
| `backend/tests/eval/gold_standards.py` | `GoldStandard` per `idea_id` (Tier 1). |
| `backend/tests/eval/rubric.py` | Scoring definitions (Tier 2). |

`EvalIdea.notes` continues to carry **per-idea rationale**; no separate per-idea directory tree is required.

### 4.4 Scope realism & updates (Tier 1)

`must_surface` / `should_surface` define a **floor** of themes and entities, **not** an exhaustive report spec. **Creativity above the floor is fine** if citations and honesty hold.

**Update policy:**

- If the Synthesizer surfaces a **clearly correct** theme absent from Tier 1 strings, **extend `GoldStandard`** with a normal commit message tagging the reason.

- If **one idea’s** `GoldStandard` needs **>2–3 updates per quarter**, treat it as a **process smell** — authors may be **chasing the model** instead of **defining product truth ahead of it**; escalate to co-founder review.

---

## 5. Success Metrics — Per Phase + Pipeline Level

Each metric below lists its **tier** (§4): **Tier 1** = substring / text coverage vs `gold_standards.py`; **Tier 2** = human rubric; **Tier 3** = objective, gold-free pipeline metrics.

**Thresholds:** **Hard / Soft** behave as before for **launch** and **trend** judgment (§7). **Additional rule:** automated **per-commit** pass/fail (full eval before prompt merge, and orchestration smoke in §6) may treat **Tier 3** metrics as machine gates only. **Tier 1** metrics feed **weekly automation** (coverage %) and **investigation**, not the same binary bar as Tier 3 hallucination checks. **Tier 2** never automates pass/fail.

### 5.1 Planner

| Metric | Tier | Notes | Threshold type |
| --- | --- | --- | --- |
| Question quality vs gold risk categories | **1** | Planner output vs **expected risk dimensions** encoded in Tier 1 strings / idea notes; **5–7** questions; **no duplicate** intent; `search_queries` **valid** where checked. | **Soft** (weekly / trend; pre-release aggregate review) |
| `search_queries` structural validity | **3** | Parser + schema pass; matches planner contract. | **Hard** |

### 5.2 Searcher

| Metric | Tier | Notes | Threshold type |
| --- | --- | --- | --- |
| Source diversity per question | **3** | **Tavily** ≥ **N** usable results (config default); post–multi-source: **Reddit** / **Trends** participation ≥ **N** where applicable (exact **N** set in implementation). | **Hard** on sustained zero-signal; **Soft** on marginal dips |
| Failure / skip rate | **3** | Rate-limits and flakes logged per `.cursorrules` degradation rules. | **Soft** trend; spike → investigation |

### 5.3 Reader

| Metric | Tier | Notes | Threshold type |
| --- | --- | --- | --- |
| Extraction count per question | **3** | Non-empty evidence where Tavily / merged corpus provides material. | **Soft** |
| URL hallucination guard trip rate | **3** | Fabricated `source_url` vs provided corpora. | **Hard** **0%** run-level policy (aggregate trip rate §7) |
| Quote substring guard trip rate | **3** | Paraphrase mislabelled as quote. | **Soft** **<10%** per Reader design unless calibration revises |
| `evidence_gap_note` rate | **3** | Thin-evidence signalling frequency (count-based). | **Soft** |

### 5.4 Reflector

| Metric | Tier | Notes | Threshold type |
| --- | --- | --- | --- |
| Trigger rate per disjunct | **3** | `gap_note`, `sparse_atoms`, `mono_domain` (per agreed instrument names). | **Soft** baseline band |
| Refinement query LLM cost | **3** | Spend on conditional second wave. | **Soft** |
| Conditional improvement rate | **3** | Second wave increases **grounded** evidence count / coverage for the same question. | **Soft** |

### 5.5 Synthesizer

| Metric | Tier | Notes | Threshold type |
| --- | --- | --- | --- |
| Report LLM cost | **3** | Phase token spend. | **Soft** |
| Citation count | **3** | Minimum viable density per `.cursorrules` non‑negotiable citations. | **Hard** |
| Citation hallucination rate | **3** | URL not in allowed evidence sets. | **Hard** **0%** |
| Competitor / theme coverage vs `must_surface` | **1** | Text-match coverage vs **Tier 1** strings (e.g. competitor names, required themes). | **Soft** (WoW trend; see §7.2) |
| Finding count | **3** | Within schema and product expectations. | **Soft** |

### 5.6 Pipeline-level

| Metric | Tier | Notes | Threshold type |
| --- | --- | --- | --- |
| `RESEARCH_READY` rate | **3** | % of eval ideas reaching terminal success. | **Hard** **≥95%** (§7.1) |
| Mean / p90 / p95 **cost** per run | **3** | `.cursorrules` ~**\$1.50** mean target. | **Hard** mean **>\$1.80** blocks (§7.1); **soft** drift below target without quality loss is **good** |
| Mean / p90 / p95 **latency** per run | **3** | `.cursorrules` **2–4 min** typical envelope. | **Soft** p95 **>5 min** investigation (§7.2) |
| Tier 1 **coverage** rate | **1** | % of **must_surface** / optional **should_surface** checks satisfied (automated substring policy TBD in `run_eval.py`). | **Soft** **−10 pp WoW** triggers review (§7.2) |

### 5.7 Rubric aggregate (Tier 2 — human only)

| Metric | Tier | Notes | Threshold type |
| --- | --- | --- | --- |
| **Per-criterion scores (1–5)** | **2** | **`rubric.py`** — `citation_quality`, `specificity`, `investigability`, `coverage`, `honesty`. | **Human** — weekly optional; **mandatory** averaged review **pre-release**; **not** a CI pass/fail |

---

## 6. Cadence — When Eval Runs

| Trigger | Scope | Tiers exercised | Rationale |
| --- | --- | --- | --- |
| **Every prompt change** (any phase affecting model instructions or schema coupling) | **Full** eval **before merge** (per `.cursorrules`) — default **10** ideas; **≥1** full pass per change author may be batched if co-founder approves batching policy later. | **Tier 3** machine gates (required) + **Tier 1** coverage where automated in `run_eval.py` (recommended same run; Tier 1 not sole per-commit binary). | Catches **hallucination**, **schema drift**, **cost** immediately without human rubric latency. |
| **Every commit** touching `research_engine` / `research_phase_mapping` / orchestration services affecting behaviour | **Smoke subset** **3–4** ideas (rotate across buckets **deterministically**). | **Tier 3 only** for automated pass/fail — no Tier 1 substring suite required on every orchestration tweak. | Fast signal without full **\$** on every non-prompt commit. |
| **Weekly** | **Full 10-idea** run; log summary under `docs/calibration/runs/` (pattern §8). | **Tier 3** + **Tier 1** (automated coverage % vs `gold_standards.py`). **Tier 2** optional if bandwidth. | **Cost trends**, **latency drift**, **theme coverage** stability. |
| **Pre minor release / launch milestone** | **Full 10** + **human read** of markdown summary + spot-check artefacts. | **Tier 3** + **Tier 1** + **Tier 2** (**mandatory** human `rubric.py` grading on the run outputs). | **Launch gate** — human judgment on quality dimensions machines under-measure. |

**Metric class mapping:** **Orchestration smoke** → **Tier 3 only** (§4). **Weekly + full pre-merge prompt runs** → **Tier 3** + **Tier 1** (`gold_standards.py` substring coverage). **Pre-release** adds **Tier 2** (mandatory human `rubric.py` grading) on top of Tier 3 + Tier 1. **Tier 2** weekly remains **optional** when bandwidth allows.

---

## 7. Failure Handling — Launch Decisions

### 7.1 Hard fail (any blocks launch until resolved)

- **`RESEARCH_READY` rate <95%** on the frozen eval set.

- **Citation hallucination rate >0%** (any fabricated URL in final `ValidationReport`).

- **Mean full-run cost >\$1.80** on eval (buffer over **\$1.50** target).

- **URL hallucination guard** trips on **>5%** of eval invocations (aggregate across ideas in the run — exact denominator defined in `run_eval.py` spec).

### 7.2 Soft fail (investigate; may not block if explained)

- Gold coverage drops **≥10 percentage points** week-over-week.

- **p95 latency >5 minutes** sustained across two weekly runs.

- Reflector **trigger rate** spikes outside an agreed baseline band (suggests Reader or Planner regression).

### 7.3 Decision authority

**Human co-founder** calls launch readiness. **AI agents** surface diffs and metrics; they **do not** approve release.

### 7.4 Recovery paths

1. **Revert** offending prompt / merge.

2. **Conscious threshold relaxation** — requires **written rationale**; if material, pair with **ADR** amendment.

3. **Fix forward** with new prompt or retrieval change + **re-run full eval**.

---

## 8. Tooling — Scripts, Dashboards, Data

### 8.1 `backend/scripts/run_eval.py` (to build)

Responsibilities:

- Orchestrate **N** ideas through the **same** backend pipeline path as production (ADR 0009 dispatcher compatibility).

- Emit **timestamped** output root: `docs/calibration/runs/eval-<timestamp>/`.

- Produce **per-idea JSON** (actual vs expected, metrics slice, pass/fail bits).

- Produce **`summary.csv`** aggregating headline metrics.

- Emit **auto-generated `README.md` or `summary.md`** in that folder: top-line metrics, failures, links to per-idea artefacts.

### 8.2 Storage policy

- **Human summaries** and **CSV** may be **git-tracked** if small.

- **Large per-idea blobs** (full JSON reports, raw API traces) — **gitignore** by default **or** upload to **GCS** with link in summary (pick one in implementation; default recommendation: **gitignore heavy**, keep **lean** `.md` + `.csv`).

### 8.3 Relationship to existing tests

`backend/tests/eval/test_eval_data_integrity.py` — **structural** tests only, **CI-safe without API keys**. **`run_eval.py`** is **operational** and **not** pytest’s role; do **not** conflate them.

---

## 9. Calibration Integration — `docs/llm-schema-calibration.md`

- Every eval run **aggregates** DEBUG **field-length** observations (e.g. `planner_field_lengths` pattern already noted in `docs/llm-schema-calibration.md`) into **fresh max / p95** tables.

- Eval’s **variety** surfaces **outliers** faster than one-off warm-ups on a single idea shape.

- **Policy:** After this discipline lands, **eval is the canonical statistical input** for **cap = max(observed) + 10–15%** decisions; **ad-hoc warm-ups** remain for **targeted debugging only**, not primary cap authority.

---

## 10. State Machine Integration

**None required for correctness.** Eval hits the **same pipeline** and **observes** status transitions; it does not fork the `ExperimentStatus` graph.

**Recommended:** synthetic **`experiment_id` prefix** and/or dedicated **`user_id`** for eval rows so **`LLMCall` / `ExternalAPICall` / admin cost views** can **filter** eval spend from founder production telemetry **without** disabling inserts.

---

## 11. Files to Create / Modify

| File | Action | Notes |
| --- | --- | --- |
| `backend/scripts/run_eval.py` | **New** | Orchestrator CLI; output under `docs/calibration/runs/eval-<timestamp>/`; implements **Tier 3** gates + **Tier 1** substring coverage helpers reading existing `gold_standards.py`. |
| `backend/tests/eval/expectations.py` (or equivalent) | **New** | Shared **Tier 3 threshold constants** + Tier 1 text-match helpers (optional extraction for runner vs pytest). |
| `docs/calibration/runs/eval-<timestamp>/` | **Pattern** | Timestamped outputs; heavy artefacts likely gitignored. |
| `docs/llm-schema-calibration.md` | **Modify** | Elevate eval harvest to **primary** observed-max source. |
| `docs/cost-ledger.md` | **Modify** | Separate **Eval** subsection or tags so production burn isn’t confounded (§13). |
| `docs/planning/eval-set-discipline.md` | **This document** | v2 APPROVED. |
| Optional ADR | **New** | §12 — formalizes gate for posterity. |

---

## 12. ADR Stubs Required

**ADR 0014 — Eval Set Discipline** (or next free index — see header caveat)

- **Context:** Pre-launch quality must be **repeatable**, not ad-hoc warm-ups.

- **Decision:** **10-idea** curated eval set (**v1 floor**); **hybrid gold** — Tier 1 **`GoldStandard`** strings + Tier 2 **`rubric.py`** human grades + Tier 3 objective gates (**no** full-`ValidationReport` JSON gold; §4); **mandatory** eval before prompt ships; **weekly** full runs; **hard** Tier 3 thresholds **block** launch.

- **Consequences:** Prompt iteration slows when quality drops — **intentional**; adds **\$** and **human review** time; enables **defensible** founder trust.

- **Reasoning summary:** Prompt work is the moat — **measuring** it is non-optional per `.cursorrules`.

---

## 13. Calibration Obligations

| Obligation | Owner / sink |
| --- | --- |
| **Schema caps** — aggregate length telemetry from eval into `docs/llm-schema-calibration.md`. | Automation in `run_eval.py` post-process + periodic human tidy. |
| **Cost ledger** — log eval spend distinctly in `docs/cost-ledger.md` (session tag `eval-weekly`, `eval-pre-release`, etc.). | Prevents **false alarms** on founder COGS dashboards. |
| **Gold drift counter** — track **gold file commits** per quarter; spike triggers process review (§4.4). | Lightweight `CHANGELOG` table or git query — implementation choice. |

---

## 14. What This Document Does NOT Cover

- Replacing or rewriting the **10 specific** curated founder idea payloads in-repo (`ideas.py` texts are **fixture data**, not re-decided here).

- **Production** observability / Sentry / billing dashboards (eval is **dev/CI-first**; synthetic IDs only reduce noise — they don’t replace prod monitoring).

- **Multi-prompt A/B** within one eval matrix (v1 evaluates **one** frozen prompt-set at a time).

- **Continuous training** or dataset collection for model fine-tuning (not in scope; fixed external models).

- **Implementation sequencing / commit plan** for `run_eval.py`, `expectations.py`, and calibration/cost-ledger wiring (§11).

---

## 15. Decisions and Rationale + Open Questions

### 15.1 Decisions (v1 recommendations)

| Decision | Choice | Rationale |
| --- | --- | --- |
| Eval set size | **10** (v1 floor; **12–20** when buckets need it) | Matches **existing** curated set + integrity tests; expansion only with bucket-balance rationale + budget sign-off. |
| Gold authorship | **Human-only** (Tier 1 strings + Tier 2 rubric) | Prevents self-referential “pass by construction.” |
| Gold strictness | **Tier 1 substring floor** (+ Tier 3 integrity) — **no** full-report JSON gold v1 | LLM phrasing varies; **tiered** measurement avoids brittle exact-shape diffing. |
| Cadence | **Prompt gate mandatory** + **weekly full** + **smoke on orchestration commits** | `.cursorrules` mandates pre-prompt-ship; weekly catches **slow drifts** APIs introduce. |
| ADR | **Yes** — record gate for posterity (`ADR 0014` or next free) | Hard launch criteria deserve **Nygard traceability**. |
| Metrics scope | **Per-phase + pipeline** | Phase metrics **localize** regressions; pipeline metrics **gate** launch. |

### 15.2 Open questions (v2 revision)

1. Should eval capture **expected token cost ranges per phase** (Tier 3 telemetry bands, not fixtures) to catch **silent cost regressions** early?

2. Should the eval set include **adversarial / known-hard** ideas (extreme vagueness, non-validatable pitches) beyond the current “vague idea” pattern — to score **graceful degradation**?

3. How does eval **budget Tavily PAYG** — fixed **\$ / week envelope**, strict **\$ / run cap**, or both?

4. Should eval support **recorded mocks** for Tavily / Reddit / Trends to cut **\$**, or **always** hit real APIs for faithful regression detection?

5. If a synthesizer prompt change **helps most eval ideas** but **regresses a minority**, what is the **merge policy** — block, waive with ADR + Tier 1 gold update, or category-specific SLA?

---

*Document status: **APPROVED — co-founder reviewed, decisions resolved, implementation prompt pending.** v2.*
