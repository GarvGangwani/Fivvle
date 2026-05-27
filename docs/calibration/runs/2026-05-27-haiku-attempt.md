# Haiku Migration Attempt — 2026-05-27

**Status:** BLOCKED — reverted to Sonnet.
**Phase:** Cross-cutting (all five research-engine LLM phases)
**Related:** `docs/llm-schema-calibration.md`, commit `22e2d4d` (per-phase provider+model in Settings)
**Authors:** Founding team (decision), calibration run (2026-05-27)

---

## 1. Goal

Switch all five research-engine phases from Claude Sonnet 4.6 to Claude Haiku 4.5 to cut LLM cost for the free/beta tier. Founding-team decision; cost-savings hypothesis assumed Haiku would complete the pipeline at lower per-run spend.

---

## 2. What Shipped

Centralized per-phase `provider` + `model` selection into `Settings` (commit `22e2d4d`). Each phase reads its own `*_provider` / `*_model` pair from config instead of hardcoded model strings. The provider seam in `app/llm/client.py` supports future open-source models via the same config surface — only `anthropic` and `groq` adapters exist today.

---

## 3. Result

Pipeline **FAILED** on Haiku. Two distinct failures, both `InstructorRetryException` from Sonnet-calibrated `max_length` caps:

| Run | Model override | Failure phase | Overrun fields |
|---|---|---|---|
| Run 1 | Synthesizer-only on Sonnet override (other phases Haiku) | Synthesizer | `competitors.N.positioning_vs_idea` (cap 400), `risks_assessment` (cap 2500) |
| Run 2 | All phases Haiku | Planner | `notes_for_synthesizer` (cap 600) |

Both runs exhausted Instructor schema retries and did not reach `RESEARCH_READY`.

---

## 4. Verdict

Haiku systematically writes **longer** than Sonnet-tuned caps across phases. This is not a config wiring problem — it is a **calibration problem**. The ~40 `max_length` caps in output schemas (especially `validation_report.py` and `planner.py`) were set to Sonnet observed-max + margin per `docs/llm-schema-calibration.md`. Haiku's output distribution does not fit those envelopes.

**Action taken:** Reverted all five phases to Sonnet in code defaults (`backend/app/config.py`) and local `.env`. Confirmed green on Sonnet: `RESEARCH_READY`, 59 citations.

---

## 5. Required for Future Haiku (or Any Non-Sonnet / Open-Source) Migration

| Requirement | Detail |
|---|---|
| (a) Per-phase cap recalibration | Re-measure ~40 `max_length` caps against the target model's output distribution per `docs/llm-schema-calibration.md`. Priority: `validation_report.py`, `planner.py`. |
| (b) Prompt conciseness | Likely need explicit brevity instructions per phase so the model stays within calibrated envelopes. |
| (c) Provider adapter | For open-source models: add a provider adapter to `app/llm/client.py` (currently only `anthropic` / `groq`). |

Do **not** flip model defaults again without completing (a) at minimum.

---

## 6. Cost Note

Failed runs cost negligible (partial pipeline, no full Synthesizer completion on Haiku). The cost-savings hypothesis remains **unvalidated** — the pipeline never completed end-to-end on Haiku.

---

## 7. Open Items

- **Synthesizer latency ~8 min on Sonnet** — known, watch; not introduced by this attempt.
- **These caps are the battleground for any model swap** — any future downgrade or open-source migration must treat schema calibration as a gate, not an afterthought.

---

*Document status: BLOCKED. Haiku defaults reverted to Sonnet in config. Re-attempt requires per-phase cap recalibration per §5.*
