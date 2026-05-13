"""Unit tests for app.schemas.validation_report.

Exercises the schema constraints for ValidationReport and all sub-models,
including the Draft variants added in B2.3-fix.

Tests:
  1.  Valid ValidationReport accepted
  2.  Finding rejected with empty citations list
  3.  Finding rejected with missing question_id
  4.  CompetitorMention rejected with empty citations list
  5.  ValidationReport rejected with too few questions_and_findings (<5)
  6.  ValidationReport rejected with too many questions_and_findings (>7)
  7.  Citation URL validation rejects non-http(s) URLs
  8.  Citation URL validation accepts http:// and https:// URLs
  9.  Finding.claim max char constraint fires
  10. Finding.evidence_summary max char constraint fires (max 400)
  11. Finding.confidence_rationale max char constraint fires (max 150)
  12. ValidationReport.executive_summary max char constraint fires
  13. ValidationReport.recommendation_rationale max char constraint fires
  14. ValidationReport.risks_assessment max char constraint fires
  15. ValidationReport.research_limitations max char constraint fires
  16. CompetitorMention rejected with >2 citations
  17. QuestionFindings.question_id pattern constraint (must be q1-q7)
  18. Duplicate question_ids in questions_and_findings rejected
  19. extra="forbid" on Citation rejects unknown fields
  20. overall_recommendation only accepts valid literals
  21. ValidationReport.competitors max 6 (not 10)
  22. FindingDraft: rejects empty citations, rejects >3, accepts valid URLs, rejects non-http
  23. CompetitorMentionDraft: rejects empty citations, rejects >2 citations
  24. ValidationReportDraft: 5-7 questions count, duplicate-id rejection
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pytest
from pydantic import ValidationError

from app.schemas.validation_report import (
    Citation,
    CompetitorMention,
    CompetitorMentionDraft,
    Finding,
    FindingDraft,
    QuestionFindings,
    QuestionFindingsDraft,
    ValidationReport,
    ValidationReportDraft,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_NOW = datetime.now(tz=timezone.utc)


def _make_citation(**overrides: Any) -> Citation:
    defaults: dict[str, Any] = {
        "url": "https://example.com/article",
        "title": "Example Article Title",
        "source_domain": "example.com",
        "accessed_at": _NOW,
    }
    defaults.update(overrides)
    return Citation(**defaults)


def _make_finding(question_id: str = "q1", **overrides: Any) -> Finding:
    defaults: dict[str, Any] = {
        "question_id": question_id,
        "claim": "Guru provides Slack-based policy answering with 847 G2 reviews.",
        "evidence_summary": (
            "Guru's G2 listing (cited) shows 847 reviews at 4.5 stars, making it "
            "the most-reviewed knowledge base tool with Slack integration."
        ),
        "citations": [_make_citation()],
        "confidence": "medium",
        "confidence_rationale": "Backed by a single G2 listing; no independent corroboration.",
    }
    defaults.update(overrides)
    return Finding(**defaults)


def _make_question_findings(question_id: str = "q1", **overrides: Any) -> QuestionFindings:
    defaults: dict[str, Any] = {
        "question_id": question_id,
        "question": "Does Guru already solve Slack policy questions for this audience?",
        "findings": [_make_finding(question_id)],
        "evidence_gap": None,
    }
    defaults.update(overrides)
    return QuestionFindings(**defaults)


def _make_competitor(**overrides: Any) -> CompetitorMention:
    defaults: dict[str, Any] = {
        "name": "Guru",
        "description": "A knowledge management tool with Slack integration.",
        "positioning_vs_idea": (
            "Guru provides Slack-based Q&A from uploaded documents, directly overlapping "
            "with the proposed Slack HR bot's core function."
        ),
        "citations": [_make_citation()],
    }
    defaults.update(overrides)
    return CompetitorMention(**defaults)


def _make_valid_report(question_count: int = 5) -> ValidationReport:
    """Build a valid ValidationReport with question_count QuestionFindings."""
    qids = [f"q{i}" for i in range(1, question_count + 1)]
    return ValidationReport(
        executive_summary=(
            "Research confirms Guru and Notion AI directly compete with the proposed "
            "Slack HR bot. The handbook-staleness risk is evidenced by Reddit posts. "
            "No fatal barrier to launch exists, but the differentiation gap is narrow. "
            "Recommendation is to iterate on a specific wedge before proceeding."
        ),
        questions_and_findings=[_make_question_findings(qid) for qid in qids],
        competitors=[_make_competitor()],
        market_signals=(
            "The HR tech market has no reliable TAM figure in the search results. "
            "Guru's G2 presence (847 reviews) signals active buyer demand in this category."
        ),
        distribution_signals="Direct Slack App Directory listing is the primary distribution channel.",
        regulatory_signals=None,
        risks_assessment=(
            "The Guru/Notion AI competitor risk (q2) is confirmed — both tools provide "
            "Slack-based policy answering. The handbook-staleness risk (q1) is confirmed. "
            "Procurement complexity (q4) is partially confirmed by one Reddit thread."
        ),
        overall_recommendation="iterate",
        recommendation_rationale=(
            "q2 confirms Guru covers the core use case for many buyers. q1 findings show "
            "the differentiation is in document freshness guarantees, not search. Iteration "
            "should focus on the 'always current handbook' wedge rather than generic Q&A."
        ),
        research_limitations="Market size data was not found in the search results.",
        rubric_version_used="v1",
    )


# ---------------------------------------------------------------------------
# 1. Valid ValidationReport accepted
# ---------------------------------------------------------------------------


def test_valid_validation_report_accepted() -> None:
    """A fully valid ValidationReport with 5 questions should be accepted."""
    report = _make_valid_report(5)
    assert len(report.questions_and_findings) == 5
    assert report.overall_recommendation == "iterate"
    assert report.rubric_version_used == "v1"


def test_valid_validation_report_with_seven_questions() -> None:
    """A ValidationReport with 7 questions (maximum) should be accepted."""
    report = _make_valid_report(7)
    assert len(report.questions_and_findings) == 7


def test_valid_all_recommendation_types() -> None:
    """All five recommendation literals should be accepted."""
    for rec in ("proceed", "iterate", "pivot", "kill", "too_vague_to_recommend"):
        r = _make_valid_report()
        r2 = r.model_copy(update={"overall_recommendation": rec})
        assert r2.overall_recommendation == rec


# ---------------------------------------------------------------------------
# 2. Finding rejected with empty citations list
# ---------------------------------------------------------------------------


def test_finding_rejects_empty_citations() -> None:
    """Finding with citations=[] should raise ValidationError (min_length=1)."""
    with pytest.raises(ValidationError) as exc_info:
        Finding(
            question_id="q1",
            claim="Guru provides Slack-based policy answering.",
            evidence_summary="Guru's G2 page shows 847 reviews.",
            citations=[],  # violates min_length=1
            confidence="medium",
            confidence_rationale="Single G2 listing.",
        )
    errors = exc_info.value.errors()
    assert any(e["loc"] == ("citations",) for e in errors)


def test_finding_rejects_more_than_three_citations() -> None:
    """Finding with 4 citations should raise ValidationError (max_length=3)."""
    four_citations = [_make_citation() for _ in range(4)]
    with pytest.raises(ValidationError):
        Finding(
            question_id="q1",
            claim="Guru provides Slack-based policy answering.",
            evidence_summary="Guru's G2 page shows 847 reviews.",
            citations=four_citations,
            confidence="medium",
            confidence_rationale="Four sources cited.",
        )


# ---------------------------------------------------------------------------
# 3. Finding rejected with missing question_id
# ---------------------------------------------------------------------------


def test_finding_rejects_missing_question_id() -> None:
    """Finding without question_id should raise ValidationError."""
    with pytest.raises(ValidationError) as exc_info:
        Finding(
            # question_id missing
            claim="Guru provides Slack-based policy answering.",
            evidence_summary="Guru's G2 page shows 847 reviews.",
            citations=[_make_citation()],
            confidence="medium",
            confidence_rationale="Single G2 listing.",
        )
    errors = exc_info.value.errors()
    assert any(e["loc"] == ("question_id",) for e in errors)


@pytest.mark.parametrize(
    "bad_id",
    ["q0", "q8", "Q1", "question1", "1", ""],
)
def test_finding_rejects_malformed_question_id(bad_id: str) -> None:
    """Finding.question_id not matching ^q[1-7]$ should raise ValidationError."""
    with pytest.raises(ValidationError):
        Finding(
            question_id=bad_id,
            claim="Guru provides Slack-based policy answering.",
            evidence_summary="Guru's G2 page shows 847 reviews.",
            citations=[_make_citation()],
            confidence="medium",
            confidence_rationale="Single G2 listing.",
        )


# ---------------------------------------------------------------------------
# 4. CompetitorMention rejected with empty citations list
# ---------------------------------------------------------------------------


def test_competitor_mention_rejects_empty_citations() -> None:
    """CompetitorMention with citations=[] should raise ValidationError."""
    with pytest.raises(ValidationError) as exc_info:
        CompetitorMention(
            name="Guru",
            description="A knowledge management tool.",
            positioning_vs_idea="Directly overlaps with the proposed Slack HR bot.",
            citations=[],  # violates min_length=1
        )
    errors = exc_info.value.errors()
    assert any(e["loc"] == ("citations",) for e in errors)


def test_competitor_mention_rejects_more_than_two_citations() -> None:
    """CompetitorMention with 3 citations should raise ValidationError (max_length=2)."""
    with pytest.raises(ValidationError):
        CompetitorMention(
            name="Guru",
            description="A knowledge management tool.",
            positioning_vs_idea="Directly overlaps with the proposed Slack HR bot.",
            citations=[_make_citation(), _make_citation(), _make_citation()],
        )


# ---------------------------------------------------------------------------
# 5. ValidationReport rejected with too few questions_and_findings (<5)
# ---------------------------------------------------------------------------


def test_validation_report_rejects_fewer_than_five_questions() -> None:
    """questions_and_findings with 4 items should raise ValidationError."""
    with pytest.raises(ValidationError) as exc_info:
        _make_valid_report(question_count=4)
    errors = exc_info.value.errors()
    assert any(e["loc"] == ("questions_and_findings",) for e in errors)


# ---------------------------------------------------------------------------
# 6. ValidationReport rejected with too many questions_and_findings (>7)
# ---------------------------------------------------------------------------


def test_validation_report_rejects_more_than_seven_questions() -> None:
    """questions_and_findings with 8 items should raise ValidationError."""
    qids = [f"q{i}" for i in range(1, 8)]  # only q1-q7 are valid IDs
    # Build 7 valid ones, then try to add an 8th with a duplicate ID
    # The max_length=7 constraint on the list fires before the duplicate check.
    eight_findings = [_make_question_findings(qid) for qid in qids]
    # Add a duplicate to get to 8 items — the list length constraint fires first.
    eight_findings.append(_make_question_findings("q7"))
    with pytest.raises(ValidationError):
        _make_valid_report(question_count=5)  # sanity check
        ValidationReport(
            executive_summary="Summary.",
            questions_and_findings=eight_findings,
            competitors=[],
            market_signals="No data.",
            distribution_signals=None,
            regulatory_signals=None,
            risks_assessment="Risks addressed here in detail for the test case.",
            overall_recommendation="iterate",
            recommendation_rationale="Rationale with q1 reference for the test.",
            research_limitations="Limited data.",
            rubric_version_used="v1",
        )


# ---------------------------------------------------------------------------
# 7. Citation URL validation rejects non-http(s) URLs
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "bad_url",
    [
        "ftp://example.com/file",
        "file:///etc/passwd",
        "data:text/html,<script>",
        "gopher://example.com",
        "javascript:alert(1)",
        "//example.com/path",
        "example.com/no-scheme",
        "relative/path/only",
    ],
)
def test_citation_url_rejects_non_https(bad_url: str) -> None:
    """Citation URLs not starting with http:// or https:// should raise ValidationError."""
    with pytest.raises(ValidationError) as exc_info:
        Citation(
            url=bad_url,
            title="Test Article",
            source_domain="example.com",
            accessed_at=_NOW,
        )
    errors = exc_info.value.errors()
    assert any(e["loc"] == ("url",) for e in errors)


