"""Unit tests for app.services.reflector_service.

LLM refinement calls are mocked via patch on
``app.services.reflector_service.llm_client.complete_structured``.
Partial re-read tests patch ``app.services.reader_service._extract_for_question``.
Observability uses ``structlog.testing.capture_logs()`` where stable.
"""

from __future__ import annotations

import logging
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
import structlog
import structlog.testing

import app.services.reflector_service as reflector_mod
from app.integrations.tavily import TavilyResult
from app.llm.client import LLMResult, USER_CACHE_ZONE_BOUNDARY
from app.llm.prompts.reflector_query_refinement import (
    PROMPT_NAME as REFLECTOR_PROMPT_NAME,
    build_reflector_query_refinement_user_prompt,
    reflector_query_refinement_v1_legacy_flat_user_and_system,
)
from app.schemas.planner import ResearchPlan, ResearchQuestion
from app.schemas.reader import ExtractedEvidence, ReaderOutput
from app.schemas.refinement import RefinedIdea
from app.schemas.reflector import ReflectorPhaseSummary
from app.services.reflector_service import (
    MAX_QUESTIONS_PER_RUN,
    MAX_REFINED_QUERIES_PER_QUESTION,
    REFLECTOR_QUERY_CACHE_BREAKPOINTS,
    _RefinedQueryListDraft,
    _evaluate_all_rules,
    _evaluate_question_rules,
    _extract_domain_from_url,
    _merge_search_results,
    _refine_queries_for_question,
    execute_reflector,
)


def _llm_meta() -> LLMResult:
    return LLMResult(
        text="{}",
        provider="anthropic",
        model="claude-sonnet-4-6",
        prompt_tokens=50,
        completion_tokens=10,
        cost_usd=Decimal("0.02"),
        latency_ms=80,
    )


def _refinement_settings() -> MagicMock:
    s = MagicMock()
    s.reflector_max_refinement_waves = 1
    return s


def _minimal_refined_idea_reflect() -> RefinedIdea:
    return RefinedIdea(
        refined_one_liner="Reflect cache wiring fixture.",
        target_audience="Understaffed hospitals evaluating nurse tooling.",
        value_proposition="Faster shift handoffs with structured notes.",
        risks=[
            "Do incumbent EMR tools already cover this workflow?",
            "Will procurement block Slack-connected bots?",
            "Can night-shift adoption succeed without admin buy-in?",
        ],
        headline="Handoffs without hallway chasing",
        subheadline="Structured nurse notes synced safely.",
        cta_text="Join waitlist",
    )


@pytest.fixture(autouse=True)
def patch_reflector_load_refined_idea():
    """``execute_reflector`` loads Experiment.refined_idea — stub DB access in tests."""
    with patch(
        "app.services.reflector_service._load_refined_idea_for_reader",
        AsyncMock(return_value=_minimal_refined_idea_reflect()),
    ):
        yield


def _research_question(qid: str) -> ResearchQuestion:
    return ResearchQuestion(
        id=qid,
        question=f"Question for {qid}?",
        rationale="r",
        search_queries=["initial-query"],
    )


def _minimal_plan(question_ids: tuple[str, ...]) -> ResearchPlan:
    """ResearchPlan requires 5–7 questions."""
    return ResearchPlan(
        questions=[_research_question(qid) for qid in question_ids],
        notes_for_synthesizer=None,
    )


def _make_reader_output(
    qid: str,
    atoms: list[ExtractedEvidence],
    *,
    gap_note: str | None = None,
) -> ReaderOutput:
    return ReaderOutput(
        question_id=qid,
        extracted_evidence=atoms,
        evidence_gap_note=gap_note,
    )


def _atom(url: str, *, paraphrase: str = "p") -> ExtractedEvidence:
    return ExtractedEvidence(
        source_url=url,
        relevance="medium",
        verbatim_quote=None,
        paraphrase=paraphrase,
        named_entities=[],
    )


def _three_diverse_atoms(tag: str) -> list[ExtractedEvidence]:
    """Three atoms whose URLs yield three distinct registrable-style netlocs."""
    return [
        _atom(f"https://alpha-{tag}.example.com/a"),
        _atom(f"https://beta-{tag}.example.com/b"),
        _atom(f"https://gamma-{tag}.example.com/c"),
    ]


