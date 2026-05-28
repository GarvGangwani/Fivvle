"""Regression tests for Reader quote guard near-match tier (ADR 0017)."""

from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

import structlog.testing

from app.integrations.tavily import TavilyResult
from app.llm.client import LLMResult
from app.schemas.reader import ExtractedEvidenceDraft, ReaderOutputDraft
from app.services.reader_service import (
    QUOTE_NEAR_MATCH_THRESHOLD,
    _classify_quote_guard,
    _partial_ratio,
    _validate_question_output,
)

_VISA_SOURCE = (
    "The visa application deadline tracker helps applicants monitor processing "
    "times across consulates worldwide with automated reminders and alerts."
)
_VISA_NEAR_VERBATIM = (
    "The visa application deadline tracker helps applicants monitor processing "
    "times across consulates worldwides with automated reminders and alerts."
)
_FABRICATED_QUOTE = (
    "Quantum entanglement enables faster-than-light communication between "
    "unrelated blockchain validators on Mars."
)


def _llm_meta() -> LLMResult:
    return LLMResult(
        text="{}",
        provider="anthropic",
        model="claude-sonnet-4-6",
        prompt_tokens=100,
        completion_tokens=50,
        cost_usd=Decimal("0.01"),
        latency_ms=120,
    )


def _tavily(url: str, content: str) -> TavilyResult:
    return TavilyResult(title="t", url=url, content=content, score=0.9)


def test_partial_ratio_near_verbatim_scores_above_threshold() -> None:
    ratio = _partial_ratio(_VISA_NEAR_VERBATIM, _VISA_SOURCE)
    assert ratio >= QUOTE_NEAR_MATCH_THRESHOLD


def test_partial_ratio_fabrication_scores_below_threshold() -> None:
    ratio = _partial_ratio(_FABRICATED_QUOTE, _VISA_SOURCE)
    assert ratio < QUOTE_NEAR_MATCH_THRESHOLD


def test_classify_quote_guard_near_verbatim_returns_near_match_recovered() -> None:
    assert _classify_quote_guard(_VISA_NEAR_VERBATIM, _VISA_SOURCE) == "near_match_recovered"


def test_classify_quote_guard_fabrication_returns_unmatched() -> None:
    assert _classify_quote_guard(_FABRICATED_QUOTE, _VISA_SOURCE) == "unmatched"


def test_classify_quote_guard_exact_substring_returns_none() -> None:
    assert _classify_quote_guard("worldwide with automated", _VISA_SOURCE) is None


def test_validate_near_match_keeps_quote_and_does_not_increment_count() -> None:
    exp_id = uuid4()
    url = "https://example.com/visa"
    tavily_results = [_tavily(url=url, content=_VISA_SOURCE)]
    draft = ReaderOutputDraft(
        question_id="q1",
        extracted_evidence=[
            ExtractedEvidenceDraft(
                source_url=url,
                relevance="high",
                verbatim_quote=_VISA_NEAR_VERBATIM,
                paraphrase="Tracker for visa deadlines.",
                named_entities=[],
            ),
        ],
    )
    with structlog.testing.capture_logs() as cap:
        out, stats = _validate_question_output(
            draft, tavily_results, "q1", exp_id, llm_meta=_llm_meta()
        )

    warns = [e for e in cap if e.get("event") == "reader quote guard trip"]
    assert len(warns) == 1
    assert warns[0]["failure_class"] == "near_match_recovered"
    assert stats["quote_hallucination_count"] == 0
    assert out.extracted_evidence[0].verbatim_quote == _VISA_NEAR_VERBATIM


def test_validate_fabricated_quote_nulls_and_increments_count() -> None:
    exp_id = uuid4()
    url = "https://example.com/visa"
    tavily_results = [_tavily(url=url, content=_VISA_SOURCE)]
    draft = ReaderOutputDraft(
        question_id="q1",
        extracted_evidence=[
            ExtractedEvidenceDraft(
                source_url=url,
                relevance="high",
                verbatim_quote=_FABRICATED_QUOTE,
                paraphrase="Unrelated claim.",
                named_entities=[],
            ),
        ],
    )
    with structlog.testing.capture_logs() as cap:
        out, stats = _validate_question_output(
            draft, tavily_results, "q1", exp_id, llm_meta=_llm_meta()
        )

    warns = [e for e in cap if e.get("event") == "reader quote guard trip"]
    assert len(warns) == 1
    assert warns[0]["failure_class"] == "unmatched"
    assert stats["quote_hallucination_count"] == 1
    assert out.extracted_evidence[0].verbatim_quote is None
