"""Evidence atom collection — maps Reader output to canonical EvidenceAtom models.

Reader continues to emit ExtractedEvidence via LLM; this module is the
adapter layer that enforces the Evidence Atom contract for downstream
Reflector analysis and Reasoning Engine stages.
"""

from __future__ import annotations

from app.schemas.business_construction import EvidenceAtom
from app.schemas.planner import ResearchPlan
from app.schemas.reader import ExtractedEvidence, ReaderOutput

_CONTEXT_MAX = 400


def _atom_id(question_id: str, index: int) -> str:
    return f"{question_id}-a{index + 1}"


def evidence_atom_from_extracted(
    *,
    question_id: str,
    question_text: str,
    index: int,
    evidence: ExtractedEvidence,
) -> EvidenceAtom:
    """Map one validated ExtractedEvidence row to an EvidenceAtom."""
    entity_context = ", ".join(evidence.named_entities[:6])
    context_parts = [f"question: {question_text[:120]}"]
    if entity_context:
        context_parts.append(f"entities: {entity_context}")
    context = " | ".join(context_parts)
    if len(context) > _CONTEXT_MAX:
        context = context[: _CONTEXT_MAX - 1] + "…"
    return EvidenceAtom(
        atom_id=_atom_id(question_id, index),
        question_id=question_id,
        observation=evidence.paraphrase,
        source_url=evidence.source_url,
        confidence=evidence.relevance,
        context=context,
        supporting_excerpt=evidence.verbatim_quote,
    )


def collect_evidence_atoms(
    reader_outputs: dict[str, ReaderOutput],
    research_plan: ResearchPlan,
) -> list[EvidenceAtom]:
    """Flatten all Reader outputs into a deduplicated evidence atom list."""
    question_text_by_id = {q.id: q.question for q in research_plan.questions}
    atoms: list[EvidenceAtom] = []
    seen_urls: set[tuple[str, str]] = set()

    for question in research_plan.questions:
        qid = question.id
        reader_output = reader_outputs.get(qid)
        if reader_output is None:
            continue
        question_text = question_text_by_id.get(qid, question.question)
        for index, evidence in enumerate(reader_output.extracted_evidence):
            key = (qid, evidence.source_url)
            if key in seen_urls:
                continue
            seen_urls.add(key)
            atoms.append(
                evidence_atom_from_extracted(
                    question_id=qid,
                    question_text=question_text,
                    index=index,
                    evidence=evidence,
                )
            )
    return atoms