# ---------------------------------------------------------------------------
# Rule engine
# ---------------------------------------------------------------------------


def test_evaluate_rules_empty_evidence_with_gap_note_fires_both_gap_and_sparse() -> None:
    ro = _make_reader_output("q1", [], gap_note="still unknown")
    assert _evaluate_question_rules(ro) == ["gap_note", "sparse_atoms"]


def test_evaluate_rules_one_atom_fires_sparse_atoms() -> None:
    ro = _make_reader_output(
        "q1",
        [_atom("https://a.example.com/x")],
        gap_note=None,
    )
    assert _evaluate_question_rules(ro) == ["sparse_atoms"]


def test_evaluate_rules_three_diverse_domains_fires_nothing() -> None:
    ro = _make_reader_output(
        "q1",
        [
            _atom("https://a.com/1"),
            _atom("https://b.com/2"),
            _atom("https://c.com/3"),
        ],
    )
    assert _evaluate_question_rules(ro) == []


def test_evaluate_rules_mono_domain_fires_mono_domain() -> None:
    ro = _make_reader_output(
        "q1",
        [
            _atom("https://example.com/a"),
            _atom("https://example.com/b"),
            _atom("https://example.com/c"),
        ],
    )
    assert _evaluate_question_rules(ro) == ["mono_domain"]


def test_evaluate_rules_gap_note_plus_mono_domain_fires_both() -> None:
    ro = _make_reader_output(
        "q1",
        [
            _atom("https://example.com/p1"),
            _atom("https://example.com/p2"),
            _atom("https://example.com/p3"),
        ],
        gap_note="gap",
    )
    assert _evaluate_question_rules(ro) == ["gap_note", "mono_domain"]


# ---------------------------------------------------------------------------
# Decision / scheduling
# ---------------------------------------------------------------------------


def test_evaluate_all_rules_respects_max_questions_per_run_cap() -> None:
    ids = ("q1", "q2", "q3", "q4", "q5")
    plan = _minimal_plan(ids)
    outputs = {
        qid: _make_reader_output(qid, [], gap_note="g") for qid in ids
    }
    scheduled, skipped = _evaluate_all_rules(outputs, plan)
    assert len(scheduled) == MAX_QUESTIONS_PER_RUN
    assert len(skipped) == 1
    assert skipped == ["q5"]
    assert [q for q, _ in scheduled] == ["q1", "q2", "q3", "q4"]


def test_evaluate_all_rules_preserves_plan_order() -> None:
    ids = ("q5", "q4", "q3", "q2", "q1")
    plan = _minimal_plan(ids)
    outputs = {
        qid: _make_reader_output(qid, [], gap_note="x") for qid in ids
    }
    scheduled, skipped = _evaluate_all_rules(outputs, plan)
    assert [q for q, _ in scheduled] == ["q5", "q4", "q3", "q2"]
    assert skipped == ["q1"]


# ---------------------------------------------------------------------------
# Domain extraction
# ---------------------------------------------------------------------------


def test_extract_domain_strips_www_prefix() -> None:
    assert _extract_domain_from_url("https://www.example.com/path") == "example.com"


def test_extract_domain_handles_subdomains() -> None:
    assert (
        _extract_domain_from_url("https://api.example.com/foo") == "api.example.com"
    )


def test_extract_domain_returns_empty_on_malformed_url() -> None:
    assert _extract_domain_from_url("not-a-url") == ""


# ---------------------------------------------------------------------------
# Merge search results
# ---------------------------------------------------------------------------


def test_merge_search_results_dedupes_by_url_first_wins() -> None:
    first = TavilyResult(title="t1", url="https://u/a", content="c1", score=1.0)
    second = TavilyResult(title="t2", url="https://u/a", content="c2", score=9.0)
    merged = _merge_search_results(
        {"q1": [first]},
        {"q1": [second]},
    )
    assert len(merged["q1"]) == 1
    assert merged["q1"][0].title == "t1"


def test_merge_search_results_adds_new_urls() -> None:
    a = TavilyResult(title="a", url="https://u/a", content="ca")
    b = TavilyResult(title="b", url="https://u/b", content="cb")
    merged = _merge_search_results({"q1": [a]}, {"q1": [b]})
    assert {r.url for r in merged["q1"]} == {"https://u/a", "https://u/b"}


