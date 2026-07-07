"""Service tests for synthesizer input evidence capping."""

from __future__ import annotations

from copy import deepcopy

from app.schemas.planner import ResearchPlan, ResearchQuestion
from app.schemas.reader import ExtractedEvidence, ReaderOutput
from app.schemas.refinement import RefinedIdea
from app.services.synthesizer_input import (
    SYNTHESIZER_EVIDENCE_ATOMS_PER_QUESTION_CAP,
    _cap_reader_evidence,
    build_synthesizer_input,
)


def _minimal_refined_idea() -> RefinedIdea:
    return RefinedIdea(
        refined_one_liner="Test idea.",
        target_audience="Ops managers.",
        value_proposition="Saves time.",
        risks=["Risk one?", "Risk two?", "Risk three?"],
        headline="Headline",
        subheadline="Subheadline",
        cta_text="Join",
    )


def _minimal_plan() -> ResearchPlan:
    return ResearchPlan(
        questions=[
            ResearchQuestion(
                id=f"q{i}",
                question=f"Q{i}?",
                rationale="r",
                search_queries=[f"sq{i}"],
            )
            for i in range(1, 8)
        ]
    )


def _ev(idx: int, relevance: str = "high") -> ExtractedEvidence:
    return ExtractedEvidence(
        source_url=f"https://example.com/{idx}",
        relevance=relevance,  # type: ignore[arg-type]
        verbatim_quote=None,
        paraphrase=f"p-{idx}",
        named_entities=[],
    )


def _reader_outputs(
    counts: dict[str, int],
    *,
    relevance: str = "high",
    unsafe_construct: bool = False,
) -> dict[str, ReaderOutput]:
    outputs: dict[str, ReaderOutput] = {}
    for qid, n in counts.items():
        evidence = [_ev(i + 1, relevance=relevance) for i in range(n)]
        if unsafe_construct and n > 10:
            outputs[qid] = ReaderOutput.model_construct(
                question_id=qid,
                extracted_evidence=evidence,
                evidence_gap_note=None,
            )
        else:
            outputs[qid] = ReaderOutput(
                question_id=qid,
                extracted_evidence=evidence,
                evidence_gap_note=None,
            )
    return outputs


def test_cap_noop_when_all_questions_under_limit() -> None:
    reader_outputs = _reader_outputs({f"q{i}": 3 for i in range(1, 8)})
    capped = _cap_reader_evidence(reader_outputs, cap=10)
    assert capped == reader_outputs


def test_cap_truncates_when_question_over_limit() -> None:
    counts = {f"q{i}": 5 for i in range(1, 8)}
    counts["q3"] = 15
    reader_outputs = _reader_outputs(counts, unsafe_construct=True)
    capped = _cap_reader_evidence(reader_outputs, cap=10)
    assert len(capped["q3"].extracted_evidence) == 10
    for i in range(1, 8):
        qid = f"q{i}"
        if qid == "q3":
            continue
        assert len(capped[qid].extracted_evidence) == 5


def test_cap_preserves_ranking_signal() -> None:
    mixed = ReaderOutput(
        question_id="q1",
        extracted_evidence=[
            _ev(1, "low"),
            _ev(2, "medium"),
            _ev(3, "high"),
            _ev(4, "low"),
            _ev(5, "high"),
        ],
        evidence_gap_note=None,
    )
    capped = _cap_reader_evidence({"q1": mixed}, cap=3)
    kept = capped["q1"].extracted_evidence
    assert [e.source_url for e in kept] == [
        "https://example.com/2",
        "https://example.com/3",
        "https://example.com/5",
    ]
    assert all(e.relevance in {"high", "medium"} for e in kept)


def test_cap_tiebreak_keeps_earliest_low_and_original_order() -> None:
    evidence = [
        _ev(1, "low"),
        _ev(2, "high"),
        _ev(3, "medium"),
        _ev(4, "low"),
        _ev(5, "high"),
        _ev(6, "medium"),
        _ev(7, "low"),
        _ev(8, "medium"),
        _ev(9, "high"),
        _ev(10, "medium"),
    ]
    reader_outputs = {
        "q1": ReaderOutput(
            question_id="q1",
            extracted_evidence=evidence,
            evidence_gap_note=None,
        )
    }
    capped = _cap_reader_evidence(reader_outputs, cap=8)
    kept = capped["q1"].extracted_evidence
    assert len(kept) == 8
    assert [e.relevance for e in kept].count("high") == 3
    assert [e.relevance for e in kept].count("medium") == 4
    assert [e.relevance for e in kept].count("low") == 1
    assert [e.source_url for e in kept] == [
        "https://example.com/1",
        "https://example.com/2",
        "https://example.com/3",
        "https://example.com/5",
        "https://example.com/6",
        "https://example.com/8",
        "https://example.com/9",
        "https://example.com/10",
    ]


def test_cap_does_not_mutate_input() -> None:
    reader_outputs = _reader_outputs({"q1": 12, "q2": 2}, unsafe_construct=True)
    snapshot = deepcopy(reader_outputs)
    _ = _cap_reader_evidence(reader_outputs, cap=8)
    assert reader_outputs == snapshot


def test_build_synthesizer_input_applies_cap_end_to_end() -> None:
    reader_outputs = _reader_outputs(
        {"q1": 12, "q2": 4, "q3": 9, "q4": 3, "q5": 2, "q6": 1, "q7": 0},
        unsafe_construct=True,
    )
    synth_input = build_synthesizer_input(
        refined_idea=_minimal_refined_idea(),
        research_plan=_minimal_plan(),
        reader_outputs=reader_outputs,
        rubric_version="v1",
    )
    assert (
        len(synth_input.reader_outputs["q1"].extracted_evidence)
        == SYNTHESIZER_EVIDENCE_ATOMS_PER_QUESTION_CAP
    )
    assert (
        len(synth_input.reader_outputs["q3"].extracted_evidence)
        == SYNTHESIZER_EVIDENCE_ATOMS_PER_QUESTION_CAP
    )
    assert len(synth_input.reader_outputs["q2"].extracted_evidence) == 4
