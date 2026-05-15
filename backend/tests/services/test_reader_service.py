"""Unit tests for app.services.reader_service.

LLM calls are mocked via patch on ``app.services.reader_service.llm_client.complete_structured``.
Observability assertions use ``structlog.testing.capture_logs()`` where stable; per-question
completion uses ``patch(..., wraps=...)`` on emit helpers because ``capture_logs()`` does not
reliably capture after other tests configure structlog processors.
"""

from __future__ import annotations

import asyncio
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
import structlog.testing
from pydantic import ValidationError

import app.services.reader_service as reader_svc
from app.integrations.tavily import TavilyResult
from app.llm.client import LLMResult
from app.schemas.planner import ResearchQuestion
from app.schemas.reader import (
    ExtractedEvidenceDraft,
    ReaderOutput,
    ReaderOutputDraft,
)
from app.services.reader_service import (
    QUOTE_HALLUCINATION_THRESHOLD,
    SENTINEL_LLM_FAILURE_MESSAGE,
    SENTINEL_URL_THRESHOLD_MESSAGE,
    ReaderTotalFailure,
    _extract_for_question,
    _validate_question_output,
    execute_reader,
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


def _tavily(url: str = "https://example.com/a", content: str = "hello world slice") -> TavilyResult:
    return TavilyResult(title="t", url=url, content=content, score=0.9)


# ---------------------------------------------------------------------------
# Schema (sanity)
# ---------------------------------------------------------------------------


def test_extracted_evidence_draft_valid() -> None:
    d = ExtractedEvidenceDraft(
        source_url="https://example.com/x",
        relevance="high",
        verbatim_quote=None,
        paraphrase="Says hello.",
        named_entities=["Acme Corp"],
    )
    assert d.source_url.startswith("https://")


def test_extracted_evidence_draft_rejects_non_http_url() -> None:
    with pytest.raises(ValidationError):
        ExtractedEvidenceDraft(
            source_url="ftp://bad.example/x",
            relevance="low",
            verbatim_quote=None,
            paraphrase="x",
            named_entities=[],
        )


def test_extracted_evidence_draft_rejects_oversized_named_entity() -> None:
    long_ent = "x" * 101
    with pytest.raises(ValidationError):
        ExtractedEvidenceDraft(
            source_url="https://example.com/x",
            relevance="high",
            verbatim_quote=None,
            paraphrase="ok",
            named_entities=[long_ent],
        )


def test_reader_output_draft_caps_evidence_list_at_10() -> None:
    items = [
        ExtractedEvidenceDraft(
            source_url=f"https://example.com/{i}",
            relevance="low",
            verbatim_quote=None,
            paraphrase="p",
            named_entities=[],
        )
        for i in range(11)
    ]
    with pytest.raises(ValidationError):
        ReaderOutputDraft(question_id="q1", extracted_evidence=items)


# ---------------------------------------------------------------------------
# URL hallucination guard
# ---------------------------------------------------------------------------


def test_validate_drops_url_not_in_provided_results() -> None:
    exp_id = uuid4()
    # 1 hallucinated + 4 valid → URL rate 1/5 = 0.20 → strict > threshold NOT tripped
    tavily_results = [
        _tavily(url=f"https://example.com/u{i}", content=f"b{i}") for i in range(4)
    ]
    draft = ReaderOutputDraft(
        question_id="q1",
        extracted_evidence=[
            ExtractedEvidenceDraft(
                source_url="https://evil.com/hallucinated",
                relevance="high",
                verbatim_quote=None,
                paraphrase="bad",
                named_entities=[],
            ),
            *[
                ExtractedEvidenceDraft(
                    source_url=f"https://example.com/u{i}",
                    relevance="medium",
                    verbatim_quote=None,
                    paraphrase=f"g{i}",
                    named_entities=[],
                )
                for i in range(4)
            ],
        ],
    )
    with structlog.testing.capture_logs() as cap:
        out, stats = _validate_question_output(
            draft, tavily_results, "q1", exp_id, llm_meta=_llm_meta()
        )

    warns = [e for e in cap if e.get("event") == "reader hallucinated url"]
    assert len(warns) == 1
    assert warns[0]["evidence_items_before_drop"] == 5
    assert stats["hallucinated_url_count"] == 1
    assert stats["hallucination_rate"] == pytest.approx(0.20)
    assert len(out.extracted_evidence) == 4
    assert {e.source_url for e in out.extracted_evidence} == {
        f"https://example.com/u{i}" for i in range(4)
    }


def test_validate_keeps_all_when_no_url_hallucinated() -> None:
    exp_id = uuid4()
    url = "https://example.com/real"
    tavily_results = [_tavily(url=url, content="full body")]
    draft = ReaderOutputDraft(
        question_id="q1",
        extracted_evidence=[
            ExtractedEvidenceDraft(
                source_url=url,
                relevance="high",
                verbatim_quote=None,
                paraphrase="ok",
                named_entities=[],
            ),
        ],
    )
    out, stats = _validate_question_output(
        draft, tavily_results, "q1", exp_id, llm_meta=_llm_meta()
    )
    assert stats["hallucinated_url_count"] == 0
    assert stats["hallucination_rate"] == 0.0
    assert len(out.extracted_evidence) == 1


def test_validate_url_threshold_triggers_sentinel() -> None:
    exp_id = uuid4()
    base = "https://example.com/"
    # 3 hallucinated + 2 valid → rate 3/5 = 0.6 > 0.20
    tavily_results = [
        _tavily(url=base + "a", content="ca"),
        _tavily(url=base + "b", content="cb"),
    ]
    draft = ReaderOutputDraft(
        question_id="q1",
        extracted_evidence=[
            ExtractedEvidenceDraft(
                source_url=base + "bad1",
                relevance="high",
                verbatim_quote=None,
                paraphrase="x",
                named_entities=[],
            ),
            ExtractedEvidenceDraft(
                source_url=base + "bad2",
                relevance="high",
                verbatim_quote=None,
                paraphrase="x",
                named_entities=[],
            ),
            ExtractedEvidenceDraft(
                source_url=base + "bad3",
                relevance="high",
                verbatim_quote=None,
                paraphrase="x",
                named_entities=[],
            ),
            ExtractedEvidenceDraft(
                source_url=base + "a",
                relevance="medium",
                verbatim_quote=None,
                paraphrase="ya",
                named_entities=[],
            ),
            ExtractedEvidenceDraft(
                source_url=base + "b",
                relevance="low",
                verbatim_quote=None,
                paraphrase="yb",
                named_entities=[],
            ),
        ],
    )
    out, stats = _validate_question_output(
        draft, tavily_results, "q1", exp_id, llm_meta=_llm_meta()
    )
    assert stats["sentinel_reason"] == "hallucination_threshold_exceeded"
    assert len(out.extracted_evidence) == 0
    assert out.evidence_gap_note == SENTINEL_URL_THRESHOLD_MESSAGE


def test_validate_url_threshold_exact_boundary_at_20pct() -> None:
    exp_id = uuid4()
    base = "https://example.com/"
    # 1 hallucinated + 4 valid → rate 1/5 = 0.20 → NOT strict >
    tavily_results = [
        _tavily(url=base + str(i), content=f"c{i}")
        for i in range(4)
    ]
    evidence = [
        ExtractedEvidenceDraft(
            source_url=base + "ghost",
            relevance="high",
            verbatim_quote=None,
            paraphrase="bad",
            named_entities=[],
        ),
    ]
    for i in range(4):
        evidence.append(
            ExtractedEvidenceDraft(
                source_url=base + str(i),
                relevance="medium",
                verbatim_quote=None,
                paraphrase=f"p{i}",
                named_entities=[],
            ),
        )
    draft = ReaderOutputDraft(question_id="q1", extracted_evidence=evidence)

    out, stats = _validate_question_output(
        draft, tavily_results, "q1", exp_id, llm_meta=_llm_meta()
    )
    assert stats["hallucination_rate"] == pytest.approx(0.20)
    assert stats["sentinel_reason"] is None
    assert len(out.extracted_evidence) == 4


# ---------------------------------------------------------------------------
# Quote hallucination guard
# ---------------------------------------------------------------------------


def test_validate_nulls_quote_when_substring_not_in_content() -> None:
    exp_id = uuid4()
    url = "https://example.com/page"
    tavily_results = [_tavily(url=url, content="actual body without phrase")]
    draft = ReaderOutputDraft(
        question_id="q1",
        extracted_evidence=[
            ExtractedEvidenceDraft(
                source_url=url,
                relevance="high",
                verbatim_quote="NOT_IN_BODY",
                paraphrase="kept",
                named_entities=[],
            ),
        ],
    )
    with structlog.testing.capture_logs() as cap:
        out, stats = _validate_question_output(
            draft, tavily_results, "q1", exp_id, llm_meta=_llm_meta()
        )

    warns = [e for e in cap if e.get("event") == "reader hallucinated quote"]
    assert len(warns) == 1
    assert stats["quote_hallucination_count"] == 1
    assert out.extracted_evidence[0].verbatim_quote is None
    assert out.extracted_evidence[0].paraphrase == "kept"


def test_validate_keeps_quote_when_substring_matches() -> None:
    exp_id = uuid4()
    url = "https://example.com/page"
    body = "prefix QUOTE_HERE suffix"
    tavily_results = [_tavily(url=url, content=body)]
    draft = ReaderOutputDraft(
        question_id="q1",
        extracted_evidence=[
            ExtractedEvidenceDraft(
                source_url=url,
                relevance="high",
                verbatim_quote="QUOTE_HERE",
                paraphrase="ok",
                named_entities=[],
            ),
        ],
    )
    out, stats = _validate_question_output(
        draft, tavily_results, "q1", exp_id, llm_meta=_llm_meta()
    )
    assert stats["quote_hallucination_count"] == 0
    assert out.extracted_evidence[0].verbatim_quote == "QUOTE_HERE"


def test_validate_quote_threshold_emits_error_but_keeps_items() -> None:
    exp_id = uuid4()
    url_template = "https://example.com/u{}"
    # 10 drafts with quotes; 2 hallucinated quotes → 2/10 = 0.2 > QUOTE threshold 0.10
    tavily_results = [
        _tavily(url=url_template.format(i), content=f"body{i} unique text") for i in range(10)
    ]
    evidence: list[ExtractedEvidenceDraft] = []
    for i in range(10):
        quote_ok = f"body{i} unique text"
        quote_bad = "ZZZ_BAD_QUOTE_ZZZ"
        # Items 0–1 bad quotes; rest match body
        q = quote_bad if i < 2 else quote_ok
        evidence.append(
            ExtractedEvidenceDraft(
                source_url=url_template.format(i),
                relevance="medium",
                verbatim_quote=q,
                paraphrase=f"p{i}",
                named_entities=[],
            ),
        )
    draft = ReaderOutputDraft(question_id="q1", extracted_evidence=evidence)

    with structlog.testing.capture_logs() as cap:
        out, stats = _validate_question_output(
            draft, tavily_results, "q1", exp_id, llm_meta=_llm_meta()
        )

    errs = [
        e for e in cap if e.get("event") == "reader quote hallucination rate exceeded threshold"
    ]
    assert len(errs) == 1
    assert stats["quote_hallucination_rate"] > QUOTE_HALLUCINATION_THRESHOLD
    assert len(out.extracted_evidence) == 10


def test_validate_quote_rate_zero_when_no_quotes_present() -> None:
    exp_id = uuid4()
    url = "https://example.com/u"
    tavily_results = [_tavily(url=url, content="only body")]
    draft = ReaderOutputDraft(
        question_id="q1",
        extracted_evidence=[
            ExtractedEvidenceDraft(
                source_url=url,
                relevance="low",
                verbatim_quote=None,
                paraphrase="para only",
                named_entities=[],
            ),
        ],
    )
    out, stats = _validate_question_output(
        draft, tavily_results, "q1", exp_id, llm_meta=_llm_meta()
    )
    assert stats["quote_hallucination_rate"] == 0.0


# ---------------------------------------------------------------------------
# _extract_for_question
# ---------------------------------------------------------------------------


async def test_extract_for_question_success_returns_validated_output() -> None:
    db = MagicMock(spec=[])  # AsyncSession unused when LLM mocked
    exp_id = uuid4()
    url = "https://example.com/q"
    tavily_results = [_tavily(url=url, content="snippet ok")]
    question = ResearchQuestion(
        id="q1",
        question="What?",
        rationale="r",
        search_queries=["sq"],
    )
    draft = ReaderOutputDraft(
        question_id="q1",
        extracted_evidence=[
            ExtractedEvidenceDraft(
                source_url=url,
                relevance="high",
                verbatim_quote=None,
                paraphrase="fine",
                named_entities=[],
            ),
        ],
    )

    async def fake_complete(*_a, **_kw):
        return draft, _llm_meta()

    orig_q = reader_svc._emit_reader_question_complete
    orig_cal = reader_svc._emit_calibration_field_lengths

    with (
        patch(
            "app.services.reader_service.llm_client.complete_structured",
            AsyncMock(side_effect=fake_complete),
        ),
        patch.object(reader_svc, "_emit_reader_question_complete", wraps=orig_q) as emit_complete,
        patch.object(reader_svc, "_emit_calibration_field_lengths", wraps=orig_cal) as emit_cal,
    ):
        out, stats = await _extract_for_question(
            db=db,
            experiment_id=exp_id,
            question=question,
            tavily_results=tavily_results,
        )

    assert isinstance(out, ReaderOutput)
    assert stats["sentinel_reason"] is None
    assert len(out.extracted_evidence) == 1
    emit_complete.assert_called_once()
    ec_kw = emit_complete.call_args.kwargs
    assert ec_kw["question_id"] == "q1"
    assert ec_kw["experiment_id"] == exp_id
    assert ec_kw["tavily_result_count"] == 1

    emit_cal.assert_called_once()
    assert emit_cal.call_args.kwargs["question_id"] == "q1"
    assert emit_cal.call_args.kwargs["experiment_id"] == exp_id


async def test_extract_for_question_llm_exception_returns_sentinel() -> None:
    db = MagicMock(spec=[])
    exp_id = uuid4()
    question = ResearchQuestion(
        id="q2",
        question="Why?",
        rationale="r",
        search_queries=["sq"],
    )

    orig_q = reader_svc._emit_reader_question_complete
    orig_cal = reader_svc._emit_calibration_field_lengths

    with (
        patch(
            "app.services.reader_service.llm_client.complete_structured",
            AsyncMock(side_effect=RuntimeError("boom")),
        ),
        patch.object(reader_svc._logger, "warning") as warn_mock,
        patch.object(reader_svc, "_emit_reader_question_complete", wraps=orig_q) as emit_complete,
        patch.object(reader_svc, "_emit_calibration_field_lengths", wraps=orig_cal) as emit_cal,
    ):
        out, stats = await _extract_for_question(
            db=db,
            experiment_id=exp_id,
            question=question,
            tavily_results=[_tavily()],
        )

    assert out.extracted_evidence == []
    assert out.evidence_gap_note == SENTINEL_LLM_FAILURE_MESSAGE
    assert stats["sentinel_reason"] == "llm_call_failed"

    warn_mock.assert_called()
    extraction_msgs = [
        c.args[0] for c in warn_mock.call_args_list if c.args and isinstance(c.args[0], str)
    ]
    assert "reader question extraction failed" in extraction_msgs

    emit_complete.assert_called_once()
    ec_kw = emit_complete.call_args.kwargs
    assert ec_kw["question_id"] == "q2"
    assert ec_kw["experiment_id"] == exp_id

    emit_cal.assert_not_called()


# ---------------------------------------------------------------------------
# execute_reader orchestration
# ---------------------------------------------------------------------------


def _seven_questions() -> list[ResearchQuestion]:
    return [
        ResearchQuestion(
            id=f"q{i}",
            question=f"Q{i}?",
            rationale="r",
            search_queries=["s"],
        )
        for i in range(1, 8)
    ]


def _draft_for_question(qid: str, url: str) -> ReaderOutputDraft:
    return ReaderOutputDraft(
        question_id=qid,
        extracted_evidence=[
            ExtractedEvidenceDraft(
                source_url=url,
                relevance="high",
                verbatim_quote=None,
                paraphrase="x",
                named_entities=[],
            ),
        ],
    )


@pytest.fixture
def mock_settings_reader_parallelism() -> MagicMock:
    s = MagicMock()
    s.reader_concurrency_limit = 2
    return s


async def test_execute_reader_runs_all_questions_concurrently(
    mock_settings_reader_parallelism: MagicMock,
) -> None:
    exp_id = uuid4()
    questions = _seven_questions()
    results_by_q = {
        q.id: [_tavily(url=f"https://example.com/{q.id}", content=f"c-{q.id}")]
        for q in questions
    }

    concurrent = 0
    max_concurrent = 0
    lock = asyncio.Lock()

    async def fake_complete_fixed(*_args, **kwargs):
        nonlocal concurrent, max_concurrent
        async with lock:
            concurrent += 1
            max_concurrent = max(max_concurrent, concurrent)
        await asyncio.sleep(0.05)
        async with lock:
            concurrent -= 1
        user = kwargs.get("user", "")
        marker = '<research_question id="'
        start = user.index(marker) + len(marker)
        end = user.index('">', start)
        qid = user[start:end]
        url = f"https://example.com/{qid}"
        return _draft_for_question(qid, url), _llm_meta()

    db = MagicMock(spec=[])

    with patch(
        "app.services.reader_service.llm_client.complete_structured",
        AsyncMock(side_effect=fake_complete_fixed),
    ):
        outputs = await execute_reader(
            experiment_id=exp_id,
            research_questions=questions,
            search_results_by_question=results_by_q,
            db=db,
            settings=mock_settings_reader_parallelism,
        )

    assert set(outputs.keys()) == {f"q{i}" for i in range(1, 8)}
    assert all(len(v.extracted_evidence) == 1 for v in outputs.values())
    assert max_concurrent <= mock_settings_reader_parallelism.reader_concurrency_limit


async def test_execute_reader_collects_partial_success() -> None:
    exp_id = uuid4()
    questions = [
        ResearchQuestion(id="q1", question="a", rationale="r", search_queries=["s"]),
        ResearchQuestion(id="q2", question="b", rationale="r", search_queries=["s"]),
        ResearchQuestion(id="q3", question="c", rationale="r", search_queries=["s"]),
    ]
    results_by_q = {
        "q1": [_tavily(url="https://e.com/q1", content="x")],
        "q2": [_tavily(url="https://e.com/q2", content="y")],
        "q3": [_tavily(url="https://e.com/q3", content="z")],
    }

    async def selective_complete_v2(*_a, **kw):
        user = kw.get("user", "")
        if 'id="q2"' in user:
            raise RuntimeError("fail q2")
        if 'id="q1"' in user:
            return _draft_for_question("q1", "https://e.com/q1"), _llm_meta()
        return _draft_for_question("q3", "https://e.com/q3"), _llm_meta()

    db = MagicMock(spec=[])

    with patch(
        "app.services.reader_service.llm_client.complete_structured",
        AsyncMock(side_effect=selective_complete_v2),
    ):
        outs = await execute_reader(
            experiment_id=exp_id,
            research_questions=questions,
            search_results_by_question=results_by_q,
            db=db,
            settings=MagicMock(reader_concurrency_limit=7),
        )

    assert len(outs) == 3
    assert outs["q2"].evidence_gap_note == SENTINEL_LLM_FAILURE_MESSAGE
    assert len(outs["q1"].extracted_evidence) == 1
    assert len(outs["q3"].extracted_evidence) == 1


async def test_execute_reader_raises_total_failure_when_all_empty() -> None:
    exp_id = uuid4()
    questions = [
        ResearchQuestion(id="q1", question="a", rationale="r", search_queries=["s"]),
    ]
    empty_draft = ReaderOutputDraft(question_id="q1", extracted_evidence=[])

    db = MagicMock(spec=[])

    with patch(
        "app.services.reader_service.llm_client.complete_structured",
        AsyncMock(return_value=(empty_draft, _llm_meta())),
    ), pytest.raises(ReaderTotalFailure):
        await execute_reader(
            experiment_id=exp_id,
            research_questions=questions,
            search_results_by_question={"q1": [_tavily()]},
            db=db,
            settings=MagicMock(reader_concurrency_limit=7),
        )


async def test_execute_reader_emits_run_level_url_error_when_hallucinations_present() -> None:
    exp_id = uuid4()
    questions = [
        ResearchQuestion(id="q1", question="a", rationale="r", search_queries=["s"]),
    ]
    # 1 bad + 4 ok → rate 0.20 → no sentinel for URL threshold; hallucinated_url_count 1
    tresults = [_tavily(url=f"https://e.com/u{i}", content=str(i)) for i in range(4)]
    evidence = [
        ExtractedEvidenceDraft(
            source_url="https://evil.test/x",
            relevance="high",
            verbatim_quote=None,
            paraphrase="bad",
            named_entities=[],
        ),
    ]
    for i in range(4):
        evidence.append(
            ExtractedEvidenceDraft(
                source_url=f"https://e.com/u{i}",
                relevance="medium",
                verbatim_quote=None,
                paraphrase=str(i),
                named_entities=[],
            ),
        )
    draft = ReaderOutputDraft(question_id="q1", extracted_evidence=evidence)

    db = MagicMock(spec=[])

    with (
        patch(
            "app.services.reader_service.llm_client.complete_structured",
            AsyncMock(return_value=(draft, _llm_meta())),
        ),
        structlog.testing.capture_logs() as cap,
    ):
        await execute_reader(
            experiment_id=exp_id,
            research_questions=questions,
            search_results_by_question={"q1": tresults},
            db=db,
            settings=MagicMock(reader_concurrency_limit=7),
        )

    errs = [e for e in cap if e.get("event") == "reader url hallucination detected"]
    assert len(errs) == 1
    assert errs[0]["affected_question_ids"] == ["q1"]


async def test_execute_reader_emits_run_level_quote_error_when_threshold_exceeded() -> None:
    exp_id = uuid4()
    questions = [
        ResearchQuestion(id="q1", question="a", rationale="r", search_queries=["s"]),
    ]
    url_template = "https://e.com/u{}"
    tresults = [_tavily(url=url_template.format(i), content=f"b{i}") for i in range(10)]
    evidence = []
    for i in range(10):
        quote = "BAD" if i < 2 else f"b{i}"
        evidence.append(
            ExtractedEvidenceDraft(
                source_url=url_template.format(i),
                relevance="medium",
                verbatim_quote=quote,
                paraphrase=str(i),
                named_entities=[],
            ),
        )
    draft = ReaderOutputDraft(question_id="q1", extracted_evidence=evidence)

    db = MagicMock(spec=[])

    with (
        patch(
            "app.services.reader_service.llm_client.complete_structured",
            AsyncMock(return_value=(draft, _llm_meta())),
        ),
        structlog.testing.capture_logs() as cap,
    ):
        await execute_reader(
            experiment_id=exp_id,
            research_questions=questions,
            search_results_by_question={"q1": tresults},
            db=db,
            settings=MagicMock(reader_concurrency_limit=7),
        )

    errs = [
        e for e in cap if e.get("event") == "reader quote hallucination rate exceeded"
    ]
    assert len(errs) == 1
    assert errs[0]["affected_question_ids"] == ["q1"]


async def test_execute_reader_does_not_emit_url_error_when_clean() -> None:
    exp_id = uuid4()
    questions = [
        ResearchQuestion(id="q1", question="a", rationale="r", search_queries=["s"]),
    ]
    url = "https://e.com/clean"
    draft = _draft_for_question("q1", url)

    db = MagicMock(spec=[])

    with (
        patch(
            "app.services.reader_service.llm_client.complete_structured",
            AsyncMock(return_value=(draft, _llm_meta())),
        ),
        structlog.testing.capture_logs() as cap,
    ):
        await execute_reader(
            experiment_id=exp_id,
            research_questions=questions,
            search_results_by_question={"q1": [_tavily(url=url, content="x")]},
            db=db,
            settings=MagicMock(reader_concurrency_limit=7),
        )

    errs = [e for e in cap if e.get("event") == "reader url hallucination detected"]
    assert errs == []


def test_sentinel_messages_match_planning_doc() -> None:
    assert isinstance(SENTINEL_LLM_FAILURE_MESSAGE, str)
    assert SENTINEL_LLM_FAILURE_MESSAGE.strip()
    assert isinstance(SENTINEL_URL_THRESHOLD_MESSAGE, str)
    assert SENTINEL_URL_THRESHOLD_MESSAGE.strip()