def test_merge_search_results_handles_new_question_id() -> None:
    row = TavilyResult(title="n", url="https://new/q", content="cn")
    merged = _merge_search_results({}, {"q9": [row]})
    assert merged["q9"][0].url == "https://new/q"


# ---------------------------------------------------------------------------
# LLM query refinement
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_refine_queries_returns_validated_list_on_success() -> None:
    from app.services.reflector_service import _RefinedQueryListDraft  # noqa: PLC0415

    q = _research_question("q1")
    ro = _make_reader_output("q1", [_atom("https://ex.com/z")])
    db = MagicMock(spec=[])

    draft = _RefinedQueryListDraft(
        queries=["refined query 1", "refined query 2", "refined query 3"],
    )
    with patch(
        "app.services.reflector_service.llm_client.complete_structured",
        AsyncMock(return_value=(draft, _llm_meta())),
    ):
        out, cost = await _refine_queries_for_question(
            db=db,
            experiment_id=uuid4(),
            question=q,
            reader_output=ro,
            triggers=["sparse_atoms"],
            refined_idea=_minimal_refined_idea_reflect(),
            research_plan=_minimal_plan(("q1", "q2", "q3", "q4", "q5")),
        )
    assert out == ["refined query 1", "refined query 2", "refined query 3"]
    assert cost == Decimal("0.02")


@pytest.mark.asyncio
async def test_refine_queries_returns_empty_list_on_llm_failure() -> None:
    q = _research_question("q1")
    ro = _make_reader_output("q1", [])
    db = MagicMock(spec=[])

    with patch(
        "app.services.reflector_service.llm_client.complete_structured",
        AsyncMock(side_effect=RuntimeError("LLM unavailable")),
    ):
        out, cost = await _refine_queries_for_question(
            db=db,
            experiment_id=uuid4(),
            question=q,
            reader_output=ro,
            triggers=["sparse_atoms"],
            refined_idea=_minimal_refined_idea_reflect(),
            research_plan=_minimal_plan(("q1", "q2", "q3", "q4", "q5")),
        )
    assert out == []
    assert cost == Decimal("0")


@pytest.mark.asyncio
async def test_refine_queries_truncates_long_queries() -> None:
    from app.services.reflector_service import _RefinedQueryListDraft  # noqa: PLC0415

    q = _research_question("q1")
    ro = _make_reader_output("q1", [])
    db = MagicMock(spec=[])
    long_q = "x" * 250
    draft = _RefinedQueryListDraft(queries=[long_q])

    with patch(
        "app.services.reflector_service.llm_client.complete_structured",
        AsyncMock(return_value=(draft, _llm_meta())),
    ):
        out, _cost = await _refine_queries_for_question(
            db=db,
            experiment_id=uuid4(),
            question=q,
            reader_output=ro,
            triggers=["sparse_atoms"],
            refined_idea=_minimal_refined_idea_reflect(),
            research_plan=_minimal_plan(("q1", "q2", "q3", "q4", "q5")),
        )
    assert len(out) == 1
    assert len(out[0]) == 200


@pytest.mark.asyncio
async def test_refine_queries_caps_at_max_refined_queries_per_question() -> None:
    from app.services.reflector_service import _RefinedQueryListDraft  # noqa: PLC0415

    q = _research_question("q1")
    ro = _make_reader_output("q1", [])
    db = MagicMock(spec=[])
    draft = _RefinedQueryListDraft(queries=["a", "b", "c", "d"])

    with patch(
        "app.services.reflector_service.llm_client.complete_structured",
        AsyncMock(return_value=(draft, _llm_meta())),
    ):
        out, _cost = await _refine_queries_for_question(
            db=db,
            experiment_id=uuid4(),
            question=q,
            reader_output=ro,
            triggers=["sparse_atoms"],
            refined_idea=_minimal_refined_idea_reflect(),
            research_plan=_minimal_plan(("q1", "q2", "q3", "q4", "q5")),
        )
    assert out == ["a", "b", "c"]
    assert len(out) == MAX_REFINED_QUERIES_PER_QUESTION


