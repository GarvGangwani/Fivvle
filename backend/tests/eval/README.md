# Research Engine Eval Set

Fixed inputs for evaluating research engine prompt quality across diverse idea types.
Maintained alongside the engine — prompt changes don't ship without an eval run.

## What this is

The eval set is a collection of 10 founder ideas with:
- **`ideas.py`** — `EvalIdea` objects: raw idea text + a hand-populated `RefinedIdea` (the
  exact input the research engine receives, bypassing the refinement step so eval runs don't
  re-spend refinement tokens).
- **`gold_standards.py`** — per-idea `GoldStandard` objects: what a good report MUST mention,
  SHOULD mention, and must NOT fabricate.
- **`rubric.py`** — five scored criteria used when a human grades a `ValidationReport` against
  the eval set.

## When to run evals

Run **before any prompt change ships** (planner, reader, synthesizer). This is a non-negotiable
quality gate per `.cursorrules` "Research Engine Quality". Evals are deliberate, not casual:

- Each full research run costs **~$0.30–$0.80** (Tavily + Claude across all phases).
- The full 10-idea eval set costs **~$5–$8**.
- Never run the full set casually; run 1–3 targeted ideas when iterating, full set before merge.

## How to add new ideas

1. Add an `EvalIdea` entry to `ideas.py` with a unique `id` slug.
2. Populate `refined_idea` by hand (match what the production refinement service produces —
   specific audience, investigable risks, no filler).
3. Add a corresponding `GoldStandard` entry to `gold_standards.py`.
4. Run `uv run pytest tests/eval/test_eval_data_integrity.py` to verify data integrity.

## The rubric (5 criteria)

Scores are 1–5 per criterion; see `rubric.py` for the full criterion definitions.

| Criterion | What it measures |
|---|---|
| `citation_quality` | Are findings backed by specific source URLs? No uncited claims? |
| `specificity` | Concrete numbers, named competitors, real complaints — not generic summaries |
| `investigability` | Did the engine chase the specific risks from refinement, not generic startup commentary? |
| `coverage` | Do questions span meaningful dimensions (market, competitors, WTP, distribution, tech)? |
| `honesty` | Does the report flag thin evidence? Does it refuse to fabricate for vague ideas? |

## Running evals (coming in B2.4)

The automated eval runner (`scripts/run_eval.py`) is scaffolded in build step B2.4.
Until then, run ideas manually via the research engine trigger endpoint and grade by hand
using `rubric.py` as your scoring guide.

`RUBRIC_VERSION` in `rubric.py` is incremented when criteria definitions change —
historical scores are only comparable within the same rubric version.