# ---------------------------------------------------------------------------
# 8. Citation URL validation accepts http:// and https:// URLs
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "good_url",
    [
        "https://reddit.com/r/sysadmin/comments/abc123",
        "http://techcrunch.com/2024/01/01/article",
        "https://g2.com/products/guru/reviews",
        "https://www.example.co.uk/page?q=test&id=1",
    ],
)
def test_citation_url_accepts_valid_http_urls(good_url: str) -> None:
    """Citation URLs starting with http:// or https:// should be accepted."""
    c = Citation(
        url=good_url,
        title="Valid Title",
        source_domain="example.com",
        accessed_at=_NOW,
    )
    assert c.url == good_url


# ---------------------------------------------------------------------------
# 9. Finding.claim max char constraint
# ---------------------------------------------------------------------------


def test_finding_claim_max_char_limit() -> None:
    """Finding.claim exceeding 500 characters should raise ValidationError."""
    with pytest.raises(ValidationError) as exc_info:
        Finding(
            question_id="q1",
            claim="x" * 501,
            evidence_summary="Evidence here.",
            citations=[_make_citation()],
            confidence="low",
            confidence_rationale="No strong sources.",
        )
    errors = exc_info.value.errors()
    assert any(e["loc"] == ("claim",) for e in errors)


# ---------------------------------------------------------------------------
# 10. Finding.evidence_summary max char constraint (max 800)
# ---------------------------------------------------------------------------


