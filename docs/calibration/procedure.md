# Research Engine Phase Calibration Procedure

A reusable procedure for calibrating any research engine phase (Reader,
Synthesizer, Reflector, future phases) against real-API output.

## Why this document exists

Schemas in this codebase have repeatedly been miscalibrated when designed
by reasoning about "reasonable output sizes" instead of measurement. The
B2.2 planner question cap, the B2 refinement risks and subheadline caps,
and other examples documented in `docs/llm-schema-calibration.md` all
followed the same pattern: cap set by guess, cap fails under real
output, cap revised after live failures.

This procedure replaces the guess-then-fail cycle with a structured
calibration session run against real-API output BEFORE phase output
shape locks in for downstream consumers.

Run this procedure:
- After initial implementation of any new research engine phase
- After meaningful prompt changes to an existing phase (anything that
  alters output shape, length tendencies, or instruction set)
- When the cost ledger or admin dashboards show anomalies on a phase
  (cap utilization spikes, retry-rate spikes, hallucination-guard trips)

## Prerequisites before running

1. Phase implementation is on `main`, tests passing.
2. The phase's service code emits DEBUG-level structlog entries for:
   - `len(value)` of every field with a `max_length` cap
   - Per-field hallucination counters (URL, quote, or phase-specific
     guards) where applicable
   - Cost and latency per LLM call
3. Anthropic balance is at least $30 (calibration runs cost ~$5-15 per
   founder-idea pipeline run; budget for 5 ideas).
4. The 5 founder ideas for the calibration set are picked and written
   down. Variety matters more than volume — see "Idea variety" below.

`reflection_loops_used` on the persisted ValidationReport is the number of
refinement waves in which the Reflector executed at least one successful
re-search (not reflector LLM-call count; a wave that flagged questions but ran
no re-search counts as 0).

## Idea variety

Pick 5 founder ideas that vary along these axes:

- **B2B vs B2C**: at least one of each
- **Regulated vs unregulated**: at least one regulated (healthcare,
  finance, legal, pharma, insurance) and one unregulated
- **Niche vs mass-market**: at least one of each
- **Established competitor space vs novel space**: at least one of each

A typical 5-idea set looks like:

