"""One-off script to build docs/RESEARCH_ENGINE_SOURCE_DUMP.md."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
OUT = REPO / "docs" / "RESEARCH_ENGINE_SOURCE_DUMP.md"

FENCE = "```"


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def py_block(content: str) -> str:
    return f"{FENCE}python\n{content.rstrip()}\n{FENCE}\n\n"


def section(num: int, title: str, path: str, *, note: str = "") -> str:
    hdr = f"## {num}. {title} — `{path}`\n\n"
    if note:
        hdr += note + "\n\n"
    return hdr + py_block(read(path))


def main() -> None:
    parts: list[str] = ["# Fivvle Research Engine — Verbatim Source Dump\n\n"]

    parts.append(section(1, "Planner phase", "app/services/planner_service.py"))
    parts.append(section(2, "Searcher phase", "app/services/searcher_service.py"))
    parts.append(section(3, "Reader phase", "app/services/reader_service.py"))
    parts.append(section(4, "Reflector phase", "app/services/reflector_service.py"))
    parts.append(section(5, "Synthesizer phase", "app/services/synthesizer_service.py"))

    parts.append(
        "## 6. Business Construction Engine — clustering, action mapping, debate — "
        "`app/services/evidence_analysis_service.py` + `app/services/reasoning_engine_service.py`\n\n"
    )
    parts.append(
        "### 6a. `app/services/evidence_analysis_service.py` (theme word-lists, clustering)\n\n"
    )
    parts.append(py_block(read("app/services/evidence_analysis_service.py")))
    parts.append(
        "### 6b. `app/services/reasoning_engine_service.py` "
        "(`_DECISION_ACTIONS`, `_run_debate_layer`)\n\n"
    )
    parts.append(py_block(read("app/services/reasoning_engine_service.py")))

    reddit_note = (
        "**Import/call sites (Reddit is NOT wired into the research Searcher pipeline):**\n\n"
        "- `backend/app/integrations/__init__.py` — re-exports `search_subreddits`, "
        "`fetch_post_comments`\n"
        "- `backend/tests/test_integrations.py` — integration tests\n"
        "- `backend/tests/test_integrations_reliability.py` — circuit breaker tests\n"
        "- `backend/tests/integrations/test_reddit_concurrent_logging.py` — concurrent "
        "logging tests\n"
        "- No imports from `searcher_service.py`, `research_engine_service.py`, or "
        "`research_engine.py`"
    )
    parts.append(
        section(7, "Reddit integration (PRAW)", "app/integrations/reddit.py", note=reddit_note)
    )

    parts.append(
        "## 8. Reader and Synthesizer prompt text — "
        "`app/llm/prompts/reader.py` + `app/llm/prompts/synthesizer.py`\n\n"
    )
    parts.append("### 8a. Reader prompts (`app/llm/prompts/reader.py`)\n\n")
    parts.append(py_block(read("app/llm/prompts/reader.py")))
    parts.append("### 8b. Synthesizer prompts (`app/llm/prompts/synthesizer.py`)\n\n")
    parts.append(py_block(read("app/llm/prompts/synthesizer.py")))

    parts.append("## 9. ValidationReport SQLAlchemy model + related evidence/citation schemas\n\n")
    parts.append("### 9a. SQLAlchemy model — `app/db/models/validation_report.py`\n\n")
    parts.append(py_block(read("app/db/models/validation_report.py")))
    parts.append(
        "### 9b. Reader evidence atoms — `app/schemas/reader.py` (ExtractedEvidence)\n\n"
    )
    parts.append(py_block(read("app/schemas/reader.py")))
    parts.append(
        "### 9c. Pydantic ValidationReport schema — `app/schemas/validation_report.py` "
        "(Citation, Finding, CompetitorMention, ValidationReport)\n\n"
    )
    parts.append(py_block(read("app/schemas/validation_report.py")))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("".join(parts), encoding="utf-8")
    print(f"Wrote {OUT} ({OUT.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