def test_finding_evidence_summary_max_char_limit() -> None:
    """Finding.evidence_summary exceeding 800 characters should raise ValidationError."""
    with pytest.raises(ValidationError):
        Finding(
            question_id="q1",
            claim="A valid claim here.",
            evidence_summary="x" * 801,
            citations=[_make_citation()],
            confidence="low",
            confidence_rationale="No strong sources.",
        )


def test_finding_evidence_summary_accepts_800_chars() -> None:
    """Finding.evidence_summary at exactly 800 characters should be accepted."""
    f = Finding(
        question_id="q1",
        claim="A valid claim here.",
        evidence_summary="x" * 800,
        citations=[_make_citation()],
        confidence="low",
        confidence_rationale="No strong sources.",
    )
    assert len(f.evidence_summary) == 800


# ---------------------------------------------------------------------------
# 11. Finding.confidence_rationale max char constraint (max 250)
# ---------------------------------------------------------------------------


def test_finding_confidence_rationale_max_char_limit() -> None:
    """Finding.confidence_rationale exceeding 250 characters should raise ValidationError."""
    with pytest.raises(ValidationError):
        Finding(
            question_id="q1",
            claim="A valid claim here.",
            evidence_summary="Valid evidence summary.",
            citations=[_make_citation()],
            confidence="low",
            confidence_rationale="x" * 251,
        )


def test_finding_confidence_rationale_accepts_250_chars() -> None:
    """Finding.confidence_rationale at exactly 250 characters should be accepted."""
    f = Finding(
        question_id="q1",
        claim="A valid claim here.",
        evidence_summary="Valid evidence summary.",
        citations=[_make_citation()],
        confidence="low",
        confidence_rationale="x" * 250,
    )
    assert len(f.confidence_rationale) == 250


# ---------------------------------------------------------------------------
# 12. ValidationReport.executive_summary max char constraint
# ---------------------------------------------------------------------------


def test_executive_summary_max_char_limit() -> None:
    """executive_summary exceeding 2000 characters should raise ValidationError."""
    base = _make_valid_report()
    with pytest.raises(ValidationError) as exc_info:
        base.model_copy(update={"executive_summary": "x" * 2001})
        ValidationReport(
            **{**base.model_dump(), "executive_summary": "x" * 2001}
        )
    errors = exc_info.value.errors()
    assert any(e["loc"] == ("executive_summary",) for e in errors)


# ---------------------------------------------------------------------------
# 13. ValidationReport.recommendation_rationale max char constraint
# ---------------------------------------------------------------------------


def test_recommendation_rationale_max_char_limit() -> None:
    """recommendation_rationale exceeding 2000 characters should raise ValidationError."""
    base = _make_valid_report()
    with pytest.raises(ValidationError):
        ValidationReport(
            **{**base.model_dump(), "recommendation_rationale": "x" * 2001}
        )


