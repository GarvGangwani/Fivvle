# Voices dev-loop harness

Dev-only tooling to iterate on **Voices**, **subreddit selection**, and **Synthesizer voices rendering** without running full experiments (~$1 each) or live Reddit calls.

## Cost

| Mode | Approx cost |
|------|-------------|
| `--skip-synthesizer` | ~$0.05 (Voices LLM only) |
| Full harness (Voices + Synthesizer) | ~$0.10 |

Real LLM calls are intentional. Reddit is fixture-backed (no HTTP).

## Reddit on local dev (read this first)

**Many local IPs are blocked by Reddit network security** (incognito browser shows
"You've been blocked by network security"). When blocked:

- Do **not** run `smoke_test_reddit_http` or `capture_reddit_fixtures` locally —
  they will fail with HTTP 403 regardless of User-Agent.
- Use the **bundled synthetic fixtures** under `fixtures/reddit_full`,
  `fixtures/reddit_empty`, and `fixtures/reddit_partial` for harness iteration.

**Before Voices ships to real founders:** live Reddit fetching **must** be verified
from **Cloud Run** (or your production equivalent). Run `smoke_test_reddit_http`
there after deploy, or confirm Voices returns real atoms on a staging research run.
Do not assume local success or failure generalizes to production.

## Quick start

```bash
cd backend

# Run harness against bundled fixtures (no live Reddit)
uv run python -m scripts.voices_devloop.voices_devloop \
  --upstream us_founder_platform --reddit full --skip-synthesizer
```

Optional — verify live Reddit HTTP from an **unblocked** network or Cloud Run only:

```bash
uv run python -m scripts.voices_devloop.smoke_test_reddit_http
```

## Fixture sets

### Upstream (`fixtures/upstream_<name>/`)

Populated by `capture_upstream.py` after a one-time full pipeline run (~$1):

```bash
uv run python -m scripts.voices_devloop.capture_upstream \
  --experiment-id <REFINED_EXPERIMENT_UUID> \
  --output-dir scripts/voices_devloop/fixtures/upstream_us_founder_platform
```

Set `RESEARCH_DEV_CAPTURE_DIR` automatically via `--output-dir`. The capture flag in `research_engine_service` defaults **OFF** unless that env var is set.

**Chosen fixture idea (founder):** US founder validation platform — milestone-based idea-to-launch workflow (similar to Fivvle).

Files written per run:

- `refined_idea.json`, `targeting.json`
- `research_plan.json`, `search_results.json`
- `reader_outputs.json`, `reflected_outputs.json`
- `evidence_analysis.json`, `reasoning_output.json`

### Reddit (`fixtures/reddit_<mode>/`)

Synthetic fixtures are **sufficient for local iteration** on Voices prompts,
subreddit-selection behavior, and Synthesizer rule-5 absence language. They
exercise full, empty, and partial Reddit fetch paths without HTTP.

| Mode | Purpose |
|------|---------|
| `full` | Normal fetch with posts + comments |
| `empty` | Simulates all subs failing (`praw_all_failed`) |
| `partial` | Only `startups` succeeds |

Regenerate `reddit_full` from an **unblocked** network or Cloud Run after HTTP
layer changes (skip on locally blocked IPs):

```bash
uv run python -m scripts.voices_devloop.capture_reddit_fixtures \
  --output-dir scripts/voices_devloop/fixtures/reddit_full
```

## Sanitization

- Strip `u/<username>` patterns before persisting fixtures
- Do **not** commit fixtures with real PII
- Usernames never logged by the integration layer (metadata only)

## Safety

- **Dev-only.** Never wire into user-facing routes.
- Capture flag in `research_engine_service` requires explicit `RESEARCH_DEV_CAPTURE_DIR`.