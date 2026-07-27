"""Deterministic rendering + concurrency logic for the editable-doc surface.

This module owns all business logic for the founder-editable validation-report
document. The experiments router handlers stay thin (5–15 lines) and delegate
here. No DB I/O happens in this module — handlers load/commit; this module
operates on already-loaded ORM rows and Pydantic models.

Two responsibilities:

1. `render_report_to_prosemirror_doc` — deterministic render of a
   `ValidationReport` (the immutable `raw_report` payload) into canonical
   ProseMirror-doc JSON. Deterministic means: identical input → byte-identical
   `json.dumps(doc, sort_keys=False, ensure_ascii=False)`. Nodes are appended in
   a fixed order; nothing depends on dict/set iteration order.

2. `build_edited_doc_response` / `apply_edited_doc_patch` — the read view and the
   compare-and-swap write. `raw_report` is never mutated; the persisted overlay
   lives in the separate `edited_doc` column.

Rendering rules (per PR spec):
- Only standard ProseMirror nodes: doc, heading, paragraph, text, bulletList,
  listItem, horizontalRule (+ bold/italic marks). No Tiptap dependency here.
- Sections whose source field is None or empty are skipped entirely — no empty
  headings are emitted.
- Section-score numeric scores are metadata and are NEVER rendered into the doc.
  The "Scoring Detail" section renders only label, rationale, pros, cons.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from app.schemas.validation_report import (
    Citation,
    ValidationReport,
)

if TYPE_CHECKING:
    from app.db.models.validation_report import (
        ValidationReport as ValidationReportRow,
    )


# ---------------------------------------------------------------------------
# ProseMirror node builders
# ---------------------------------------------------------------------------


def _text(value: str) -> dict[str, Any]:
    return {"type": "text", "text": value}


def _text_marked(value: str, mark: str) -> dict[str, Any]:
    return {"type": "text", "marks": [{"type": mark}], "text": value}


def _paragraph(content: list[dict[str, Any]]) -> dict[str, Any]:
    return {"type": "paragraph", "content": content}


def _paragraph_text(value: str) -> dict[str, Any]:
    return {"type": "paragraph", "content": [_text(value)]}


def _heading(level: int, value: str) -> dict[str, Any]:
    return {"type": "heading", "attrs": {"level": level}, "content": [_text(value)]}


def _bullet_list(items: list[str]) -> dict[str, Any]:
    return {
        "type": "bulletList",
        "content": [
            {"type": "listItem", "content": [_paragraph_text(item)]} for item in items
        ],
    }


def _ordered_domains(citations: list[Citation]) -> list[str]:
    """Unique source domains in citation order (dedup preserves determinism)."""
    domains: list[str] = []
    for citation in citations:
        domain = citation.source_domain
        if domain and domain not in domains:
            domains.append(domain)
    return domains


# ---------------------------------------------------------------------------
# Deterministic renderer
# ---------------------------------------------------------------------------


def render_report_to_prosemirror_doc(report: ValidationReport) -> dict[str, Any]:
    """Render an immutable ValidationReport into canonical ProseMirror-doc JSON.

    Deterministic: nodes are appended in a fixed order and no output depends on
    dict/set iteration order. Empty/None source fields are skipped so no empty
    headings appear. Numeric scores are intentionally omitted (metadata only).
    """
    content: list[dict[str, Any]] = []

    # Executive Summary (required).
    content.append(_heading(1, "Executive Summary"))
    content.append(_paragraph_text(report.executive_summary))

    # Questions & Findings (required, 5–7 blocks).
    content.append(_heading(1, "Questions & Findings"))
    for qf in report.questions_and_findings:
        content.append(_heading(2, f"{qf.question_id.upper()}. {qf.question}"))
        for finding in qf.findings:
            content.append(_heading(3, finding.claim))
            evidence_nodes: list[dict[str, Any]] = [_text(finding.evidence_summary)]
            domains = _ordered_domains(finding.citations)
            if domains:
                evidence_nodes.append(_text(" "))
                evidence_nodes.append(_text_marked(f"({', '.join(domains)})", "italic"))
            content.append(_paragraph(evidence_nodes))
            content.append(
                _paragraph(
                    [
                        _text_marked("Confidence: ", "bold"),
                        _text(f"{finding.confidence} — {finding.confidence_rationale}"),
                    ]
                )
            )
        if qf.evidence_gap:
            content.append(
                _paragraph(
                    [_text_marked("Evidence gap: ", "bold"), _text(qf.evidence_gap)]
                )
            )

    # Competitors (skip entirely when the list is empty).
    if report.competitors:
        content.append(_heading(1, "Competitors"))
        for competitor in report.competitors:
            content.append(_heading(3, competitor.name))
            content.append(_paragraph_text(competitor.description))
            content.append(_paragraph_text(competitor.positioning_vs_idea))
            domains = _ordered_domains(competitor.citations)
            if domains:
                content.append(
                    _paragraph([_text_marked(f"({', '.join(domains)})", "italic")])
                )

    # Market Signals (required).
    content.append(_heading(1, "Market Signals"))
    content.append(_paragraph_text(report.market_signals))

    # Distribution Signals (optional).
    if report.distribution_signals:
        content.append(_heading(1, "Distribution Signals"))
        content.append(_paragraph_text(report.distribution_signals))

    # Regulatory Signals (optional).
    if report.regulatory_signals:
        content.append(_heading(1, "Regulatory Signals"))
        content.append(_paragraph_text(report.regulatory_signals))

    # Risks Assessment (required).
    content.append(_heading(1, "Risks Assessment"))
    content.append(_paragraph_text(report.risks_assessment))

    # Recommendation Rationale (required).
    content.append(_heading(1, "Recommendation Rationale"))
    content.append(_paragraph_text(report.recommendation_rationale))

    # Research Limitations (required).
    content.append(_heading(1, "Research Limitations"))
    content.append(_paragraph_text(report.research_limitations))

    # Voices (optional) — placed after Research Limitations, before Scoring Detail.
    if report.voices:
        content.append(_heading(1, "Voices"))
        content.append(_paragraph_text(report.voices))

    # Scoring Detail (skip when there are no section scores). Numeric scores are
    # metadata served by the /validation-report endpoint — never rendered here.
    if report.section_scores:
        content.append(_heading(1, "Scoring Detail"))
        for section in report.section_scores:
            content.append(_heading(3, section.label))
            if section.rationale:
                content.append(_paragraph_text(section.rationale))
            if section.pros:
                content.append(_paragraph([_text_marked("Pros", "bold")]))
                content.append(_bullet_list(list(section.pros)))
            if section.cons:
                content.append(_paragraph([_text_marked("Cons", "bold")]))
                content.append(_bullet_list(list(section.cons)))

    # TODO(PR-later): business_construction rendering. Excluded from PR 1 —
    # it is a structured artifact, not narrative prose, and needs its own node
    # design. Do not surface it in this doc or the response until then.

    return {"type": "doc", "content": content}


# ---------------------------------------------------------------------------
# ProseMirror → plain prose (for landing strategist input)
# ---------------------------------------------------------------------------


def flatten_prosemirror_doc(doc: dict[str, Any] | None) -> str | None:
    """Walk a ProseMirror JSON doc into markdown-ish plain prose.

    Returns None when ``doc`` is None. Unknown node types recurse into
    ``content`` when present; otherwise they contribute nothing. Marks on
    text nodes are ignored.
    """
    if doc is None:
        return None

    def _text_of(node: dict[str, Any]) -> str:
        parts: list[str] = []
        for child in node.get("content") or []:
            if not isinstance(child, dict):
                continue
            ctype = child.get("type")
            if ctype == "text":
                parts.append(str(child.get("text") or ""))
            elif ctype == "hardBreak":
                parts.append("\n")
            else:
                parts.append(_text_of(child))
        return "".join(parts)

    def _walk(node: dict[str, Any]) -> str:
        ntype = node.get("type")
        children = [c for c in (node.get("content") or []) if isinstance(c, dict)]

        if ntype == "doc":
            return "".join(_walk(c) for c in children)

        if ntype == "heading":
            attrs = node.get("attrs") if isinstance(node.get("attrs"), dict) else {}
            level = attrs.get("level", 1)
            try:
                level_int = max(1, int(level))
            except (TypeError, ValueError):
                level_int = 1
            return f"{'#' * level_int} {_text_of(node)}\n\n"

        if ntype == "paragraph":
            return f"{_text_of(node)}\n\n"

        if ntype == "blockquote":
            inner = "".join(_walk(c) for c in children).rstrip("\n")
            if not inner:
                return ""
            quoted = "\n".join(f"> {line}" for line in inner.split("\n"))
            return f"{quoted}\n\n"

        if ntype == "bulletList":
            lines: list[str] = []
            for item in children:
                lines.append(f"- {_text_of(item).strip()}")
            return "\n".join(lines) + "\n\n"

        if ntype == "orderedList":
            lines = []
            for i, item in enumerate(children, start=1):
                lines.append(f"{i}. {_text_of(item).strip()}")
            return "\n".join(lines) + "\n\n"

        if ntype == "listItem":
            return "".join(_walk(c) for c in children)

        if ntype == "horizontalRule":
            return "---\n\n"

        if ntype == "hardBreak":
            return "\n"

        if ntype == "text":
            return str(node.get("text") or "")

        # Unknown node: recurse content if present.
        if children:
            return "".join(_walk(c) for c in children)
        return ""

    if not isinstance(doc, dict):
        return None
    return _walk(doc).rstrip()


# ---------------------------------------------------------------------------
# Staleness + read view
# ---------------------------------------------------------------------------


def edited_doc_behind_regeneration(report: ValidationReportRow) -> bool:
    """True when a persisted edit predates the latest research regeneration.

    A persisted overlay is stale if it was last edited before `raw_report` was
    (re)generated — i.e. edited_at < generated_at. Never stale when there is no
    persisted overlay.
    """
    if report.edited_doc is None or report.edited_at is None:
        return False
    return report.edited_at < report.generated_at


def build_edited_doc_response(report: ValidationReportRow) -> dict[str, Any]:
    """Build the {doc, version, source, edited_doc_behind_regeneration} view.

    Returns the persisted overlay when present, otherwise a live deterministic
    render of the immutable raw_report. `raw_report` is never mutated.
    """
    if report.edited_doc is not None:
        return {
            "doc": report.edited_doc,
            "version": report.edited_doc_version,
            "source": "persisted",
            "edited_doc_behind_regeneration": edited_doc_behind_regeneration(report),
        }
    parsed = ValidationReport.model_validate(report.raw_report)
    return {
        "doc": render_report_to_prosemirror_doc(parsed),
        "version": report.edited_doc_version,
        "source": "generated",
        "edited_doc_behind_regeneration": False,
    }


# ---------------------------------------------------------------------------
# Compare-and-swap write
# ---------------------------------------------------------------------------


class EditedDocVersionConflict(Exception):
    """Raised when a PATCH base_version does not match the row's current version.

    Carries the authoritative current_version so the handler can return it to the
    client for a programmatic retry.
    """

    def __init__(self, current_version: int) -> None:
        self.current_version = current_version
        super().__init__(f"edited_doc_version conflict: current={current_version}")


def apply_edited_doc_patch(
    report: ValidationReportRow,
    *,
    doc: dict[str, Any],
    base_version: int,
) -> None:
    """Compare-and-swap the edited overlay onto the ORM row (no commit).

    Succeeds only when base_version equals the row's current edited_doc_version.
    The first edit (base_version=0 against a never-edited row) transitions the
    row from "generated" to "persisted" and sets version to 1. Sets edited_at
    explicitly to now(UTC). Does not touch raw_report. The caller commits.
    """
    if base_version != report.edited_doc_version:
        raise EditedDocVersionConflict(report.edited_doc_version)
    report.edited_doc = doc
    report.edited_doc_version = report.edited_doc_version + 1
    report.edited_at = datetime.now(UTC)