# ---------------------------------------------------------------------------
# 14. ValidationReport.risks_assessment max char constraint
# ---------------------------------------------------------------------------


def test_risks_assessment_max_char_limit() -> None:
    """risks_assessment exceeding 2500 characters should raise ValidationError."""
    base = _make_valid_report()
    with pytest.raises(ValidationError):
        ValidationReport(
            **{**base.model_dump(), "risks_assessment": "x" * 2501}
        )


# ---------------------------------------------------------------------------
# 15. ValidationReport.research_limitations max char constraint
# ---------------------------------------------------------------------------


def test_research_limitations_max_char_limit() -> None:
    """research_limitations exceeding 800 characters should raise ValidationError."""
    base = _make_valid_report()
    with pytest.raises(ValidationError):
        ValidationReport(
            **{**base.model_dump(), "research_limitations": "x" * 801}
        )


# ---------------------------------------------------------------------------
# 16. CompetitorMention rejected with >2 citations (already tested above,
#     but repeating as a standalone named test for the checklist)
# ---------------------------------------------------------------------------


def test_competitor_mention_max_two_citations() -> None:
    """CompetitorMention.citations max_length=2 must be enforced."""
    with pytest.raises(ValidationError):
        _make_competitor(
            citations=[_make_citation(), _make_citation(), _make_citation()]
        )


# ---------------------------------------------------------------------------
# 17. QuestionFindings.question_id pattern constraint
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("bad_id", ["q0", "q8", "Q3", "question2", ""])
def test_question_findings_rejects_malformed_question_id(bad_id: str) -> None:
    """QuestionFindings.question_id must match ^q[1-7]$."""
    with pytest.raises(ValidationError):
        _make_question_findings(question_id=bad_id)


# ---------------------------------------------------------------------------
# 18. Duplicate question_ids in questions_and_findings rejected
# ---------------------------------------------------------------------------


def test_validation_report_rejects_duplicate_question_ids() -> None:
    """ValidationReport with two QuestionFindings sharing question_id should raise."""
    qfs = [
        _make_question_findings("q1"),
        _make_question_findings("q1"),  # duplicate
        _make_question_findings("q2"),
        _make_question_findings("q3"),
        _make_question_findings("q4"),
    ]
    with pytest.raises(ValidationError) as exc_info:
        ValidationReport(
            executive_summary="Test summary with enough text to pass the min length check.",
            questions_and_findings=qfs,
            competitors=[],
            market_signals="No market data found in the search results.",
            distribution_signals=None,
            regulatory_signals=None,
            risks_assessment="Risks addressed here in detail for the test case scenario.",
            overall_recommendation="iterate",
            recommendation_rationale="Rationale with q1 reference for the test case here.",
            research_limitations="Limited by duplicate question ids in this test.",
            rubric_version_used="v1",
        )
    errors = exc_info.value.errors()
    assert errors


# ---------------------------------------------------------------------------
# 19. extra="forbid" on Citation rejects unknown fields
# ---------------------------------------------------------------------------


def test_citation_forbids_extra_fields() -> None:
    """Citation with an unknown field should raise ValidationError (extra='forbid')."""
    with pytest.raises(ValidationError) as exc_info:
        Citation(
            url="https://example.com",
            title="Example",
            source_domain="example.com",
            accessed_at=_NOW,
            publication_date="2024-01-01",  # unknown field
        )
    errors = exc_info.value.errors()
    assert any("extra" in str(e).lower() or "forbidden" in str(e).lower() for e in errors)


# ---------------------------------------------------------------------------
# 20. overall_recommendation only accepts valid literals
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "bad_rec",
    ["maybe", "yes", "no", "unknown", "Pass", "PROCEED", ""],
)
def test_overall_recommendation_rejects_invalid_literals(bad_rec: str) -> None:
    """overall_recommendation must be one of the 5 valid literals."""
    base = _make_valid_report()
    with pytest.raises(ValidationError):
        ValidationReport(
            **{**base.model_dump(), "overall_recommendation": bad_rec}
        )


# ---------------------------------------------------------------------------
# 21. ValidationReport.competitors max 6 (tightened from 10 in B2.3-fix)
# ---------------------------------------------------------------------------


def test_validation_report_rejects_more_than_six_competitors() -> None:
    """ValidationReport with 7 competitors should raise ValidationError (max_length=6)."""
    seven_competitors = [_make_competitor() for _ in range(7)]
    base = _make_valid_report()
    with pytest.raises(ValidationError) as exc_info:
        ValidationReport(**{**base.model_dump(), "competitors": [
            c.model_dump() for c in seven_competitors
        ]})
    errors = exc_info.value.errors()
    assert any(e["loc"] == ("competitors",) for e in errors)


def test_validation_report_accepts_six_competitors() -> None:
    """ValidationReport with exactly 6 competitors should be accepted."""
    six_competitors = [_make_competitor() for _ in range(6)]
    base = _make_valid_report()
    report = ValidationReport(**{**base.model_dump(), "competitors": [
        c.model_dump() for c in six_competitors
    ]})
    assert len(report.competitors) == 6


# ---------------------------------------------------------------------------
# 22. FindingDraft: URL-string citations (B2.3-fix)
# ---------------------------------------------------------------------------


