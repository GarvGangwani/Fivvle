"""Evidence analysis — expanded Reflector responsibility (deterministic v1).

Detects contradictions, missing/weak evidence, clusters, and gaps without
making business decisions. Output feeds the Reasoning Engine.
"""

from __future__ import annotations

import re

from app.schemas.business_construction import (
    ClusterTheme,
    EvidenceAnalysisResult,
    EvidenceAtom,
    EvidenceCluster,
    EvidenceContradiction,
)
from app.schemas.planner import ResearchPlan
from app.schemas.reader import ReaderOutput

_POSITIVE_SIGNALS = frozenset(
    {"grow", "growing", "demand", "adopt", "adoption", "increase", "strong", "popular"}
)
_NEGATIVE_SIGNALS = frozenset(
    {"decline", "fail", "failed", "churn", "saturated", "weak", "drop", "struggle"}
)

_THEME_KEYWORDS: dict[ClusterTheme, frozenset[str]] = {
    "market": frozenset({"market", "tam", "demand", "growth", "trend", "size"}),
    "competition": frozenset(
        {"competitor", "competition", "alternative", "incumbent", "substitute"}
    ),
    "customer": frozenset(
        {"customer", "user", "buyer", "founder", "audience", "persona", "pain"}
    ),
    "distribution": frozenset(
        {"distribution", "channel", "acquisition", "gtm", "sales", "marketing"}
    ),
    "regulatory": frozenset(
        {"regulation", "regulatory", "compliance", "legal", "privacy", "gdpr", "hipaa"}
    ),
    "product": frozenset({"product", "feature", "retention", "onboarding", "ux"}),
    "general": frozenset(),
}


def _tokenize(text: str) -> set[str]:
    return {t.lower() for t in re.findall(r"[a-zA-Z]{4,}", text)}


def _sentiment_bucket(text: str) -> str | None:
    tokens = _tokenize(text)
    pos = len(tokens & _POSITIVE_SIGNALS)
    neg = len(tokens & _NEGATIVE_SIGNALS)
    if pos > neg and pos > 0:
        return "positive"
    if neg > pos and neg > 0:
        return "negative"
    return None


def _infer_theme(text: str) -> ClusterTheme:
    tokens = _tokenize(text)
    best_theme: ClusterTheme = "general"
    best_score = 0
    for theme, keywords in _THEME_KEYWORDS.items():
        if theme == "general":
            continue
        score = len(tokens & keywords)
        if score > best_score:
            best_score = score
            best_theme = theme
    return best_theme


def _dominant_confidence(atom_ids: list[str], atoms_by_id: dict[str, EvidenceAtom]) -> str:
    order = {"high": 3, "medium": 2, "low": 1}
    scores: list[int] = []
    for atom_id in atom_ids:
        atom = atoms_by_id.get(atom_id)
        if atom:
            scores.append(order[atom.confidence])
    if not scores:
        return "low"
    avg = sum(scores) / len(scores)
    if avg >= 2.5:
        return "high"
    if avg >= 1.5:
        return "medium"
    return "low"


def _cluster_atoms(atoms: list[EvidenceAtom]) -> list[EvidenceCluster]:
    buckets: dict[ClusterTheme, list[str]] = {}
    atoms_by_id = {a.atom_id: a for a in atoms}
    for atom in atoms:
        theme = _infer_theme(f"{atom.observation} {atom.context}")
        buckets.setdefault(theme, []).append(atom.atom_id)

    clusters: list[EvidenceCluster] = []
    for index, (theme, atom_ids) in enumerate(buckets.items()):
        if not atom_ids:
            continue
        sample = atoms_by_id[atom_ids[0]]
        clusters.append(
            EvidenceCluster(
                cluster_id=f"cl-{index + 1}",
                theme=theme,
                label=f"{theme.replace('_', ' ').title()} signals",
                atom_ids=atom_ids,
                dominant_confidence=_dominant_confidence(atom_ids, atoms_by_id),  # type: ignore[arg-type]
            )
        )
    return clusters


def _detect_contradictions(
    atoms: list[EvidenceAtom],
    clusters: list[EvidenceCluster],
) -> list[EvidenceContradiction]:
    contradictions: list[EvidenceContradiction] = []
    atoms_by_id = {a.atom_id: a for a in atoms}
    counter = 0

    for cluster in clusters:
        if len(cluster.atom_ids) < 2:
            continue
        positive_ids: list[str] = []
        negative_ids: list[str] = []
        for atom_id in cluster.atom_ids:
            atom = atoms_by_id[atom_id]
            bucket = _sentiment_bucket(atom.observation)
            if bucket == "positive":
                positive_ids.append(atom_id)
            elif bucket == "negative":
                negative_ids.append(atom_id)
        if positive_ids and negative_ids:
            counter += 1
            contradictions.append(
                EvidenceContradiction(
                    contradiction_id=f"cx-{counter}",
                    atom_ids=[positive_ids[0], negative_ids[0]],
                    theme=cluster.theme,
                    description=(
                        f"Mixed directional signals within {cluster.theme} theme: "
                        "some sources imply momentum while others imply friction or decline."
                    ),
                    confidence="medium",
                )
            )
    return contradictions


def analyze_evidence(
    atoms: list[EvidenceAtom],
    *,
    reader_outputs: dict[str, ReaderOutput],
    research_plan: ResearchPlan,
) -> EvidenceAnalysisResult:
    """Run deterministic evidence quality analysis (Reflector extension)."""
    missing_evidence: list[str] = []
    evidence_gaps: list[str] = []

    for question in research_plan.questions:
        reader_output = reader_outputs.get(question.id)
        if reader_output is None or len(reader_output.extracted_evidence) == 0:
            missing_evidence.append(
                f"{question.id}: no validated evidence atoms for planned question"
            )
        if reader_output and reader_output.evidence_gap_note:
            evidence_gaps.append(f"{question.id}: {reader_output.evidence_gap_note}")

    weak_evidence_atom_ids = [
        atom.atom_id for atom in atoms if atom.confidence == "low"
    ]
    clusters = _cluster_atoms(atoms)
    contradictions = _detect_contradictions(atoms, clusters)

    return EvidenceAnalysisResult(
        atoms=atoms,
        contradictions=contradictions,
        missing_evidence=missing_evidence,
        weak_evidence_atom_ids=weak_evidence_atom_ids,
        clusters=clusters,
        evidence_gaps=evidence_gaps,
    )