# ---------------------------------------------------------------------------
# execute_reflector integration
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_execute_reflector_skips_when_no_questions_trigger() -> None:
    plan = _minimal_plan(("q1", "q2", "q3", "q4", "q5"))
    outputs = {
        q.id: _make_reader_output(q.id, _three_diverse_atoms(q.id))
        for q in plan.questions
    }
    search = {"q1": [TavilyResult(title="t", url="https://x.com/y", content="body")]}

    llm_mock = AsyncMock(
        side_effect=AssertionError("complete_structured must not run when no triggers"),
    )
    with patch(
        "app.services.reflector_service.llm_client.complete_structured",
        llm_mock,
    ):
        ro_out, sr_out, summary = await execute_reflector(
            experiment_id=uuid4(),
            research_plan=plan,
            reader_outputs=outputs,
            search_results=search,
            db=MagicMock(spec=[]),
            settings=_refinement_settings(),
        )

    llm_mock.assert_not_called()
    assert ro_out == outputs
    assert sr_out == search
    assert summary.waves_used == 0


@pytest.mark.asyncio
async def test_execute_reflector_passes_through_when_max_refinement_waves_zero() -> (
    None
):
    plan = _minimal_plan(("q1", "q2", "q3", "q4", "q5"))
    outputs = {
        q.id: _make_reader_output(q.id, [], gap_note="g") for q in plan.questions
    }
    settings = MagicMock()
    settings.reflector_max_refinement_waves = 0

    with structlog.testing.capture_logs() as cap:
        ro_out, sr_out, summary = await execute_reflector(
            experiment_id=uuid4(),
            research_plan=plan,
            reader_outputs=outputs,
            search_results={},
            db=MagicMock(spec=[]),
            settings=settings,
        )

    assert ro_out == outputs
    assert sr_out == {}
    assert summary.waves_used == 0
    assert not any(
        e.get("event") == "reflector signal snapshot" for e in cap
    )
    assert not any(e.get("event") == "reflector decision complete" for e in cap)


@pytest.mark.asyncio
async def test_execute_reflector_never_raises_on_internal_exception() -> None:
    plan = _minimal_plan(("q1", "q2", "q3", "q4", "q5"))
    inp = {q.id: _make_reader_output(q.id, [], gap_note="x") for q in plan.questions}
    sr_in = {}

    with patch(
        "app.services.reflector_service._evaluate_all_rules",
        side_effect=RuntimeError("rules blew up"),
    ), structlog.testing.capture_logs() as cap:
        ro_out, sr_out, summary = await execute_reflector(
            experiment_id=uuid4(),
            research_plan=plan,
            reader_outputs=inp,
            search_results=sr_in,
            db=MagicMock(spec=[]),
            settings=_refinement_settings(),
        )

    assert ro_out is inp
    assert sr_out is sr_in
    assert summary.waves_used == 0
    assert any(
        "reflector phase encountered unexpected error" in str(e.get("event", ""))
        for e in cap
    ), cap