def _make_finding_draft(question_id: str = "q1", **overrides: Any) -> FindingDraft:
    defaults: dict[str, Any] = {
        "question_id": question_id,
        "claim": "Guru provides Slack-based policy answering with 847 G2 reviews.",
        "evidence_summary": "Guru's G2 page confirms it as the leading Slack knowledge tool.",
        "citations": ["https://example.com/article"],
        "confidence": "medium",
        "confidence_rationale": "Backed by single G2 listing.",
    }
    defaults.update(overrides)
    return FindingDraft(**defaults)


def test_finding_draft_rejects_empty_citations() -> None:
    """FindingDraft with citations=[] should raise ValidationError (min_length=1)."""
    with pytest.raises(ValidationError) as exc_info:
        FindingDraft(
            question_id="q1",
            claim="Guru provides Slack-based policy answering.",
            evidence_summary="Guru's G2 page shows 847 reviews.",
            citations=[],
            confidence="medium",
            confidence_rationale="Single G2 listing.",
        )
    errors = exc_info.value.errors()
    assert any(e["loc"] == ("citations",) for e in errors)


def test_finding_draft_rejects_more_than_three_citations() -> None:
    """FindingDraft with 4 citations should raise ValidationError (max_length=3)."""
    with pytest.raises(ValidationError):
        FindingDraft(
            question_id="q1",
            claim="Guru provides Slack-based policy answering.",
            evidence_summary="Guru's G2 page shows 847 reviews.",
            citations=[
                "https://example.com/1",
                "https://example.com/2",
                "https://example.com/3",
                "https://example.com/4",
            ],
            confidence="medium",
            confidence_rationale="Four sources cited.",
        )


@pytest.mark.parametrize(
    "good_url",
    [
        "https://reddit.com/r/sysadmin/comments/abc123",
        "http://techcrunch.com/2024/01/01/article",
        "https://g2.com/products/guru/reviews",
    ],
)
def test_finding_draft_accepts_valid_url_strings(good_url: str) -> None:
    """FindingDraft citations accept http:// and https:// URL strings."""
    f = _make_finding_draft(citations=[good_url])
    assert f.citations == [good_url]


@pytest.mark.parametrize(
    "bad_url",
    [
        "ftp://example.com/file",
        "file:///etc/passwd",
        "data:text/html,<script>",
        "gopher://example.com",
        "//example.com/path",
        "example.com/no-scheme",
    ],
)
def test_finding_draft_rejects_url_not_starting_with_https(bad_url: str) -> None:
    """FindingDraft citations reject URLs not starting with http:// or https://."""
    with pytest.raises(ValidationError) as exc_info:
        FindingDraft(
            question_id="q1",
            claim="A valid claim here.",
            evidence_summary="Evidence here.",
            citations=[bad_url],
            confidence="low",
            confidence_rationale="No strong sources.",
        )
    errors = exc_info.value.errors()
    assert errors


def test_finding_draft_evidence_summary_max_800() -> None:
    """FindingDraft.evidence_summary max is 800 chars (same as Finding)."""
    with pytest.raises(ValidationError):
        _make_finding_draft(evidence_summary="x" * 801)


def test_finding_draft_confidence_rationale_max_250() -> None:
    """FindingDraft.confidence_rationale max is 250 chars (same as Finding)."""
    with pytest.raises(ValidationError):
        _make_finding_draft(confidence_rationale="x" * 251)


# ---------------------------------------------------------------------------
# 23. CompetitorMentionDraft: URL-string citations (B2.3-fix)
# ---------------------------------------------------------------------------


def _make_competitor_mention_draft(**overrides: Any) -> CompetitorMentionDraft:
    defaults: dict[str, Any] = {
        "name": "Guru",
        "description": "A knowledge management tool with Slack integration.",
        "positioning_vs_idea": (
            "Guru provides Slack-based Q&A, directly overlapping with the proposed bot."
        ),
        "citations": ["https://example.com/article"],
    }
    defaults.update(overrides)
    return CompetitorMentionDraft(**defaults)


def test_competitor_mention_draft_rejects_empty_citations() -> None:
    """CompetitorMentionDraft with citations=[] should raise ValidationError."""
    with pytest.raises(ValidationError) as exc_info:
        CompetitorMentionDraft(
            name="Guru",
            description="A knowledge management tool.",
            positioning_vs_idea="Directly overlaps.",
            citations=[],
        )
    errors = exc_info.value.errors()
    assert any(e["loc"] == ("citations",) for e in errors)


def test_competitor_mention_draft_rejects_more_than_two_citations() -> None:
    """CompetitorMentionDraft with 3 citations should raise ValidationError (max_length=2)."""
    with pytest.raises(ValidationError):
        CompetitorMentionDraft(
            name="Guru",
            description="A knowledge management tool.",
            positioning_vs_idea="Directly overlaps.",
            citations=[
                "https://example.com/1",
                "https://example.com/2",
                "https://example.com/3",
            ],
        )


def test_competitor_mention_draft_accepts_valid_urls() -> None:
    """CompetitorMentionDraft accepts 1-2 valid http(s):// URL strings."""
    c = _make_competitor_mention_draft(citations=[
        "https://example.com/1",
        "https://example.com/2",
    ])
    assert len(c.citations) == 2


def test_competitor_mention_draft_rejects_non_http_url() -> None:
    """CompetitorMentionDraft rejects URLs not starting with http:// or https://."""
    with pytest.raises(ValidationError):
        _make_competitor_mention_draft(citations=["ftp://example.com/file"])


# ---------------------------------------------------------------------------
# 24. ValidationReportDraft: 5-7 questions, duplicate-id rejection (B2.3-fix)
# ---------------------------------------------------------------------------


