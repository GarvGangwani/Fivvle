# Per-Commit Review Checklist

A reusable checklist the human co-founder runs through before
committing any agent-produced code in the research engine, services,
schemas, or LLM-call sites.

This checklist is not a substitute for reading the diff. It is a
forcing function for catching specific patterns that diff-reading
alone often misses.

## When to run this checklist

- Before every `git commit` of agent-produced code
- Especially before commits that touch: LLM call sites, schemas with
  `max_length` caps, hallucination guards, state machine transitions,
  cost-tracking code, security-sensitive code (auth, SSRF wrapper,
  webhooks)

## The checklist

For each item: tick yes, no, or N/A. If any item is "no," resolve it
before committing.

### 1. Planning doc adherence

- [ ] Does the committed code match the planning doc's design?
- [ ] If there are deviations, did the agent flag them in its output?
- [ ] If there are deviations that the agent did NOT flag, are they
  intentional or accidental?
- [ ] For accidental deviations: revert to planning-doc behavior or
  update the planning doc before committing.

### 2. Test verification

- [ ] Did the agent run the relevant test files? Did they pass?
- [ ] Pick one or two newly-added tests covering the most important
  new behavior. Toggle the implementation off (comment out, return
  early, revert the change). Run those tests.
- [ ] Do the tests FAIL when the implementation is toggled off?
- [ ] If they don't fail, the tests aren't actually testing the new
  behavior. Investigate before committing.
- [ ] Toggle the implementation back on. Tests pass again?

### 3. Calibration logging

- [ ] For every new schema field with a `max_length` cap: is there a
  DEBUG-level structlog emit somewhere in the service code that logs
  `len(field_value)`?
- [ ] If no calibration logging exists, future calibration will be
  impossible. Add the logging before committing.

### 4. Observability

- [ ] For every new failure mode (validation error path, guard trip,
  sentinel production, total failure): is there a structlog emit that
  captures the failure with enough context to debug?
- [ ] For per-phase or per-question failures: does the emit include
  `experiment_id`, the phase or question identifier, and the failure
  type?
- [ ] For run-level failures: does the emit include `experiment_id`
  and a summary of what was affected?
- [ ] Are log levels appropriate? (WARNING for per-item degradation,
  ERROR for systemic signals that need dashboard attention, INFO for
  normal flow.)

### 5. Cost tracking

- [ ] Every new LLM call site goes through `complete_structured()` or
  the equivalent client wrapper, NOT a direct provider SDK call?
- [ ] Every LLM call has a `prompt_name` set, distinct from existing
  prompts (e.g., `reader_v1`, not `reader`)?
- [ ] Every external API call goes through an integration wrapper
  with circuit breaker and retry?
- [ ] Every external API call writes to `ExternalAPICall` table?

### 6. Security

- [ ] Per `AGENTS.md` "LLM and agent security": are LLM outputs parsed
  via Pydantic before any downstream use?
- [ ] Per `AGENTS.md` "Logging hygiene": are LLM prompts containing
  user content NOT logged verbatim? (Log token counts and prompt names
  only.)
- [ ] Per `AGENTS.md` "Logging hygiene": are scraped web contents NOT
  logged?
- [ ] Per `AGENTS.md` "Authentication": any new authenticated endpoint
  verifies Firebase token via `Depends()`?
- [ ] Per `AGENTS.md` "Authorization": any new endpoint with a
  resource ID verifies ownership separately from authentication?
- [ ] Per `AGENTS.md` "SSRF prevention": any new URL fetch goes
  through `safe_fetch`, not direct `httpx.get()`?

### 7. State machine integrity

- [ ] If the commit touches `research_engine_service.py` or any
  experiment status transition: are transitions atomic (each transition
  commits its own status update before the next phase starts)?
- [ ] Are failure paths explicit (the code says "transition to
  RESEARCH_FAILED" rather than leaving the experiment in a mid-pipeline
  state on exception)?
- [ ] Does the commit leave any state in `ExperimentStatus` enum that
  is defined but has no executor and no forward transition? If so, is
  it documented as "unreachable until phase X lands"?

### 8. Schema migration safety

- [ ] If the commit includes a new Alembic migration: does the
  migration include both `upgrade` and `downgrade` functions?
- [ ] If the migration adds a NOT NULL column to an existing table:
  does it use the two-step pattern (add with `server_default`, then
  drop the default)?
- [ ] Has the migration been tested locally against the existing
  database (the Docker `fivvle-postgres` container)?

### 9. Backwards compatibility

- [ ] Does the commit break any existing endpoint contracts?
- [ ] Does the commit break any existing schema fields that
  downstream consumers depend on?
- [ ] If breaking changes are intentional: are they documented in the
  commit message and in the relevant planning doc / ADR?

### 10. Agent honesty signals

- [ ] Did the agent claim "tests pass" without showing the actual
  test output? If yes, demand the test output before believing the
  claim.
- [ ] Did the agent attribute new failures to "pre-existing issues"
  or "unrelated to this change"? If yes, verify by running tests on
  the previous commit (`git stash; git checkout HEAD~1; run tests`)
  before accepting the explanation.
- [ ] Did the agent silently change scope (add files outside the
  scope of the prompt, modify files not mentioned in the prompt)? If
  yes, review the additions for whether they belong in this commit or
  should be split out.

## After the checklist

If all items are yes (or N/A with justification), commit.

If any item is no, either:
1. Resolve the issue (the agent can usually fix it with a follow-up
   prompt), or
2. Decide consciously that the gap is acceptable for this commit and
   document the gap somewhere it will be remembered (a TODO file, an
   issue, or a comment in the relevant file).

Do NOT commit with unresolved "no" items just because you want to
move forward. The checklist is the forcing function. Skipping it
defeats its purpose.

## Modifying this checklist

Add items as new patterns emerge. Remove items when they stop being
relevant. Treat this document as living infrastructure.