1. B2B SaaS in an established space (e.g., "AI assistant for sales reps
   that drafts follow-up emails")
2. Consumer mobile app in a mass-market space (e.g., "meal planning
   app that uses what's already in your fridge")
3. Regulated B2B (e.g., "compliance automation for clinical trial
   document review")
4. Niche developer tool (e.g., "CLI for managing kubernetes secrets
   across multiple clusters with team-level access controls")
5. Novel consumer concept (e.g., "subscription service that ships a
   pre-portioned art project to your door each month")

The variety surfaces calibration issues a single idea would hide.
Mass-market ideas produce more Tavily results and longer paraphrases.
Niche ideas produce fewer results and trigger sparse-evidence paths.
Regulated ideas produce more named entities (laws, agencies, standards).

If you can't get variety from 5 ideas, run 7. Variety beats volume.

## Procedure

### Step 1 — Prepare the calibration data sheet

Create a new file: `docs/calibration/runs/YYYY-MM-DD-{phase}-calibration.md`.

Header section:

```markdown
# Calibration Run: {phase} — YYYY-MM-DD

**Phase:** Reader / Synthesizer / Reflector / ...
**Prompt version:** {prompt_name}_v{N} (from PROMPT_NAME constant)
**Anthropic balance at start:** $X.XX
**Tavily balance at start:** $X.XX
**Ideas in calibration set:** 5

## Ideas

1. Idea description, in 1-2 sentences
2. ...
```

Leave the rest of the file empty for now.

### Step 2 — Run each idea through the full pipeline

For each of the 5 ideas:

1. Submit via the API or smoke script (`backend/scripts/try_b2_4_end_to_end.py`
   or its current equivalent).
2. Wait for pipeline completion or `RESEARCH_FAILED`.
3. Capture:
   - Total wall-clock latency
   - Total Anthropic cost (sum of `LLMCall.cost_usd` for that
     experiment)
   - Total Tavily cost (sum of `ExternalAPICall.cost_usd` for that
     experiment)
   - Per-phase row counts in `LLMCall` (how many LLM calls did each
     phase make)
   - Final experiment status

4. Pull the phase-specific DEBUG structlog entries for that experiment
   from Cloud Logging or local logs. For Reader specifically, this
   includes per-question `extracted_evidence_count`,
   `hallucinated_url_count`, `quote_hallucination_count`, and per-field
   `len()` values from the DEBUG emits.

5. Append a per-idea section to the calibration data sheet:

```markdown
## Idea N: {short label}

- Status: RESEARCH_READY / RESEARCH_FAILED / ...
- Wall-clock: X.X minutes
- Anthropic cost: $X.XX
- Tavily cost: $X.XX
- {Phase}-specific data:
  - Per-question LLM calls: N (for per-question phases like Reader)
  - Total extracted_evidence items: N
  - hallucinated_url_count total: N
  - quote_hallucination_count total: N
  - {field_name} len distribution: median X, max Y, observed cap utilization Z%
  - ...

- Anomalies observed: (free text)
- Sample output quality: (free text — 1-2 paragraphs assessing whether
  the phase's output is what we wanted)
```

### Step 3 — Compute per-field calibration deltas

For each field with a `max_length` cap, compute across all 5 ideas:

- Observed max value across all instances of the field
- Observed median value across all instances of the field
- Cap utilization at observed max: `observed_max / cap`
- Recommended new cap: `observed_max + 15%` rounded to nearest 50

If `cap utilization at observed max < 0.5` (cap is 2× larger than
needed), recommended new cap is also `observed_max + 15%`. Caps should
be tight to observed output, not loose.

If `cap utilization at observed max > 0.95` (output is brushing the
cap), the cap was too tight and output may have been truncated.
Investigate truncation in the structlog entries. If truncation
happened, the recommended new cap is `observed_max × 1.30` (extra
margin to account for truncation having lost data).

Record findings in the data sheet:

```markdown
## Calibration analysis

| Field | Current cap | Observed max | Observed median | Utilization | Recommended cap | Rationale |
|---|---|---|---|---|---|---|
| field_name | 200 | 187 | 142 | 94% | 250 | High utilization, raise with margin |
| ...
```

### Step 4 — Compute hallucination-guard threshold deltas

For each hallucination guard in the phase (URL guard, quote guard,
phase-specific guards):

- Observed rate per question across all 5 ideas (mean and max)
- Current threshold
- Whether threshold was tripped during the calibration runs

If observed median rate is consistently below 25% of threshold, the
threshold shape is right but the number can move. Note this in the
data sheet; do NOT change the threshold unless multiple consecutive
calibration runs show the same pattern (one calibration session is one
data point, not a trend).

If threshold was tripped on any run, investigate the underlying cause
in the structlog entries before deciding whether to relax the
threshold or fix the prompt. The threshold existing AND tripping is
working as designed — it's catching a real prompt-quality issue.

### Step 5 — Cost ledger update

Append to `docs/cost-ledger.md`:

```markdown
## YYYY-MM-DD — {phase} calibration run

| Date | Activity | Anthropic | Tavily | Notes |
|---|---|---|---|---|
| YYYY-MM-DD | {phase} calibration, idea 1 ({short label}) | $X.XX | $X.XX | status |
| YYYY-MM-DD | {phase} calibration, idea 2 ({short label}) | $X.XX | $X.XX | status |
| ...
| YYYY-MM-DD | {phase} calibration, idea 5 ({short label}) | $X.XX | $X.XX | status |

Subtotal: ~$X.XX of $X.XX budget.

### Average cost per pipeline run

Mean: $X.XX. Median: $X.XX. Max: $X.XX (idea N, reason).

Compared to .cursorrules target of $0.25-$0.70: {within / above / well above}.
```

### Step 6 — Update llm-schema-calibration.md

Append the per-field findings from Step 3 to
`docs/llm-schema-calibration.md`, using the existing format for that
file. Each entry must be dated and reference this calibration run's
data sheet.

If any caps are being raised, propose the schema edits in a separate
short prompt — the calibration procedure does not write code, it only
produces calibration data.

### Step 7 — Document overall phase quality assessment

In the calibration data sheet, add a closing section:

```markdown
## Overall phase quality assessment

### What worked
- (free text — what aspects of the phase output were good across all 5
  ideas)

### What didn't work
- (free text — common failure patterns, weak extractions, low-quality
  paraphrases, etc.)

### Recommended prompt changes
- (free text — specific changes to the phase's prompt that would
  improve quality based on observed output)

### Recommended schema changes
- (refer to Step 3 calibration analysis table)

### Recommended threshold changes
- (refer to Step 4 analysis)

### Open questions for the next iteration
- (free text — anything observed that needs more data before a
  decision)
```

### Step 8 — Commit and review

Commit the calibration data sheet and any updates to the cost ledger
and `llm-schema-calibration.md` as a single commit:
git add docs/calibration/runs/YYYY-MM-DD-{phase}-calibration.md docs/cost-ledger.md docs/llm-schema-calibration.md
git commit -m "calibration({phase}): {phase} v{N} prompt — observed-max + threshold review"

The calibration data sheet is a permanent artifact. Do not delete or
overwrite old calibration runs. Each one is a data point in the phase's
quality history.

## Frequency

- After initial phase implementation: ALWAYS run before the phase ships
  for production traffic
- After meaningful prompt changes: ALWAYS run before the change ships
- Periodic re-calibration on production traffic: every 30 days, or when
  cost-per-run drifts more than 25% from the last calibration run's
  mean

## What this procedure does NOT cover

- Eval-set discipline (separate planning artifact, follows after Reader
  and Synthesizer are both calibrated)
- Multi-run statistical analysis (one calibration run is one data
  point; statistical analysis requires multiple runs over time and is
  out of scope for the per-run procedure)
- Automated regression detection (eventual goal, manual for MVP)