def _make_question_findings_draft(
    question_id: str = "q1", **overrides: Any
) -> QuestionFindingsDraft:
    defaults: dict[str, Any] = {
        "question_id": question_id,
        "question": f"Does tool {question_id} solve the core use case?",
        "findings": [_make_finding_draft(question_id)],
        "evidence_gap": None,
    }
    defaults.update(overrides)
    return QuestionFindingsDraft(**defaults)


def _make_valid_draft_report(question_count: int = 5) -> ValidationReportDraft:
    """Build a valid ValidationReportDraft with question_count entries."""
    qids = [f"q{i}" for i in range(1, question_count + 1)]
    return ValidationReportDraft(
        executive_summary=(
            "Research confirms Guru and Notion AI directly compete with the proposed "
            "Slack HR bot. The handbook-staleness risk is evidenced by Reddit posts. "
            "Recommendation is to iterate on a specific wedge before proceeding."
        ),
        questions_and_findings=[_make_question_findings_draft(qid) for qid in qids],
        competitors=[],
        market_signals=(
            "No reliable TAM figure in the search results. "
            "Guru's G2 presence signals active buyer demand in this category."
        ),
        distribution_signals=None,
        regulatory_signals=None,
        risks_assessment=(
            "The Guru competitor risk is confirmed. Handbook staleness confirmed. "
            "Procurement complexity partially confirmed by one Reddit thread."
        ),
        overall_recommendation="iterate",
        recommendation_rationale=(
            "q2 confirms Guru covers the core use case. q1 shows the differentiation "
            "is in freshness guarantees. Iterate on the always-current wedge."
        ),
        research_limitations="Market size data was not found in the search results.",
        rubric_version_used="v1",
    )


def test_validation_report_draft_accepts_five_questions() -> None:
    """ValidationReportDraft with 5 questions (minimum) should be accepted."""
    draft = _make_valid_draft_report(5)
    assert len(draft.questions_and_findings) == 5


def test_validation_report_draft_accepts_seven_questions() -> None:
    """ValidationReportDraft with 7 questions (maximum) should be accepted."""
    draft = _make_valid_draft_report(7)
    assert len(draft.questions_and_findings) == 7


def test_validation_report_draft_rejects_fewer_than_five_questions() -> None:
    """ValidationReportDraft with 4 questions should raise ValidationError."""
    with pytest.raises(ValidationError) as exc_info:
        _make_valid_draft_report(question_count=4)
    errors = exc_info.value.errors()
    assert any(e["loc"] == ("questions_and_findings",) for e in errors)


def test_validation_report_draft_rejects_duplicate_question_ids() -> None:
    """ValidationReportDraft with two entries sharing question_id should raise."""
    qfs = [
        _make_question_findings_draft("q1"),
        _make_question_findings_draft("q1"),  # duplicate
        _make_question_findings_draft("q2"),
        _make_question_findings_draft("q3"),
        _make_question_findings_draft("q4"),
    ]
    with pytest.raises(ValidationError) as exc_info:
        ValidationReportDraft(
            executive_summary="Test summary with enough text to pass the min length check.",
            questions_and_findings=qfs,
            competitors=[],
            market_signals="No market data found in search results for this question.",
            distribution_signals=None,
            regulatory_signals=None,
            risks_assessment="Risks addressed here in detail for the test case scenario.",
            overall_recommendation="iterate",
            recommendation_rationale="Rationale with q1 reference for the test case here.",
            research_limitations="Limited by duplicate question ids in this test.",
            rubric_version_used="v1",
        )
    errors = exc_info.value.errors()
    assert errors


def test_validation_report_draft_rejects_more_than_six_competitors() -> None:
    """ValidationReportDraft with 7 competitors should raise ValidationError (max=6)."""
    seven_draft_competitors = [_make_competitor_mention_draft() for _ in range(7)]
    base = _make_valid_draft_report()
    with pytest.raises(ValidationError):
        ValidationReportDraft(
            **{
                **base.model_dump(),
                "competitors": [c.model_dump() for c in seven_draft_competitors],
            }
        )


def test_validation_report_draft_extra_fields_forbidden() -> None:
    """ValidationReportDraft with unknown fields should raise ValidationError."""
    base = _make_valid_draft_report()
    with pytest.raises(ValidationError):
        ValidationReportDraft(**{**base.model_dump(), "unknown_field": "value"})


# ---------------------------------------------------------------------------
# 25. Regression: realistic high-quality report parses successfully
#
# The first end-to-end synthesizer run produced 34 Pydantic validation errors
# because evidence_summary (~650 chars with source quotes) and executive_summary
# (~1200 chars) exceeded the old 400/800 limits. This test builds a
# ValidationReportDraft with realistic field lengths and asserts it parses
# without error — regression protection against future constraint tightening.
# ---------------------------------------------------------------------------


