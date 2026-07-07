"""Tests for evidence analysis and Reasoning Engine stages."""

from __future__ import annotations

from app.schemas.business_construction import EvidenceAtom
from app.schemas.planner import ResearchPlan, ResearchQuestion
from app.schemas.reader import ExtractedEvidence, ReaderOutput
from app.schemas.refinement import RefinedIdea
from app.services.evidence_analysis_service import analyze_evidence
from app.services.evidence_atoms import collect_evidence_atoms
from app.services.reasoning_engine_service import execute_reasoning_engine


def _refined_idea() -> RefinedIdea:
    return RefinedIdea(
        refined_one_liner="AI HR policy bot for Slack",
        target_audience="Ops managers at 50-500 person companies",
        value_proposition="Cuts repeat policy questions",
        risks=["Incumbent tools", "Compliance", "Adoption"],
        headline="Policy answers in Slack",
        subheadline="Connect your handbook",
        cta_text="Join waitlist",
    )


def _plan() -> ResearchPlan:
    return ResearchPlan(
        questions=[
            ResearchQuestion(
                id=f"q{i}",
                question=f"Question {i}?",
                rationale=f"Rationale {i}",
                search_queries=[f"query {i}"],
            )
            for i in range(1, 6)
        ]
    )


def _reader_outputs() -> dict[str, ReaderOutput]:
    outputs = {
        "q1": ReaderOutput(
            question_id="q1",
            extracted_evidence=[
                ExtractedEvidence(
                    source_url="https://example.com/growth",
                    relevance="high",
                    verbatim_quote="demand is growing rapidly",
                    paraphrase="Analysts report growing demand for HR automation in Slack.",
                    named_entities=["Guru"],
                ),
                ExtractedEvidence(
                    source_url="https://example.com/decline",
                    relevance="medium",
                    verbatim_quote=None,
                    paraphrase="Some teams report adoption decline after pilot programs fail.",
                    named_entities=[],
                ),
            ],
        ),
        "q2": ReaderOutput(
            question_id="q2",
            extracted_evidence=[
                ExtractedEvidence(
                    source_url="https://example.com/competitors",
                    relevance="high",
                    verbatim_quote=None,
                    paraphrase="Guru and Notion AI dominate knowledge management integrations.",
                    named_entities=["Guru", "Notion AI"],
                ),
            ],
            evidence_gap_note="Limited pricing data found.",
        ),
    }
    for qid in ("q3", "q4", "q5"):
        outputs[qid] = ReaderOutput(question_id=qid, extracted_evidence=[])
    return outputs


def test_collect_evidence_atoms_maps_reader_output() -> None:
    atoms = collect_evidence_atoms(_reader_outputs(), _plan())
    assert len(atoms) == 3
    assert atoms[0].observation.startswith("Analysts report")
    assert atoms[0].confidence == "high"
    assert "Guru" in atoms[0].context


def test_analyze_evidence_clusters_and_contradictions() -> None:
    reader_outputs = _reader_outputs()
    atoms = collect_evidence_atoms(reader_outputs, _plan())
    analysis = analyze_evidence(
        atoms,
        reader_outputs=reader_outputs,
        research_plan=_plan(),
    )
    assert len(analysis.clusters) >= 1
    assert analysis.evidence_gaps
    assert analysis.atoms[0].atom_id.startswith("q1-a")


def test_reasoning_engine_produces_business_components() -> None:
    reader_outputs = _reader_outputs()
    atoms = collect_evidence_atoms(reader_outputs, _plan())
    analysis = analyze_evidence(
        atoms,
        reader_outputs=reader_outputs,
        research_plan=_plan(),
    )
    reasoning = execute_reasoning_engine(
        refined_idea=_refined_idea(),
        evidence_analysis=analysis,
    )
    assert reasoning.mechanisms
    assert reasoning.hypotheses
    assert reasoning.founder_decisions
    assert len(reasoning.business_components) == 10
    component_types = {c.component_type for c in reasoning.business_components}
    assert "customer_definition" in component_types
    assert "execution_priorities" in component_types


def test_reasoning_engine_debate_selects_one_hypothesis_per_cluster() -> None:
    reader_outputs = _reader_outputs()
    atoms = collect_evidence_atoms(reader_outputs, _plan())
    analysis = analyze_evidence(
        atoms,
        reader_outputs=reader_outputs,
        research_plan=_plan(),
    )
    reasoning = execute_reasoning_engine(
        refined_idea=_refined_idea(),
        evidence_analysis=analysis,
    )
    selected = [d for d in reasoning.debates if d.selected]
    assert len(selected) >= 1
