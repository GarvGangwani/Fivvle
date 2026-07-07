"""Build docs/BUG3_MARKDOWN_EXPORT_INVESTIGATION.md."""

from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
FRONTEND = REPO / "frontend"
BACKEND = REPO / "backend"
DOCS = REPO / "docs"
OUT = DOCS / "BUG3_MARKDOWN_EXPORT_INVESTIGATION.md"

FENCE = "```"


def read(path: Path) -> str:
    raw = path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        return raw.decode("utf-8-sig")
    return raw.decode("utf-8")


def block(content: str, lang: str) -> str:
    return f"{FENCE}{lang}\n{content.rstrip()}\n{FENCE}\n\n"


def file_block(path: Path, lang: str | None = None) -> str:
    suffix = path.suffix.lstrip(".")
    use_lang = lang or ("tsx" if suffix in {"tsx", "ts"} else suffix)
    rel = path.relative_to(REPO).as_posix()
    return f"### `{rel}`\n\n{block(read(path), use_lang)}"


def extract_class(path: Path, class_name: str) -> str:
    lines = read(path).splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith(f"class {class_name}"))
    end = len(lines)
    for j in range(start + 1, len(lines)):
        if lines[j].startswith("class ") and not lines[j].startswith("class _"):
            end = j
            break
    return f"### {class_name}\n\n`{path.relative_to(REPO).as_posix()}`\n\n{block(chr(10).join(lines[start:end]), 'python')}"


def extract_interface(path: Path, name: str) -> str:
    lines = read(path).splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith(f"export interface {name}"))
    end = len(lines)
    for j in range(start + 1, len(lines)):
        if lines[j].startswith("export ") and not lines[j].startswith("export interface "):
            end = j
            break
    rel = path.relative_to(REPO).as_posix()
    return f"### {name}\n\n`{rel}`\n\n{block(chr(10).join(lines[start:end]), 'typescript')}"


def extract_py_function(path: Path, def_name: str) -> str:
    lines = read(path).splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith(f"async def {def_name}") or line.startswith(f"def {def_name}"))
    end = len(lines)
    for j in range(start + 1, len(lines)):
        if lines[j].startswith("@router.") or (
            lines[j].startswith("async def ") or lines[j].startswith("def ")
        ) and j > start:
            end = j
            break
    rel = path.relative_to(REPO).as_posix()
    return f"`{rel}` — `{def_name}`\n\n{block(chr(10).join(lines[start:end]), 'python')}"


def extract_ts_range(path: Path, start_line: int, end_line: int, label: str) -> str:
    lines = read(path).splitlines()
    chunk = "\n".join(lines[start_line - 1 : end_line])
    rel = path.relative_to(REPO).as_posix()
    return f"**File:** `{rel}` **Lines:** {start_line}–{end_line}\n\n{block(chunk, 'typescript')}"