def test_realistic_high_quality_draft_report_parses() -> None:
    """A ValidationReportDraft with realistic high-depth field lengths must parse.

    Field lengths here match what a high-quality synthesizer run produces:
    - evidence_summary: ~650 chars (includes verbatim source quote + named entities)
    - confidence_rationale: ~220 chars (names specific sources and corroboration)
    - executive_summary: ~1200 chars (5 sentences naming competitors and findings)
    - risks_assessment: ~1100 chars (addresses 4 risks with question_id references)
    - recommendation_rationale: ~1100 chars (anchored to question_ids with evidence)
    - market_signals: ~800 chars (named data points, no fabricated TAM)
    - research_limitations: ~650 chars (honest multi-dimension gap statement)
    """
    evidence_summary_with_quote = (
        "Guru's G2 listing (cited) shows 847 reviews averaging 4.5 stars, placing it as "
        "the most-reviewed knowledge-management tool with Slack integration. A 2024 r/sysadmin "
        "thread (cited) quotes a user: \"we cancelled Guru because the Slack integration kept "
        "hallucinating outdated PTO rules — our HR team lost trust in it within two weeks.\" "
        "A second r/operations thread from March 2024 (cited) describes the same failure mode: "
        "ops managers spending 90+ minutes weekly re-answering questions the bot answered "
        "incorrectly. Three independent posts converge on the same root cause: stale document "
        "syncing, not search quality."
    )
    # Fixture must exceed the old 400-char limit to prove regression protection.
    assert 400 < len(evidence_summary_with_quote) <= 800, (
        f"evidence_summary fixture must exceed old 400-char limit: {len(evidence_summary_with_quote)}"
    )

    confidence_rationale_specific = (
        "Backed by Guru's official G2 page (847 reviews, verified purchase) and corroborated "
        "by two independent r/sysadmin threads from 2024 describing the identical Slack bot "
        "staleness failure mode; three independent sources with consistent signal."
    )
    # Fixture must exceed the old 150-char limit to prove regression protection.
    assert 150 < len(confidence_rationale_specific) <= 250, (
        f"confidence_rationale fixture must exceed old 150-char limit: {len(confidence_rationale_specific)}"
    )

    executive_summary_full = (
        "Research confirms the handbook-staleness problem is real and actively felt by operations "
        "managers: three r/sysadmin and r/operations threads from 2024 describe employees losing "
        "trust in AI policy bots within weeks of rollout due to stale document syncing, with one "
        "thread explicitly calling out Guru's 72-hour sync lag as the root cause of the failure. "
        "Guru (847 G2 reviews at 4.5 stars, $35/user/month) and Notion AI (bundled into existing "
        "Notion workspaces at no additional per-seat cost) both provide Slack-based policy "
        "answering, but neither offers a real-time handbook sync guarantee, leaving the core "
        "differentiation gap open and evidenced by multiple independent community sources. "
        "The willingness-to-pay signal is strong: Guru's 847 paying customers at $35 per user "
        "per month confirms the audience already pays for Slack knowledge tools in this category, "
        "and the G2 review sentiment shows active evaluation and switching behaviour rather than "
        "a settled-market dynamic that would indicate low receptivity to a new entrant. "
        "No fatal regulatory barrier exists for an HR knowledge SaaS in this scope — the searches "
        "returned no evidence of employment-law, data-privacy, or licensing constraints that would "
        "block an MVP launch, and distribution via the Slack App Directory is a proven low-friction "
        "channel for IT-approved installs at Series A through C companies. "
        "Recommendation is to iterate: narrow to the always-current handbook wedge and build "
        "the real-time sync guarantee as the primary differentiator before broadening scope to "
        "generic policy Q&A functionality that Guru already covers for most buyers today. "
        "The key iteration is to ship a proof of real-time sync with one design-partner customer "
        "before investing in broader Q&A capabilities, so the differentiation claim can be "
        "validated with evidence rather than asserted without it."
    )
    # Fixture must exceed the old 1500-char limit to prove the new limit accommodates real output.
    assert 1500 < len(executive_summary_full) <= 2000, (
        f"executive_summary fixture must exceed old 1500-char limit: {len(executive_summary_full)}"
    )

    risks_assessment_full = (
        "The handbook-staleness risk (q1) is confirmed: three r/sysadmin posts from 2024 "
        "describe AI policy bots surfacing outdated PTO rules, causing employees to distrust the "
        "tool within weeks of rollout; one thread explicitly names Guru's 72-hour document sync "
        "lag as the root cause, and a second thread reports an HR team disabling the bot entirely "
        "after two weeks of incorrect PTO answers; this failure mode is the primary wedge "
        "opportunity the proposed product addresses and is the most strongly evidenced signal "
        "in the research. "
        "The Guru and Notion AI competitor risk (q2, q3) is confirmed: both tools provide "
        "Slack-based policy answering with active paying customers and published reviews, but "
        "neither offers a real-time document sync guarantee in their current positioning or "
        "marketing materials, and no Tavily result showed either competitor responding to the "
        "staleness complaint, leaving the differentiation gap open and uncontested by the "
        "current market leaders. "
        "The procurement complexity risk (q5) is partially confirmed: one r/humanresources thread "
        "reports 60-plus-day IT approval cycles at Series B companies, and a second thread from "
        "r/sysadmin describes a six-month vendor review process at a 200-person company; however, "
        "Guru's own pricing page and App Directory listing suggest solo-manager purchasing is "
        "also common at sub-50-person teams, meaning a self-serve motion may bypass the "
        "procurement friction entirely for the initial customer segment. "
        "The willingness-to-pay risk (q4) is addressed and substantially de-risked: Guru's "
        "847 paying customers at $35 per user per month confirms the audience already pays for "
        "Slack knowledge tools in this exact category today, and the active review volume on G2 "
        "indicates ongoing evaluation rather than a settled market with low switching intent."
    )
    # Fixture must exceed the old 1500-char limit to prove the new limit accommodates real output.
    assert 1500 < len(risks_assessment_full) <= 2500, (
        f"risks_assessment fixture must exceed old 1500-char limit: {len(risks_assessment_full)}"
    )

    recommendation_rationale_full = (
        "q2 and q3 findings confirm Guru covers the generic Slack Q&A use case for many buyers "
        "at $35 per user per month with 847 active G2 reviewers, making a direct undifferentiated "
        "product infeasible without a clear and evidenced differentiating claim that Guru does not "
        "already address in its current positioning or marketing materials. "
        "q1 findings surface the evidenced gap: three 2024 Reddit threads from r/sysadmin and "
        "r/operations describe employees losing trust in policy bots within two weeks specifically "
        "because of stale document syncing, a failure mode Guru acknowledges in neither its G2 "
        "responses nor its product page, and one thread explicitly names a 72-hour sync lag as "
        "the root cause of the trust failure, giving the proposed product a concrete and "
        "quotable differentiating claim to lead with in positioning. "
        "q4 findings confirm willingness to pay exists in this category: Guru's 847 paying "
        "customers at $35 per user per month establishes the audience actively pays for Slack "
        "knowledge tools at this price range today, and the G2 review volume indicates "
        "ongoing evaluation and switching behaviour rather than a settled market with "
        "low receptivity to a new entrant offering a specific improvement. "
        "q5 partially confirms that procurement friction is real at Series B and above — one "
        "r/humanresources thread reports 60-plus-day IT approval cycles and another describes a "
        "six-month vendor review — suggesting a self-serve or manager-led trial motion as the "
        "go-to-market entry point to bypass enterprise procurement friction in the early stage. "
        "Iteration should target the always-current handbook sync guarantee as the sole "
        "differentiating claim before broadening scope to generic Q&A functionality that Guru "
        "already covers adequately for the majority of buyers in this category."
    )
    # Fixture must exceed the old 1500-char limit to prove the new limit accommodates real output.
    assert 1500 < len(recommendation_rationale_full) <= 2000, (
        f"recommendation_rationale fixture must exceed old 1500-char limit: "
        f"{len(recommendation_rationale_full)}"
    )

    market_signals_full = (
        "No reliable TAM figure for the AI-assisted HR policy answering niche appeared in the "
        "search results: broad HR tech market claims in the $30B range were found but are not "
        "specific to Slack-based knowledge bots and were not cited to avoid fabricating "
        "addressable market figures. "
        "Guru's 847 G2 reviews averaging 4.5 stars in the Slack knowledge-management category "
        "at $35 per user per month signals active paying buyer demand and willingness to pay "
        "at this price point. "
        "Three 2024 community threads across r/sysadmin and r/operations indicate operations "
        "managers at Series A through C companies are actively evaluating and churning from "
        "existing solutions, signalling unsatisfied demand rather than a solved market."
    )
    # Fixture must exceed the old 600-char limit to prove regression protection.
    assert 600 < len(market_signals_full) <= 1000, (
        f"market_signals fixture must exceed old 600-char limit: {len(market_signals_full)}"
    )

    research_limitations_full = (
        "Market size data specific to AI-assisted HR policy answering was not found in the "
        "search results; broad HR tech market figures exist but are not granular enough to "
        "be cited without fabricating addressable market claims. "
        "Pricing and churn data specific to Notion AI's HR use case was absent; Notion AI "
        "positioning is inferred from its general product page rather than HR-specific customer "
        "evidence or case studies. "
        "No primary research on IT procurement cycle lengths for knowledge bots at Series A "
        "through C was available; the one Reddit thread citing 60-plus-day cycles is a single "
        "anecdote rather than a systematic survey."
    )
    # Fixture must exceed the old 500-char limit to prove regression protection.
    assert 500 < len(research_limitations_full) <= 800, (
        f"research_limitations fixture must exceed old 500-char limit: {len(research_limitations_full)}"
    )

    realistic_finding = FindingDraft(
        question_id="q1",
        claim=(
            "Guru's Slack integration surfaces outdated policy answers due to stale document "
            "syncing, causing employee trust failures within weeks of rollout per three 2024 "
            "Reddit threads — this is the evidenced gap the proposed product targets."
        ),
        evidence_summary=evidence_summary_with_quote,
        citations=[
            "https://reddit.com/r/sysadmin/comments/abc123/guru_slack_bot_stale",
            "https://reddit.com/r/operations/comments/def456/policy_bot_trust",
            "https://g2.com/products/guru/reviews",
        ],
        confidence="high",
        confidence_rationale=confidence_rationale_specific,
    )

    draft = ValidationReportDraft(
        executive_summary=executive_summary_full,
        questions_and_findings=[
            QuestionFindingsDraft(
                question_id=f"q{i}",
                question=f"Research question {i} for the handbook bot idea?",
                findings=[
                    realistic_finding if i == 1
                    else _make_finding_draft(f"q{i}")
                ],
                evidence_gap=None,
            )
            for i in range(1, 6)
        ],
        competitors=[_make_competitor_mention_draft()],
        market_signals=market_signals_full,
        distribution_signals=(
            "The Slack App Directory is the primary distribution channel — apps listed "
            "there receive organic installs from IT administrators searching for Slack "
            "integrations without a sales motion, reducing CAC for B2B tools."
        ),
        regulatory_signals=None,
        risks_assessment=risks_assessment_full,
        overall_recommendation="iterate",
        recommendation_rationale=recommendation_rationale_full,
        research_limitations=research_limitations_full,
        rubric_version_used="v1",
    )

    assert draft.overall_recommendation == "iterate"
    assert draft.rubric_version_used == "v1"
    assert len(draft.questions_and_findings) == 5
    # evidence_summary must exceed the old 400-char limit.
    assert len(draft.questions_and_findings[0].findings[0].evidence_summary) > 400
    # executive_summary must exceed the old 1500-char limit.
    assert len(draft.executive_summary) > 1500
