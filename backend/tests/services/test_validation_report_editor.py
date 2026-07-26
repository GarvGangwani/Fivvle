"""Unit tests for app.services.validation_report_editor.

Covers:
- Deterministic render (byte-equal json.dumps twice, sort_keys=False).
- All narrative fields surface in the doc.
- Optional/empty sections are skipped (no empty headings).
- Numeric scores are NEVER rendered into the doc.
- is_stale_since_regeneration truth table.
- apply_edited_doc_patch CAS success, first-edit transition, and conflict.
- build_edited_doc_response source selection (generated vs persisted).

These are pure-logic tests — no DB, no network. A lightweight namespace stands
in for the ValidationReport ORM row where only attribute access is needed.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any

import pytest

from app.schemas.validation_report import (
    Citation,
    CompetitorMention,
    Finding,
    QuestionFindings,
    SectionScore,
    ValidationReport,
)
from app.services.validation_report_editor import (
    EditedDocVersionConflict,
    apply_edited_doc_patch,
    build_edited_doc_response,
    flatten_prosemirror_doc,
    is_stale_since_regeneration,
    render_report_to_prosemirror_doc,
)

_NOW = datetime(2026, 7, 16, 12, 0, 0, tzinfo=UTC)


# ---------------------------------------------------------------------------
# Report factory
# ---------------------------------------------------------------------------


def _citation(domain: str = "example.com") -> Citation:
    return Citation(
        url=f"https://{domain}/article",
        title="Example Article",
        source_domain=domain,
        accessed_at=_NOW,
    )


def _finding(qid: str, claim: str, domain: str = "reddit.com") -> Finding:
    return Finding(
        question_id=qid,
        claim=claim,
        evidence_summary=f"Evidence paraphrase for {claim}",
        citations=[_citation(domain)],
        confidence="medium",
        confidence_rationale="Backed by a single corroborating source.",
    )


def _make_report(**overrides: Any) -> ValidationReport:
    """A fully populated ValidationReport with all optional sections set."""
    qids = [f"q{i}" for i in range(1, 6)]
    data: dict[str, Any] = {
        "executive_summary": (
            "EXEC_SUMMARY_MARKER: research shows narrow differentiation with a viable wedge "
            "and no fatal barrier; recommendation is to iterate before proceeding."
        ),
        "questions_and_findings": [
            QuestionFindings(
                question_id=qid,
                question=f"QUESTION_MARKER_{qid}?",
                findings=[_finding(qid, f"CLAIM_MARKER_{qid}")],
                evidence_gap=(f"GAP_MARKER_{qid}" if qid == "q1" else None),
            )
            for qid in qids
        ],
        "competitors": [
            CompetitorMention(
                name="COMPETITOR_MARKER",
                description="A competing tool in the same space.",
                positioning_vs_idea="POSITIONING_MARKER against the idea.",
                citations=[_citation("g2.com")],
            )
        ],
        "market_signals": "MARKET_MARKER: active buyer demand with no reliable TAM figure.",
        "distribution_signals": "DISTRIBUTION_MARKER: app directory listing is primary.",
        "regulatory_signals": "REGULATORY_MARKER: no material compliance angle found.",
        "risks_assessment": (
            "RISKS_MARKER: competitor risk confirmed, staleness risk confirmed, "
            "procurement complexity partially confirmed."
        ),
        "overall_recommendation": "iterate",
        "recommendation_rationale": (
            "RATIONALE_MARKER: q2 confirms core use case coverage; iterate on the freshness wedge."
        ),
        "research_limitations": "LIMITATIONS_MARKER: market size data not found.",
        "voices": "VOICES_MARKER: founders on r/ops describe the same weekly interruption.",
        "rubric_version_used": "v1",
        "section_scores": [
            SectionScore(
                section_id="market",
                label="SECTION_LABEL_MARKET",
                score=73,
                rationale="RATIONALE_MARKET_MARKER",
                pros=["PRO_MARKET_MARKER"],
                cons=["CON_MARKET_MARKER"],
            ),
            SectionScore(
                section_id="research",
                label="SECTION_LABEL_RESEARCH",
                score=41,
                rationale=None,
                pros=[],
                cons=[],
            ),
        ],
        "overall_score": 62,
    }
    data.update(overrides)
    return ValidationReport(**data)


# ---------------------------------------------------------------------------
# Doc traversal helper
# ---------------------------------------------------------------------------


def _collect_text(node: Any) -> list[str]:
    out: list[str] = []
    if isinstance(node, dict):
        if node.get("type") == "text":
            out.append(node.get("text", ""))
        for child in node.get("content", []) or []:
            out.extend(_collect_text(child))
    return out


def _heading_texts(doc: dict[str, Any]) -> list[str]:
    out: list[str] = []
    for node in doc["content"]:
        if node.get("type") == "heading":
            out.append("".join(_collect_text(node)))
    return out


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


def test_render_is_byte_deterministic() -> None:
    """Rendering the same report twice yields byte-identical JSON.

    Uses sort_keys=False deliberately: a key-ordering bug must NOT be masked.
    """
    report = _make_report()
    first = json.dumps(
        render_report_to_prosemirror_doc(report), sort_keys=False, ensure_ascii=False
    )
    second = json.dumps(
        render_report_to_prosemirror_doc(report), sort_keys=False, ensure_ascii=False
    )
    assert first == second


def test_render_root_is_prosemirror_doc() -> None:
    doc = render_report_to_prosemirror_doc(_make_report())
    assert doc["type"] == "doc"
    assert isinstance(doc["content"], list)


# ---------------------------------------------------------------------------
# Content coverage
# ---------------------------------------------------------------------------


def test_all_narrative_fields_present() -> None:
    doc = render_report_to_prosemirror_doc(_make_report())
    text = " ".join(_collect_text(doc))
    for marker in (
        "EXEC_SUMMARY_MARKER",
        "QUESTION_MARKER_q1",
        "CLAIM_MARKER_q1",
        "GAP_MARKER_q1",
        "COMPETITOR_MARKER",
        "POSITIONING_MARKER",
        "MARKET_MARKER",
        "DISTRIBUTION_MARKER",
        "REGULATORY_MARKER",
        "RISKS_MARKER",
        "RATIONALE_MARKER",
        "LIMITATIONS_MARKER",
        "VOICES_MARKER",
        "SECTION_LABEL_MARKET",
        "RATIONALE_MARKET_MARKER",
        "PRO_MARKET_MARKER",
        "CON_MARKET_MARKER",
    ):
        assert marker in text, f"missing {marker}"


def test_question_id_is_uppercased_in_heading() -> None:
    doc = render_report_to_prosemirror_doc(_make_report())
    headings = _heading_texts(doc)
    assert any(h.startswith("Q1. ") for h in headings)


def test_section_headings_in_expected_order() -> None:
    doc = render_report_to_prosemirror_doc(_make_report())
    h1s = [
        "".join(_collect_text(n))
        for n in doc["content"]
        if n.get("type") == "heading" and n["attrs"]["level"] == 1
    ]
    assert h1s == [
        "Executive Summary",
        "Questions & Findings",
        "Competitors",
        "Market Signals",
        "Distribution Signals",
        "Regulatory Signals",
        "Risks Assessment",
        "Recommendation Rationale",
        "Research Limitations",
        "Voices",
        "Scoring Detail",
    ]


def test_domains_rendered_as_italic_parenthetical() -> None:
    doc = render_report_to_prosemirror_doc(_make_report())
    # Find an italic text node containing a domain.
    italics: list[str] = []
    for node in _iter_nodes(doc):
        if node.get("type") == "text" and any(
            m.get("type") == "italic" for m in node.get("marks", []) or []
        ):
            italics.append(node["text"])
    assert any("reddit.com" in t for t in italics)
    assert any("g2.com" in t for t in italics)


def _iter_nodes(node: Any):
    if isinstance(node, dict):
        yield node
        for child in node.get("content", []) or []:
            yield from _iter_nodes(child)


# ---------------------------------------------------------------------------
# Skip rules
# ---------------------------------------------------------------------------


def test_optional_sections_skipped_when_none() -> None:
    report = _make_report(
        distribution_signals=None,
        regulatory_signals=None,
        voices=None,
        competitors=[],
    )
    doc = render_report_to_prosemirror_doc(report)
    headings = _heading_texts(doc)
    assert "Distribution Signals" not in headings
    assert "Regulatory Signals" not in headings
    assert "Voices" not in headings
    assert "Competitors" not in headings


def test_empty_string_optional_sections_skipped() -> None:
    # distribution_signals as empty string must also be skipped (falsy source).
    report = _make_report(distribution_signals="")
    doc = render_report_to_prosemirror_doc(report)
    assert "Distribution Signals" not in _heading_texts(doc)


def test_scoring_detail_skipped_when_no_section_scores() -> None:
    report = _make_report(section_scores=[])
    doc = render_report_to_prosemirror_doc(report)
    assert "Scoring Detail" not in _heading_texts(doc)


def test_evidence_gap_skipped_when_none() -> None:
    report = _make_report()
    doc = render_report_to_prosemirror_doc(report)
    text = " ".join(_collect_text(doc))
    # Only q1 has a gap in the factory; q2 has none → no stray gap marker.
    assert "GAP_MARKER_q2" not in text


def test_section_score_rationale_and_bullets_skipped_when_empty() -> None:
    # The "research" section in the factory has no rationale/pros/cons.
    doc = render_report_to_prosemirror_doc(_make_report())
    nodes = list(_iter_nodes(doc))
    # Find the RESEARCH label heading; ensure no "Pros"/"Cons" belong to it by
    # confirming there is exactly one Pros and one Cons in the whole doc (market only).
    bold_texts = [
        n["text"]
        for n in nodes
        if n.get("type") == "text"
        and any(m.get("type") == "bold" for m in n.get("marks", []) or [])
    ]
    assert bold_texts.count("Pros") == 1
    assert bold_texts.count("Cons") == 1


# ---------------------------------------------------------------------------
# Numeric scores must never appear in the doc
# ---------------------------------------------------------------------------


def test_numeric_scores_not_rendered() -> None:
    report = _make_report()
    doc = render_report_to_prosemirror_doc(report)
    texts = _collect_text(doc)
    for forbidden in ("73", "41", "62"):
        assert all(forbidden not in t for t in texts), f"numeric score {forbidden} leaked into doc"


# ---------------------------------------------------------------------------
# is_stale_since_regeneration
# ---------------------------------------------------------------------------


def test_stale_false_when_no_edited_doc() -> None:
    row = SimpleNamespace(
        edited_doc=None, edited_at=None, generated_at=_NOW
    )
    assert is_stale_since_regeneration(row) is False


def test_stale_false_when_edit_after_regeneration() -> None:
    row = SimpleNamespace(
        edited_doc={"type": "doc", "content": []},
        edited_at=_NOW + timedelta(hours=1),
        generated_at=_NOW,
    )
    assert is_stale_since_regeneration(row) is False


def test_stale_true_when_edit_before_regeneration() -> None:
    row = SimpleNamespace(
        edited_doc={"type": "doc", "content": []},
        edited_at=_NOW - timedelta(hours=1),
        generated_at=_NOW,
    )
    assert is_stale_since_regeneration(row) is True


# ---------------------------------------------------------------------------
# build_edited_doc_response source selection
# ---------------------------------------------------------------------------


def test_response_source_generated_when_no_overlay() -> None:
    raw = _make_report().model_dump(mode="json")
    row = SimpleNamespace(
        raw_report=raw,
        edited_doc=None,
        edited_doc_version=0,
        edited_at=None,
        generated_at=_NOW,
    )
    view = build_edited_doc_response(row)
    assert view["source"] == "generated"
    assert view["version"] == 0
    assert view["is_stale_since_regeneration"] is False
    assert view["doc"]["type"] == "doc"


def test_response_source_persisted_when_overlay_present() -> None:
    raw = _make_report().model_dump(mode="json")
    overlay = {"type": "doc", "content": [{"type": "paragraph", "content": []}]}
    row = SimpleNamespace(
        raw_report=raw,
        edited_doc=overlay,
        edited_doc_version=3,
        edited_at=_NOW + timedelta(hours=1),
        generated_at=_NOW,
    )
    view = build_edited_doc_response(row)
    assert view["source"] == "persisted"
    assert view["version"] == 3
    assert view["doc"] == overlay


# ---------------------------------------------------------------------------
# apply_edited_doc_patch — CAS
# ---------------------------------------------------------------------------


def test_patch_first_edit_transitions_generated_to_persisted() -> None:
    row = SimpleNamespace(edited_doc=None, edited_doc_version=0, edited_at=None)
    new_doc = {"type": "doc", "content": []}
    apply_edited_doc_patch(row, doc=new_doc, base_version=0)
    assert row.edited_doc == new_doc
    assert row.edited_doc_version == 1
    assert isinstance(row.edited_at, datetime)
    assert row.edited_at.tzinfo is not None


def test_patch_increments_version_on_match() -> None:
    row = SimpleNamespace(
        edited_doc={"type": "doc", "content": []}, edited_doc_version=4, edited_at=_NOW
    )
    apply_edited_doc_patch(row, doc={"type": "doc", "content": [{"type": "paragraph"}]}, base_version=4)
    assert row.edited_doc_version == 5


def test_patch_conflict_raises_with_current_version() -> None:
    row = SimpleNamespace(
        edited_doc={"type": "doc", "content": []}, edited_doc_version=7, edited_at=_NOW
    )
    with pytest.raises(EditedDocVersionConflict) as exc:
        apply_edited_doc_patch(row, doc={"type": "doc", "content": []}, base_version=2)
    assert exc.value.current_version == 7
    # Row is untouched on conflict.
    assert row.edited_doc_version == 7


# ---------------------------------------------------------------------------
# flatten_prosemirror_doc
# ---------------------------------------------------------------------------


def test_flatten_none_returns_none() -> None:
    assert flatten_prosemirror_doc(None) is None


def test_flatten_empty_doc() -> None:
    assert flatten_prosemirror_doc({"type": "doc", "content": []}) == ""


def test_flatten_headings_and_paragraphs() -> None:
    doc = {
        "type": "doc",
        "content": [
            {
                "type": "heading",
                "attrs": {"level": 1},
                "content": [{"type": "text", "text": "Title"}],
            },
            {
                "type": "paragraph",
                "content": [{"type": "text", "text": "Hello world."}],
            },
        ],
    }
    out = flatten_prosemirror_doc(doc)
    assert out == "# Title\n\nHello world."


def test_flatten_mixed_lists() -> None:
    doc = {
        "type": "doc",
        "content": [
            {
                "type": "bulletList",
                "content": [
                    {
                        "type": "listItem",
                        "content": [
                            {
                                "type": "paragraph",
                                "content": [{"type": "text", "text": "One"}],
                            }
                        ],
                    },
                    {
                        "type": "listItem",
                        "content": [
                            {
                                "type": "paragraph",
                                "content": [{"type": "text", "text": "Two"}],
                            }
                        ],
                    },
                ],
            },
            {
                "type": "orderedList",
                "content": [
                    {
                        "type": "listItem",
                        "content": [
                            {
                                "type": "paragraph",
                                "content": [{"type": "text", "text": "Alpha"}],
                            }
                        ],
                    }
                ],
            },
        ],
    }
    out = flatten_prosemirror_doc(doc)
    assert out is not None
    assert "- One" in out
    assert "- Two" in out
    assert "1. Alpha" in out


def test_flatten_nested_list() -> None:
    doc = {
        "type": "doc",
        "content": [
            {
                "type": "bulletList",
                "content": [
                    {
                        "type": "listItem",
                        "content": [
                            {
                                "type": "paragraph",
                                "content": [{"type": "text", "text": "Parent"}],
                            },
                            {
                                "type": "bulletList",
                                "content": [
                                    {
                                        "type": "listItem",
                                        "content": [
                                            {
                                                "type": "paragraph",
                                                "content": [
                                                    {"type": "text", "text": "Child"}
                                                ],
                                            }
                                        ],
                                    }
                                ],
                            },
                        ],
                    }
                ],
            }
        ],
    }
    out = flatten_prosemirror_doc(doc)
    assert out is not None
    assert "Parent" in out
    assert "Child" in out


def test_flatten_unknown_node_does_not_crash() -> None:
    doc = {
        "type": "doc",
        "content": [
            {
                "type": "customWeirdNode",
                "content": [
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": "Survives"}],
                    }
                ],
            }
        ],
    }
    out = flatten_prosemirror_doc(doc)
    assert out is not None
    assert "Survives" in out