def sample_report_json() -> str:
    sample = {
        "executive_summary": (
            "Research confirms Guru and Notion AI directly compete with the proposed "
            "Slack HR bot. The handbook-staleness risk is evidenced by Reddit posts. "
            "No fatal barrier to launch exists, but the differentiation gap is narrow. "
            "Recommendation is to iterate on a specific wedge before proceeding."
        ),
        "questions_and_findings": [
            {
                "question_id": "q1",
                "question": "Does Guru already solve Slack policy questions for this audience?",
                "findings": [
                    {
                        "question_id": "q1",
                        "claim": "Guru provides Slack-based policy answering with 847 G2 reviews.",
                        "evidence_summary": (
                            "Guru's G2 listing (cited) shows 847 reviews at 4.5 stars, making it "
                            "the most-reviewed knowledge base tool with Slack integration."
                        ),
                        "citations": [
                            {
                                "url": "https://example.com/article",
                                "title": "Example Article Title",
                                "source_domain": "example.com",
                                "accessed_at": "2026-01-01T00:00:00+00:00",
                            }
                        ],
                        "confidence": "medium",
                        "confidence_rationale": "Backed by a single G2 listing; no independent corroboration.",
                    }
                ],
                "evidence_gap": None,
            }
        ],
        "competitors": [
            {
                "name": "Guru",
                "description": "A knowledge management tool with Slack integration.",
                "positioning_vs_idea": (
                    "Guru provides Slack-based Q&A from uploaded documents, directly overlapping "
                    "with the proposed Slack HR bot's core function."
                ),
                "citations": [
                    {
                        "url": "https://example.com/article",
                        "title": "Example Article Title",
                        "source_domain": "example.com",
                        "accessed_at": "2026-01-01T00:00:00+00:00",
                    }
                ],
            }
        ],
        "market_signals": (
            "The HR tech market has no reliable TAM figure in the search results. "
            "Guru's G2 presence (847 reviews) signals active buyer demand in this category."
        ),
        "distribution_signals": "Direct Slack App Directory listing is the primary distribution channel.",
        "regulatory_signals": None,
        "risks_assessment": (
            "The Guru/Notion AI competitor risk (q2) is confirmed — both tools provide "
            "Slack-based policy answering. The handbook-staleness risk (q1) is confirmed. "
            "Procurement complexity (q4) is partially confirmed by one Reddit thread."
        ),
        "overall_recommendation": "iterate",
        "recommendation_rationale": (
            "q2 confirms Guru covers the core use case for many buyers. q1 findings show "
            "the differentiation is in document freshness guarantees, not search."
        ),
        "research_limitations": "Market size data was not found in the search results.",
        "rubric_version_used": "v1",
    }
    return json.dumps(sample, indent=2)


