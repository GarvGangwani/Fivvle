"""One-shot generator for docs/context/FIVVLE_REDDIT_CONTEXT.md."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs" / "context" / "FIVVLE_REDDIT_CONTEXT.md"

# Field defaults in config that must not leak real secrets when pasted.
_REDACT_ENV_DEFAULTS = re.compile(
    r"^(anthropic_api_key|groq_api_key|moonshot_api_key|tavily_api_key|"
    r"reddit_client_id|reddit_client_secret|razorpay_key_secret|database_url)\s*=\s*.+$",
    re.MULTILINE,
)


def redact(text: str) -> str:
    text = _REDACT_ENV_DEFAULTS.sub(r"\1 = <REDACTED>", text)
    text = re.sub(r"REDDIT_CLIENT_SECRET=.*", "REDDIT_CLIENT_SECRET=<REDACTED>", text)
    return text


def read(rel: str) -> str:
    p = ROOT / rel
    if not p.exists():
        return ""
    return redact(p.read_text(encoding="utf-8"))


def fence(rel: str, lang: str = "python") -> str:
    body = read(rel)
    if not body:
        return f"### `{rel}`\n\nDOES NOT EXIST\n"
    return f"### `{rel}`\n\n```{lang} title=\"{rel}\"\n{body.rstrip()}\n```\n"


def rg(pattern: str, *paths: str) -> str:
    cmd = [
        "rg",
        "-i" if pattern.islower() and pattern == "praw" else "",
        pattern,
        str(ROOT),
        "--glob",
        "!**/.venv/**",
        "--glob",
        "!**/node_modules/**",
        "--glob",
        "!**/.pytest_cache/**",
    ]
    cmd = [c for c in cmd if c]
    if paths:
        cmd = ["rg", pattern] + list(paths)
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)
        return (r.stdout or "").strip() or "(no matches)"
    except FileNotFoundError:
        # fallback: use grep tool output embedded manually
        return "(rg not on PATH — see section files below)"


def run_rg(args: list[str]) -> str:
    r = subprocess.run(
        args,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    return (r.stdout or "").strip()


def git_scoped(cmd: list[str]) -> str:
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return (r.stdout or "").strip() or "no in-progress Reddit work"


def section_files(title: str, rels: list[str], lang: str = "python") -> str:
    parts = [f"## {title}\n"]
    for rel in rels:
        parts.append(fence(rel, lang))
    return "\n".join(parts)


def main() -> None:
    lines: list[str] = [
        "# FIVVLE Reddit / Voices Context Dump",
        "",
        "Generated for external assistant working on a Voices (Reddit/PRAW) research phase.",
        "Source files below are verbatim unless marked DOES NOT EXIST.",
        "",
        "## 1. PRAW module — what exists",
        "",
        "### `rg -i praw` (whole repo, excluding .venv and node_modules)",
        "",
        "```text",
        rg("praw"),
        "```",
        "",
        "**Invocation note:** PRAW lives in `backend/app/integrations/reddit.py`, re-exported from "
        "`backend/app/integrations/__init__.py`. It is **not imported or called** by "
        "`searcher_service.py`, `research_engine.py`, or `research_engine_service.py`. "
        "Only integration tests invoke `search_subreddits` / `fetch_post_comments` directly.",
        "",
    ]

    for missing in [
        "backend/app/services/reddit_service.py",
        "backend/app/services/reddit_client.py",
        "backend/app/services/praw_client.py",
    ]:
        lines.append(f"### `{missing}`\n\nDOES NOT EXIST\n")

    lines.append("### Reddit-specific schemas under `backend/app/schemas/`\n\nDOES NOT EXIST\n")

    for rel in [
        "backend/app/integrations/reddit.py",
        "backend/app/integrations/__init__.py",
        "backend/app/config.py",
        "backend/tests/test_integrations.py",
        "backend/tests/integrations/test_reddit_concurrent_logging.py",
        "backend/.env.example",
        "backend/pyproject.toml",
        "functions/research_engine/requirements.txt",
    ]:
        lines.append(fence(rel, "toml" if rel.endswith(".toml") else "text" if rel.endswith(".txt") else "python"))

    config = read("backend/app/config.py")
    config_lines = config.splitlines()
    reddit_excerpt = "\n".join(config_lines[62:66]) if len(config_lines) > 66 else "(not found)"

    lines.extend(
        [
            "## 2. Reddit auth / credentials",
            "",
            "### Reddit-related settings in `backend/app/config.py`",
            "",
            "```python title=\"backend/app/config.py (reddit settings)\"",
            reddit_excerpt,
            "```",
            "",
            "**Environment variables (Pydantic Settings, case-insensitive):**",
            "- `REDDIT_CLIENT_ID` → `Settings.reddit_client_id`",
            "- `REDDIT_CLIENT_SECRET` → `Settings.reddit_client_secret`",
            "- `REDDIT_USER_AGENT` → `Settings.reddit_user_agent`",
            "",
            "**Auth mode:** Script/read-only application OAuth — `praw.Reddit(client_id=..., "
            "client_secret=..., user_agent=...)`. No username/password, no user OAuth redirect flow, "
            "no posting scopes. This is the standard Reddit **script** app pattern (client credentials "
            "only). Rate limit for OAuth apps: **60 requests/minute** per Reddit API docs.",
            "",
            section_files(
                "3. Existing external-source patterns",
                [
                    "backend/app/services/searcher_service.py",
                    "backend/app/integrations/tavily.py",
                    "backend/app/db/models/external_api_call.py",
                    "backend/app/cost/tavily.py",
                ],
            ),
            "",
            "### `external_api_call` / `ExternalAPICall` grep (backend)",
            "",
            "```text",
            run_rg(["rg", "external_api_call|ExternalAPICall", str(ROOT / "backend"), "-g", "!**/.venv/**"])
            or "(no matches)",
            "```",
            "",
            section_files(
                "4. Reader schema and how Tavily results flow in",
                [
                    "backend/app/schemas/reader.py",
                    "backend/app/services/reader_service.py",
                    "backend/app/llm/prompts/reader.py",
                ],
            ),
            "",
            "### `ExtractedEvidence` consumers (grep, backend)",
            "",
            "```text",
            run_rg(["rg", "ExtractedEvidence", str(ROOT / "backend")]),
            "```",
            "",
            "**Production consumers:** `reader_service.py` (produces), `evidence_atoms.py` (maps to "
            "`EvidenceAtom`), `synthesizer_input.py` (caps + packs for synthesizer), "
            "`llm/prompts/synthesizer.py` (citation rules). Tests import heavily.",
            "",
            section_files(
                "5. Research plan and question generation",
                [
                    "backend/app/services/planner_service.py",
                    "backend/app/llm/prompts/planner.py",
                    "backend/app/schemas/planner.py",
                ],
            ),
            "",
            "**Planner `search_queries`:** Each `ResearchQuestion` has `search_queries: list[str]` "
            "(1–3 items). Strings are **generic web search queries** passed to Tavily in Searcher — "
            "not Tavily API objects, but today they are only consumed by Tavily (no Reddit query field).",
            "",
            "### `backend/app/services/orchestrator.py`",
            "",
            "DOES NOT EXIST",
            "",
            section_files(
                "6. Orchestrator — where a new phase would slot in",
                [
                    "backend/app/services/research_engine.py",
                    "backend/app/services/research_engine_service.py",
                    "backend/app/db/enums.py",
                ],
            ),
            "",
            "### `ExperimentStatus` research sub-states (from enum)",
            "",
            "Values used during research: `RESEARCHING` (parent), `RESEARCH_PLANNING`, "
            "`RESEARCH_SEARCHING`, `RESEARCH_READING`, `RESEARCH_REFLECTING`, `RESEARCH_SYNTHESIZING`, "
            "then `RESEARCH_READY`.",
            "",
            "**Parallelism:** Phases are **strictly sequential** at the orchestrator level. Within Searcher, "
            "Tavily queries run concurrently (`asyncio.gather`). Within Reader, per-question LLM calls use "
            "`reader_concurrency_limit` (default 7). No parallel phase execution (e.g. Searcher + Voices).",
            "",
            "**Per-phase cost:** LLM phases write `LLMCall` with `phase` field. External APIs write "
            "`ExternalAPICall` with `provider` (`tavily`, `reddit`, `pytrends`) and `cost_category`.",
            "",
            section_files(
                "7. Synthesizer — where a Voices section would land",
                [
                    "backend/app/llm/prompts/synthesizer.py",
                    "backend/app/schemas/validation_report.py",
                ],
            ),
            "",
            "**Current `ValidationReport` top-level section fields:** `executive_summary`, "
            "`overall_recommendation`, `recommendation_rationale`, `questions_and_findings`, "
            "`competitors`, `market_signals`, `distribution_signals`, `regulatory_signals`, "
            "`risks_assessment`, `research_limitations`, `section_scores`, `business_construction`, "
            "`overall_score`, `rubric_version_used`. No `voices` or `reddit_signals` field in current schema "
            "(legacy DB column dropped).",
            "",
            section_files(
                "8. Cost / observability",
                [
                    "backend/app/llm/cost.py",
                    "backend/app/db/models/llm_call.py",
                    "backend/app/db/models/external_api_call.py",
                    "backend/app/cost/category.py",
                    "backend/app/cost/rollup.py",
                ],
            ),
            "",
            "### `_PHASE_TO_CATEGORY` / `CostCategory` grep",
            "",
            "```text",
            run_rg(["rg", "_PHASE_TO_CATEGORY|CostCategory", str(ROOT / "backend" / "app")]),
            "```",
            "",
            "### Admin cost dashboard endpoints — `backend/app/routers/admin.py`",
            "",
            "```python title=\"backend/app/routers/admin.py\"",
            read("backend/app/routers/admin.py").rstrip(),
            "```",
            "",
            "## 9. Rate limiting and retry patterns",
            "",
            fence("backend/app/reliability/retry.py"),
            fence("backend/app/reliability/circuit_breakers.py"),
            fence("backend/app/reliability/rate_limit.py"),
            "",
            "### `rate_limit` / `backoff` / `retry` grep (backend/app/reliability + integrations)",
            "",
            "```text",
            run_rg(
                [
                    "rg",
                    "rate_limit|backoff|retry",
                    str(ROOT / "backend" / "app"),
                    "-g",
                    "!**/.venv/**",
                ]
            ),
            "```",
            "",
            "### `429` in Tavily integration and Searcher",
            "",
            "```text",
            run_rg(
                [
                    "rg",
                    "429",
                    str(ROOT / "backend" / "app" / "integrations"),
                    str(ROOT / "backend" / "app" / "services" / "searcher_service.py"),
                ]
            )
            or "(no literal 429 handlers — transient errors handled via circuit_breakers.is_transient_error)",
            "```",
            "",
            "**Pattern to reuse for Reddit 60/min:** `retry_async` + `circuit_breakers` (429 in transient set) "
            "as used by Tavily; plus explicit client-side throttling not yet implemented for Reddit.",
            "",
            section_files(
                "10. Geography and targeting threading",
                [
                    "backend/app/schemas/targeting.py",
                    "backend/app/services/geography_hint_service.py",
                    "backend/app/services/searcher_service.py",
                ],
            ),
            "",
            "### `ExperimentTargeting` call sites (grep, backend)",
            "",
            "```text",
            run_rg(["rg", "ExperimentTargeting", str(ROOT / "backend")]),
            "```",
            "",
            "### Searcher geography integration (replaces hardcoded `_geo_domain_hint`)",
            "",
            "Searcher calls `geography_hint_service.get_include_domains_for_geography()` when "
            "`targeting.target_geography` is set and the query is geo-sensitive (`_is_geo_sensitive`). "
            "See `searcher_service.py` above for the full implementation.",
            "",
            "## 11. Known Reddit gotchas from the founder",
            "",
            "- **Async vs sync:** PRAW is synchronous. `reddit.py` wraps all blocking calls with "
            "`asyncio.to_thread()` — safe inside FastAPI async handlers.",
            "- **OAuth scopes:** Read-only public data only (`subreddit.search`, post comments). No elevated "
            "scopes, no private subreddits, no user profile data.",
            "- **Flaky/skipped tests:** None marked `@pytest.mark.skip` or flaky for Reddit in "
            "`test_integrations.py` or `test_reddit_concurrent_logging.py`.",
            "- **TODO/FIXME in Reddit files:**",
            "",
            "```text",
            run_rg(
                [
                    "rg",
                    "TODO|FIXME|XXX|HACK",
                    str(ROOT / "backend" / "app" / "integrations" / "reddit.py"),
                    str(ROOT / "backend" / "tests" / "test_integrations.py"),
                ]
            )
            or "(none)",
            "```",
            "",
            "## 12. Recent uncommitted or in-progress Reddit-adjacent work",
            "",
            "### `git status` (reddit/praw/voices/subreddit)",
            "",
            "```text",
            git_scoped(
                [
                    "git",
                    "status",
                    "--short",
                    "--",
                    "*reddit*",
                    "*praw*",
                    "*voices*",
                    "*subreddit*",
                ]
            ),
            "```",
            "",
            "### `git diff HEAD --stat` (scoped)",
            "",
            "```text",
            git_scoped(["git", "diff", "HEAD", "--stat", "--", "*reddit*", "*praw*", "*voices*", "*subreddit*"]),
            "```",
            "",
            "## 13. Cursor's own read",
            "",
            "- `backend/app/integrations/reddit.py` — complete wrapper (search + comments, cost logging, "
            "`asyncio.to_thread`) but **never wired** into the research pipeline.",
            "- `backend/app/integrations/__init__.py` exports Reddit next to Tavily — hook point exists.",
            "- `backend/app/config.py` requires Reddit env vars at startup even though Searcher ignores Reddit.",
            "- No `reddit_service.py`, no Reddit Pydantic schemas — all logic is in `integrations/reddit.py`.",
            "- `searcher_service.py` only calls Tavily + pytrends; no import of `app.integrations.reddit`.",
            "- Pipeline orchestration is in `research_engine_service.py` + `research_engine.py` — fixed "
            "sequential phase list; adding Voices needs new status enum value(s) and orchestrator branch.",
            "- `ValidationReport` has market/distribution/regulatory sections but no `voices` slot yet.",
            "- Geography threading via `geography_hint_service` + `ExperimentTargeting` is established for "
            "Tavily `include_domains` — mirror for subreddit selection.",
            "- Reddit rate-limit handling is weaker than Tavily (no `retry_async` wrapper in `reddit.py`).",
            "- `docs/planning/multi-source-searcher.md` defers Reddit to v2; `.cursorrules` still lists Reddit "
            "as MVP — documentation tension.",
            "- `docs/FIVVLE_CRITIQUE.md` explicitly notes Reddit built but unused.",
            "- `functions/research_engine/requirements.txt` includes `praw` — Cloud Function image has dep "
            "even though function code path may not call it yet.",
            "",
        ]
    )

    text = "\n".join(lines) + "\n"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(text, encoding="utf-8")
    line_count = len(text.splitlines())
    print(f"Wrote {OUT} ({line_count} lines)")


if __name__ == "__main__":
    main()