@pytest.mark.asyncio
async def test_execute_reflector_degrade_path_logs_exc_info_on_post_research_error(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Post-re-search failures degrade to inputs and log stack traces (exc_info)."""
    plan = _minimal_plan(("q1", "q2", "q3", "q4", "q5"))
    inp = {
        q.id: _make_reader_output(q.id, [], gap_note="g") for q in plan.questions
    }
    sr_in: dict[str, list[TavilyResult]] = {}
    new_row = TavilyResult(
        title="fresh",
        url="https://fresh.example/n",
        content="fresh slice",
        score=0.9,
    )

    async def fake_partial_search(**kwargs):  # noqa: ARG001
        return {"q1": [new_row]}, 1, 0

    with (
        patch(
            "app.services.reflector_service._refine_queries_for_question",
            AsyncMock(return_value=(["rq-one"], Decimal("0"))),
        ),
        patch(
            "app.services.reflector_service._partial_re_search",
            AsyncMock(side_effect=fake_partial_search),
        ),
        patch(
            "app.services.reflector_service._merge_search_results",
            side_effect=TypeError("post-re-search merge failed"),
        ),
        patch.object(
            reflector_mod._logger,
            "error",
            wraps=reflector_mod._logger.error,
        ) as error_mock,
        structlog.testing.capture_logs(
            processors=[
                structlog.processors.add_log_level,
                structlog.processors.format_exc_info,
            ],
        ) as cap,
        caplog.at_level(logging.ERROR),
    ):
        ro_out, sr_out, summary = await execute_reflector(
            experiment_id=uuid4(),
            research_plan=plan,
            reader_outputs=inp,
            search_results=sr_in,
            db=MagicMock(spec=[]),
            settings=_refinement_settings(),
        )

    assert ro_out is inp
    assert sr_out is sr_in
    assert summary.waves_used == 0

    degrade_logs = [
        e
        for e in cap
        if "reflector phase encountered unexpected error" in str(e.get("event", ""))
    ]
    assert len(degrade_logs) == 1
    exc_text = degrade_logs[0].get("exception", "")
    assert "Traceback" in exc_text
    assert "TypeError" in exc_text
    assert "post-re-search merge failed" in exc_text
    assert degrade_logs[0].get("error_type") == "TypeError"
    assert error_mock.call_args.kwargs.get("exc_info") is True

    exc_records = [r for r in caplog.records if r.exc_info is not None]
    if exc_records:
        assert exc_records[0].exc_info[0] is TypeError
    else:
        assert "Traceback" in exc_text


@pytest.mark.asyncio
async def test_execute_reflector_merges_refined_evidence_on_success() -> None:
    plan = _minimal_plan(("q1", "q2", "q3", "q4", "q5"))
    prior = _make_reader_output("q1", [_atom("https://old.example/o")])
    unchanged = _make_reader_output(
        "q2",
        [
            _atom("https://a.d/a"),
            _atom("https://b.d/b"),
            _atom("https://c.d/c"),
        ],
    )
    outputs = {
        "q1": prior,
        "q2": unchanged,
        **{
            q.id: _make_reader_output(q.id, [_atom(f"https://{q.id}.example/z")])
            for q in plan.questions[2:]
        },
    }
    sr_in = {
        "q1": [
            TavilyResult(title="old", url="https://old.example/o", content="old slice"),
        ],
    }
    new_row = TavilyResult(
        title="fresh",
        url="https://fresh.example/n",
        content="fresh slice",
        score=0.9,
    )
    refreshed = _make_reader_output(
        "q1",
        [
            _atom("https://fresh.example/n", paraphrase="merged atom"),
            _atom("https://old.example/o"),
        ],
    )

    async def fake_partial_search(**kwargs):  # noqa: ARG001
        return {"q1": [new_row]}, 1, 0

    async def fake_partial_read(**kwargs):  # noqa: ARG001
        return {"q1": refreshed}

    with patch(
        "app.services.reflector_service._refine_queries_for_question",
        AsyncMock(return_value=(["rq-one"], Decimal("0"))),
    ), patch(
        "app.services.reflector_service._partial_re_search",
        AsyncMock(side_effect=fake_partial_search),
    ), patch(
        "app.services.reflector_service._partial_re_read",
        AsyncMock(side_effect=fake_partial_read),
    ):
        ro_out, sr_out, summary = await execute_reflector(
            experiment_id=uuid4(),
            research_plan=plan,
            reader_outputs=outputs,
            search_results=sr_in,
            db=MagicMock(spec=[]),
            settings=_refinement_settings(),
        )

    assert summary.waves_used == 1
    assert ro_out["q1"] is refreshed
    assert ro_out["q2"] is unchanged
    urls_q1 = {a.source_url for a in ro_out["q1"].extracted_evidence}
    assert "https://fresh.example/n" in urls_q1
    assert any(new_row.url in r.url for r in sr_out.get("q1", []))


@pytest.mark.asyncio
async def test_execute_reflector_preserves_prior_evidence_when_re_read_fails() -> None:
    plan = _minimal_plan(("q1", "q2", "q3", "q4", "q5"))
    prior = _make_reader_output(
        "q1",
        [_atom("https://prior.example/p", paraphrase="keep-me")],
        gap_note="g",
    )
    outputs = {
        "q1": prior,
        **{
            q.id: _make_reader_output(
                q.id,
                [
                    _atom(f"https://a{q.id}.com/1"),
                    _atom(f"https://b{q.id}.com/2"),
                    _atom(f"https://c{q.id}.com/3"),
                ],
            )
            for q in plan.questions[1:]
        },
    }
    sr_in = {"q1": [TavilyResult(title="t", url="https://prior.example/p", content="x")]}

    async def boom_partial_search(**kwargs):  # noqa: ARG001
        hit = TavilyResult(
            title="more",
            url="https://more.example/m",
            content="mc",
            score=1.0,
        )
        return {"q1": [hit]}, 1, 0

    db = MagicMock(spec=[])

    with patch(
        "app.services.reflector_service._refine_queries_for_question",
        AsyncMock(return_value=(["refined-q"], Decimal("0"))),
    ), patch(
        "app.services.reflector_service._partial_re_search",
        AsyncMock(side_effect=boom_partial_search),
    ), patch(
        "app.services.reader_service._extract_for_question",
        AsyncMock(side_effect=RuntimeError("reader slice failed")),
    ):
        ro_out, _sr, summary = await execute_reflector(
            experiment_id=uuid4(),
            research_plan=plan,
            reader_outputs=outputs,
            search_results=sr_in,
            db=db,
            settings=_refinement_settings(),
        )

    assert summary.waves_used == 1
    assert ro_out["q1"].extracted_evidence[0].paraphrase == "keep-me"


@pytest.mark.asyncio
async def test_execute_reflector_emits_decision_complete_info_log() -> None:
    plan = _minimal_plan(("q1", "q2", "q3", "q4", "q5"))
    outputs = {q.id: _make_reader_output(q.id, [], gap_note="x") for q in plan.questions}

    with patch(
        "app.services.reflector_service._refine_queries_for_question",
        AsyncMock(return_value=([], Decimal("0"))),
    ), structlog.testing.capture_logs() as cap:
        await execute_reflector(
            experiment_id=uuid4(),
            research_plan=plan,
            reader_outputs=outputs,
            search_results={},
            db=MagicMock(spec=[]),
            settings=_refinement_settings(),
        )

    decisions = [
        e for e in cap if e.get("event") == "reflector decision complete"
    ]
    assert len(decisions) == 1
    row = decisions[0]
    assert row["questions_flagged_for_re_search"] == len(plan.questions)
    assert row["questions_scheduled_for_re_search"] == MAX_QUESTIONS_PER_RUN
    assert row["decision_method"] == "rule_v1"
    assert row["re_search_triggered"] is True


@pytest.mark.asyncio
async def test_execute_reflector_emits_phase_complete_info_log() -> None:
    plan = _minimal_plan(("q1", "q2", "q3", "q4", "q5"))
    outputs = {
        q.id: _make_reader_output(q.id, _three_diverse_atoms(q.id))
        for q in plan.questions
    }

    with structlog.testing.capture_logs() as cap:
        await execute_reflector(
            experiment_id=uuid4(),
            research_plan=plan,
            reader_outputs=outputs,
            search_results={},
            db=MagicMock(spec=[]),
            settings=_refinement_settings(),
        )

    complete = [e for e in cap if e.get("event") == "reflector phase complete"]
    assert len(complete) == 1
    assert "total_phase_latency_ms" in complete[0]


@pytest.mark.asyncio
async def test_execute_reflector_logs_do_not_contain_quote_or_paraphrase_text() -> (
    None
):
    leak_para = "LOG_LEAK_PARAPHRASE_MARKER_XYZZY"
    leak_quote = "LOG_LEAK_QUOTE_MARKER_ABCDE"
    leak_tavily = "LOG_LEAK_TAVILY_BODY_MARKER_999"

    plan = _minimal_plan(("q1", "q2", "q3", "q4", "q5"))
    outputs = {
        q.id: _make_reader_output(
            q.id,
            [
                ExtractedEvidence(
                    source_url=f"https://{q.id}.example/doc",
                    relevance="high",
                    verbatim_quote=leak_quote,
                    paraphrase=leak_para,
                    named_entities=[],
                ),
            ],
            gap_note="gap-note-marker-should-not-appear-at-info",
        )
        for q in plan.questions
    }
    search_results = {
        q.id: [
            TavilyResult(
                title="ttl",
                url=f"https://{q.id}.example/doc",
                content=leak_tavily,
            ),
        ]
        for q in plan.questions
    }

    def _flatten(obj: object) -> list[str]:
        out: list[str] = []
        if isinstance(obj, dict):
            for k, v in obj.items():
                out.extend(_flatten(k))
                out.extend(_flatten(v))
        elif isinstance(obj, (list, tuple)):
            for item in obj:
                out.extend(_flatten(item))
        elif isinstance(obj, str):
            out.append(obj)
        return out

    with patch(
        "app.services.reflector_service._refine_queries_for_question",
        AsyncMock(return_value=([], Decimal("0"))),
    ), structlog.testing.capture_logs() as cap:
        await execute_reflector(
            experiment_id=uuid4(),
            research_plan=plan,
            reader_outputs=outputs,
            search_results=search_results,
            db=MagicMock(spec=[]),
            settings=_refinement_settings(),
        )

    blob = "\n".join(_flatten(cap))
    assert leak_para not in blob
    assert leak_quote not in blob
    assert leak_tavily not in blob


@pytest.mark.asyncio
async def test_execute_reflector_fizzle_when_all_re_searches_fail_or_empty() -> None:
    plan = _minimal_plan(("q1", "q2", "q3", "q4", "q5"))
    outputs = {q.id: _make_reader_output(q.id, [], gap_note="x") for q in plan.questions}

    async def empty_partial_search(**kwargs):  # noqa: ARG001
        return {}, 0, 2

    with patch(
        "app.services.reflector_service._refine_queries_for_question",
        AsyncMock(return_value=(["refined-q"], Decimal("0"))),
    ), patch(
        "app.services.reflector_service._partial_re_search",
        AsyncMock(side_effect=empty_partial_search),
    ), structlog.testing.capture_logs() as cap:
        _ro, _sr, summary = await execute_reflector(
            experiment_id=uuid4(),
            research_plan=plan,
            reader_outputs=outputs,
            search_results={},
            db=MagicMock(spec=[]),
            settings=_refinement_settings(),
        )

    assert summary.waves_used == 0
    fizzles = [e for e in cap if e.get("event") == "reflector wave fizzled"]
    assert len(fizzles) == 1
    assert fizzles[0]["reason"] == "re_search_failed_or_empty"
    assert fizzles[0]["loop_iteration"] == 0


@pytest.mark.asyncio
async def test_execute_reflector_fizzle_when_refinement_not_executable() -> None:
    plan = _minimal_plan(("q1", "q2", "q3", "q4", "q5"))
    outputs = {q.id: _make_reader_output(q.id, [], gap_note="x") for q in plan.questions}

    with patch(
        "app.services.reflector_service._refine_queries_for_question",
        AsyncMock(return_value=([], Decimal("0"))),
    ), structlog.testing.capture_logs() as cap:
        _ro, _sr, summary = await execute_reflector(
            experiment_id=uuid4(),
            research_plan=plan,
            reader_outputs=outputs,
            search_results={},
            db=MagicMock(spec=[]),
            settings=_refinement_settings(),
        )

    assert summary.waves_used == 0
    fizzles = [e for e in cap if e.get("event") == "reflector wave fizzled"]
    assert len(fizzles) == 1
    assert fizzles[0]["reason"] == "no_executable_re_searches"


# ---------------------------------------------------------------------------
# Prompt caching (reflector_query_refinement_v1_cached)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_reflector_passes_cache_breakpoints_to_client() -> None:
    q = _research_question("q1")
    ro = _make_reader_output("q1", [_atom("https://ex.com/z")])
    db = MagicMock(spec=[])
    draft = _RefinedQueryListDraft(queries=["a", "b"])
    captured: dict = {}

    async def capture_complete(*_a, **kw):
        captured.update(kw)
        return draft, _llm_meta()

    with patch(
        "app.services.reflector_service.llm_client.complete_structured",
        AsyncMock(side_effect=capture_complete),
    ):
        await _refine_queries_for_question(
            db=db,
            experiment_id=uuid4(),
            question=q,
            reader_output=ro,
            triggers=["sparse_atoms"],
            refined_idea=_minimal_refined_idea_reflect(),
            research_plan=_minimal_plan(("q1", "q2", "q3", "q4", "q5")),
        )

    bps = captured["cache_breakpoints"]
    assert bps is not None
    assert len(bps) == 2
    assert bps[0].position == "user_zone_a_end" and bps[0].ttl == "1h"
    assert bps[1].position == "user_zone_b_end" and bps[1].ttl == "5m"
    assert bps == REFLECTOR_QUERY_CACHE_BREAKPOINTS


def test_reflector_user_prompt_contains_zone_boundaries() -> None:
    plan = _minimal_plan(("q1", "q2", "q3", "q4", "q5"))
    q = plan.questions[0]
    user = build_reflector_query_refinement_user_prompt(
        refined_idea=_minimal_refined_idea_reflect(),
        research_plan=plan,
        question_id=q.id,
        question_text=q.question,
        trigger_signals=["sparse_atoms"],
        evidence_count=1,
        relevance_high_count=0,
        relevance_medium_count=1,
        relevance_low_count=0,
        unique_domain_count=1,
        existing_domains=["ex.com"],
        original_search_queries=["initial-query"],
        evidence_gap_note=None,
        for_cache=True,
    )
    assert user.count(USER_CACHE_ZONE_BOUNDARY) == 2
    zone_a, zone_b, zone_c = user.split(USER_CACHE_ZONE_BOUNDARY)
    assert "You are a search strategist for Fivvle" in zone_a
    assert "<refined_idea>" in zone_b and "<research_plan>" in zone_b
    assert '<research_question id="q1">' in zone_c
    assert "<existing_evidence_summary>" in zone_c


def test_reflector_reflector_query_refinement_v1_cached_semantically_equivalent_to_v1() -> (
    None
):
    import re

    def norm(s: str) -> str:
        return re.sub(r"\s+", " ", s).strip()

    plan = _minimal_plan(("q1", "q2", "q3", "q4", "q5"))
    q = plan.questions[0]
    leg_sys, leg_user = reflector_query_refinement_v1_legacy_flat_user_and_system(
        question_id=q.id,
        question_text=q.question,
        trigger_signals=["sparse_atoms"],
        evidence_count=1,
        relevance_high_count=0,
        relevance_medium_count=1,
        relevance_low_count=0,
        unique_domain_count=1,
        existing_domains=["ex.com"],
        original_search_queries=["initial-query"],
        evidence_gap_note=None,
    )
    cached_user = build_reflector_query_refinement_user_prompt(
        refined_idea=_minimal_refined_idea_reflect(),
        research_plan=plan,
        question_id=q.id,
        question_text=q.question,
        trigger_signals=["sparse_atoms"],
        evidence_count=1,
        relevance_high_count=0,
        relevance_medium_count=1,
        relevance_low_count=0,
        unique_domain_count=1,
        existing_domains=["ex.com"],
        original_search_queries=["initial-query"],
        evidence_gap_note=None,
        for_cache=True,
    )
    flat = norm(cached_user.replace(USER_CACHE_ZONE_BOUNDARY, ""))
    assert norm(leg_sys) in flat
    assert norm(leg_user) in flat
    for anchor in (
        "EVIDENCE-ONLY RULE",
        "TRIGGER-AWARE REFINEMENT",
        "SECURITY NOTICE",
        "<task>",
        "<existing_evidence_summary>",
        "<closing_instruction>",
        "trigger_signals",
    ):
        assert anchor in flat
    assert REFLECTOR_PROMPT_NAME == "reflector_query_refinement_v1_cached"


@pytest.mark.asyncio
async def test_reflector_falls_back_when_cache_breakpoints_none() -> None:
    q = _research_question("q1")
    ro = _make_reader_output("q1", [])
    db = MagicMock(spec=[])
    draft = _RefinedQueryListDraft(queries=["x", "y"])
    captured: dict = {}

    async def capture_complete(*_a, **kw):
        captured.update(kw)
        return draft, _llm_meta()

    with patch(
        "app.services.reflector_service.llm_client.complete_structured",
        AsyncMock(side_effect=capture_complete),
    ):
        await _refine_queries_for_question(
            db=db,
            experiment_id=uuid4(),
            question=q,
            reader_output=ro,
            triggers=["sparse_atoms"],
            refined_idea=_minimal_refined_idea_reflect(),
            research_plan=_minimal_plan(("q1", "q2", "q3", "q4", "q5")),
            cache_breakpoints=None,
        )

    assert captured["cache_breakpoints"] is None
    assert USER_CACHE_ZONE_BOUNDARY not in captured["user"]