def main() -> None:
    export_ts = FRONTEND / "lib" / "validation-report-export.ts"
    report_text_ts = FRONTEND / "lib" / "report-text.ts"

    parts: list[str] = [
        "# Bug 3 — Markdown Export Rendering — Investigation Dump\n\n",
        "Context: Markdown export shows leading-comma sentences and garbled market-stats "
        "prose. Export is **entirely client-side** — no backend markdown generation endpoint.\n\n",
        "## 1. Frontend export trigger\n\n",
        "**Component:** `frontend/components/research/ValidationReportExportMenu.tsx`\n\n",
        "**Parent:** `frontend/components/research/ReportCanvas.tsx` (also embedded toolbar)\n\n",
        "**Endpoint called for report data:** `GET /experiments/{id}/validation-report` "
        "(loaded earlier by ReportCanvas; export uses in-memory `ValidationReport`)\n\n",
        "**Markdown download:** No HTTP call — `downloadValidationReportMarkdown(report, "
        "projectName)` builds a Blob client-side and triggers browser download.\n\n",
        "**Conversion expression:** N/A (not a metrics export)\n\n",
        file_block(FRONTEND / "components/research/ValidationReportExportMenu.tsx"),
        "### `frontend/components/research/ReportCanvas.tsx` (parent — loads report, renders export menu)\n\n",
        block(read(FRONTEND / "components/research/ReportCanvas.tsx"), "tsx"),
        "## 2. API client wrapper\n\n",
        "**Relevant exports:** `getValidationReport` (data fetch only — not called at download click)\n\n",
        block(
            "\n".join(read(FRONTEND / "lib/api.ts").splitlines()[188:193]),
            "typescript",
        ),
        "### `frontend/lib/validation-report-export.ts` (markdown + HTML builders and download helpers)\n\n",
        block(read(export_ts), "typescript"),
        "## 3. Backend export route\n\n",
        "**No backend markdown export route exists.** Grep of `backend/app/routers/` and "
        "`backend/` found no `text/markdown` response, no `export-report` handler, and no "
        "`markdown_service`.\n\n",
        "The report JSON consumed by the frontend is served by:\n\n",
        extract_py_function(BACKEND / "app/routers/experiments.py", "get_validation_report"),
        "### `backend/app/db/models/validation_report.py` (persistence — `raw_report` JSONB)\n\n",
        block(read(BACKEND / "app/db/models/validation_report.py"), "python"),
        "## 4. Markdown renderer / template\n\n",
        "Markdown is built in TypeScript via string array concatenation in "
        "`buildValidationReportMarkdown()` — not Jinja, not Python f-strings, not mdutils.\n\n",
        "Text shaping helpers live in `frontend/lib/report-text.ts`.\n\n",
        file_block(report_text_ts),
        "## 5a. Leading-comma origin site\n\n",
        "The phrase `\", roadside assistance or walk-home safety, test trust mechanisms...\"` "
        "**does not appear anywhere in the repository** (grep across frontend + backend). "
        "It is LLM-generated prose stored on the `ValidationReport` and passed through export.\n\n",
        "Most likely path for a **leading comma before clause text**:\n\n",
        "1. Synthesizer emits risks_assessment (or recommendation_rationale / "
        "distribution_signals) with an empty leading clause before a comma, e.g. "
        'a string starting with ", roadside assistance..." or missing intro before that comma.\n'
        "2. `parseRiskAssessment()` treats text before the first `Risk N —` marker as "
        "`preamble` and exports it verbatim via `markdownRiskSection()` → `markdownParagraphs()`.\n\n",
        extract_ts_range(report_text_ts, 129, 159, "parseRiskAssessment preamble extraction"),
        extract_ts_range(report_text_ts, 581, 603, "markdownRiskSection"),
        extract_ts_range(export_ts, 716, 718, "risks_assessment export call"),
        "## 5b. Garbled market-stats origin site\n\n",
        "There is **no code that iterates evidence atoms or market signals into markdown "
        "prose**. `market_signals` is a single string field on `ValidationReport`, emitted "
        "by the synthesizer LLM and passed through `markdownParagraphs()`.\n\n",
        extract_ts_range(export_ts, 534, 538, "markdownParagraphs"),
        extract_ts_range(export_ts, 702, 714, "market_signals markdown blocks"),
        extract_ts_range(report_text_ts, 163, 194, "splitReadableParagraphs sentence splitter"),
        "**Upstream data generation** (synthesizer prompt instructs `market_signals` as "
        "2–4 sentences with figures — no concatenation in service code):\n\n",
        block(
            "\n".join(read(BACKEND / "app/llm/prompts/synthesizer.py").splitlines()[59:104]),
            "python",
        ),
        "### `backend/app/schemas/validation_report.py` — `market_signals` field definition\n\n",
        block(
            "\n".join(read(BACKEND / "app/schemas/validation_report.py").splitlines()[496:510]),
            "python",
        ),
        "## 6. Report data model\n\n",
        extract_interface(FRONTEND / "lib/types.ts", "ValidationReport"),
        extract_interface(FRONTEND / "lib/types.ts", "QuestionFindings"),
        extract_interface(FRONTEND / "lib/types.ts", "Finding"),
        extract_interface(FRONTEND / "lib/types.ts", "CompetitorMention"),
        extract_interface(FRONTEND / "lib/types.ts", "Citation"),
        extract_class(BACKEND / "app/schemas/validation_report.py", "ValidationReport"),
        extract_class(BACKEND / "app/schemas/validation_report.py", "QuestionFindings"),
        extract_class(BACKEND / "app/schemas/validation_report.py", "Finding"),
        extract_class(BACKEND / "app/schemas/validation_report.py", "CompetitorMention"),
        extract_class(BACKEND / "app/schemas/validation_report.py", "Citation"),
        extract_class(BACKEND / "app/db/models/validation_report.py", "ValidationReport"),
        "## 7. Sample fixture (if any)\n\n",
        "No committed JSON fixture files under `backend/tests/fixtures/` or `backend/tests/data/`. "
        "Representative `ValidationReport` built by `_make_valid_report()` in "
        "`backend/tests/schemas/test_validation_report.py`:\n\n",
        block(sample_report_json(), "json"),
        "## 8. HTML export path (for comparison, compact)\n\n",
        "**Route:** None (client-side `downloadValidationReportHtml` in "
        "`frontend/lib/validation-report-export.ts`)\n\n",
        "**Market signals HTML analog** (same `splitReadableParagraphs` + same "
        "`report.market_signals` string as markdown):\n\n",
        block(
            "\n".join(read(export_ts).splitlines()[350:377]),
            "typescript",
        ),
        "**Risk assessment HTML analog** (same `parseRiskAssessment` / `riskSectionHtml`):\n\n",
        block(
            "\n".join(read(export_ts).splitlines()[182:216]),
            "typescript",
        ),
        "## Notes\n\n",
        "1. **Download → Markdown click:** Triggers **no HTTP endpoint**. It calls "
        "`downloadValidationReportMarkdown(report, projectName)` which runs "
        "`buildValidationReportMarkdown()` locally and downloads a Blob as "
        "`{slug}-validation-report.md`. Report data was previously fetched via "
        "`GET /experiments/{id}/validation-report` when the canvas loaded.\n\n",
        "2. **Markdown generation method:** **(d) mix — all client-side TypeScript.** "
        "Section bodies use template literal / string-array building in "
        "`buildValidationReportMarkdown()`. Prose fields pass through "
        "`markdownParagraphs()` → `splitReadableParagraphs()`. Risk assessment uses "
        "`parseRiskAssessment()` then structured markdown assembly. No Jinja, no Python "
        "renderer, no mdutils.\n\n",
        "3. **Leading-comma string origin:** Not in repo source. It would appear in stored "
        "`ValidationReport.risks_assessment` (or another prose field) from the synthesizer. "
        "Export path: `report.risks_assessment` → `markdownRiskSection()` → if "
        "`parseRiskAssessment` finds `Risk N —` markers, text before the first marker becomes "
        "`preamble` (`report-text.ts` lines 136–140) → `markdownParagraphs(parsed.preamble)` "
        "with **no trim/guard for leading punctuation**. Upstream variable: synthesizer output "
        "text before the first risk marker (not a separate template variable in export code).\n\n",
        "4. **Garbled market-stats code (verbatim):** "
        "`marketBlocks.push(\"### Market overview\", \"\", markdownParagraphs(report.market_signals), \"\");` "
        "where `markdownParagraphs` is "
        "`const paragraphs = splitReadableParagraphs(text, maxChars); return paragraphs.map((paragraph) => \\`${paragraph}\\n\\`).join(\"\\n\");` "
        "— no atom iteration or number concatenation in export layer.\n\n",
        "5. **HTML export vs markdown for market stats:** **Same upstream string, same "
        "`splitReadableParagraphs` helper.** HTML uses `proseHtml(report.market_signals)`; "
        "markdown uses `markdownParagraphs(report.market_signals)`. If garbling appears in "
        "markdown only, it is not due to different market-stats rendering logic — both paths "
        "share `report-text.ts`. Any garbling is in the stored `market_signals` string and/or "
        "how `splitReadableParagraphs` splits number-heavy text.\n\n",
        "6. **Optional / nullable fields feeding these sites:** "
        "`distribution_signals: string | null` (default None), "
        "`regulatory_signals: string | null` (default None), "
        "`evidence_gap: str | None` per question (default None), "
        "`SectionScore.rationale: str | None`, "
        "`QuestionFindings.score: int | None`. "
        "`market_signals` and `risks_assessment` are **required non-null strings** "
        "(min_length 10 and 50). `recommendation_rationale` is required when recommendation "
        "is shown. Export does not substitute defaults for empty strings inside those fields.\n\n",
        "7. **Tests for markdown export:** **None found.** Grep found no tests for "
        "`buildValidationReportMarkdown`, `downloadValidationReportMarkdown`, or "
        "`parseRiskAssessment` in frontend or backend test suites.\n",
    ]

    OUT.write_text("".join(parts), encoding="utf-8")
    print(f"Wrote {OUT} ({OUT.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
