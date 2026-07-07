"""Reasoning Engine — business construction intelligence layer.

Runs deterministically after Reflector evidence analysis and before
Synthesizer communication. Produces structured mechanisms, hypotheses,
debates, predictions, founder decisions, and business components.

Stages (logical, single service module):
  1. Observation clustering (from evidence analysis)
  2. Mechanism builder
  3. Hypothesis generator
  4. Debate layer
  5. Prediction engine
  6. Founder decision engine
  7. Business construction layer
"""

from __future__ import annotations

from app.logging_config import get_logger
from app.schemas.business_construction import (
    BusinessComponent,
    BusinessComponentType,
    EvidenceAnalysisResult,
    EvidenceCluster,
    FounderDecision,
    Hypothesis,
    HypothesisDebate,
    Mechanism,
    Prediction,
    ReasoningEngineOutput,
)
from app.schemas.refinement import RefinedIdea

_logger = get_logger(__name__)

_ENGINE_VERSION = "v1"

_HYPOTHESIS_TEMPLATES: dict[str, list[str]] = {
    "market": [
        "Demand for this category is weaker than the founder assumes.",
        "Demand exists but is concentrated in a narrower wedge than planned.",
        "Market timing is favorable but only for a specific sub-segment.",
    ],
    "competition": [
        "Incumbents already satisfy the core job-to-be-done.",
        "Competition is fragmented — a focused wedge can win.",
        "Competitors failed due to structural retention issues, not lack of demand.",
    ],
    "customer": [
        "The stated buyer is not the actual economic decision-maker.",
        "Pain is real but not urgent enough to drive switching.",
        "Customers need trust and proof before adopting a new vendor.",
    ],
    "distribution": [
        "Distribution is the primary bottleneck, not product quality.",
        "A single channel (community or partnerships) must anchor GTM.",
        "Self-serve acquisition will underperform without social proof.",
    ],
    "regulatory": [
        "Compliance requirements will slow onboarding unless scoped carefully.",
        "Regulatory risk is manageable with a narrow initial use case.",
        "Privacy constraints require deferred data collection.",
    ],
    "product": [
        "Retention is structurally difficult without recurring engagement loops.",
        "Onboarding friction is the dominant activation blocker.",
        "The MVP scope is too broad for the first validation cycle.",
    ],
    "general": [
        "The idea needs sharper positioning before scaling distribution.",
        "Evidence is too thin to commit — run focused validation experiments first.",
        "A pivot toward a narrower ICP would improve signal quality.",
    ],
}

_DECISION_ACTIONS: dict[str, str] = {
    "market": "Define a measurable demand proxy and validate it before building full product scope.",
    "competition": "Position against the weakest incumbent substitute with a concrete differentiation claim.",
    "customer": "Interview 8–12 ICP buyers and map the real budget holder before finalizing packaging.",
    "distribution": "Pick one primary acquisition channel and run a 2-week distribution experiment.",
    "regulatory": "Scope v1 to the lowest-compliance workflow and document data handling upfront.",
    "product": "Design onboarding for time-to-value under 10 minutes with a single hero workflow.",
    "general": "Ship a narrow validation experiment that tests the riskiest assumption first.",
}


def _build_mechanisms(
    clusters: list[EvidenceCluster],
    analysis: EvidenceAnalysisResult,
) -> list[Mechanism]:
    atoms_by_id = {a.atom_id: a for a in analysis.atoms}
    mechanisms: list[Mechanism] = []

    for index, cluster in enumerate(clusters):
        if len(cluster.atom_ids) < 1:
            continue
        sample_observations = [
            atoms_by_id[aid].observation
            for aid in cluster.atom_ids[:3]
            if aid in atoms_by_id
        ]
        joined = " ".join(sample_observations)[:240]
        statement = (
            f"Across {len(cluster.atom_ids)} source(s), {cluster.theme} evidence suggests: "
            f"{joined}"
        )
        mechanisms.append(
            Mechanism(
                mechanism_id=f"m-{index + 1}",
                cluster_id=cluster.cluster_id,
                statement=statement,
                supporting_atom_ids=cluster.atom_ids[:10],
                confidence=cluster.dominant_confidence,
            )
        )
    return mechanisms


def _generate_hypotheses(
    clusters: list[EvidenceCluster],
    mechanisms: list[Mechanism],
) -> list[Hypothesis]:
    hypotheses: list[Hypothesis] = []
    mechanism_by_cluster = {m.cluster_id: m for m in mechanisms}
    label_letters = "ABC"

    for cluster in clusters:
        templates = _HYPOTHESIS_TEMPLATES.get(cluster.theme, _HYPOTHESIS_TEMPLATES["general"])
        mechanism = mechanism_by_cluster.get(cluster.cluster_id)
        for idx, template in enumerate(templates[:3]):
            hypotheses.append(
                Hypothesis(
                    hypothesis_id=f"h-{cluster.cluster_id}-{idx + 1}",
                    cluster_id=cluster.cluster_id,
                    label=label_letters[idx],
                    statement=template,
                    mechanism_id=mechanism.mechanism_id if mechanism else None,
                )
            )
    return hypotheses


def _run_debate_layer(
    hypotheses: list[Hypothesis],
    analysis: EvidenceAnalysisResult,
) -> list[HypothesisDebate]:
    atoms_by_id = {a.atom_id: a for a in analysis.atoms}
    contradiction_atoms: set[str] = set()
    for contradiction in analysis.contradictions:
        contradiction_atoms.update(contradiction.atom_ids)

    debates: list[HypothesisDebate] = []
    by_cluster: dict[str, list[Hypothesis]] = {}
    for hypothesis in hypotheses:
        by_cluster.setdefault(hypothesis.cluster_id, []).append(hypothesis)

    for cluster_id, cluster_hypotheses in by_cluster.items():
        cluster_atom_ids = next(
            (c.atom_ids for c in analysis.clusters if c.cluster_id == cluster_id),
            [],
        )
        best: HypothesisDebate | None = None
        best_score = -1

        for hypothesis in cluster_hypotheses:
            supporting = [
                aid
                for aid in cluster_atom_ids
                if aid in atoms_by_id and aid not in contradiction_atoms
            ][:5]
            contradicting = [
                aid for aid in cluster_atom_ids if aid in contradiction_atoms
            ][:3]
            score = len(supporting) - len(contradicting)
            debate = HypothesisDebate(
                hypothesis_id=hypothesis.hypothesis_id,
                supporting_atom_ids=supporting,
                contradicting_atom_ids=contradicting,
                confidence="high" if score >= 3 else "medium" if score >= 1 else "low",
                prediction_if_true=(
                    f"If true, {hypothesis.statement} the founder should prioritize "
                    f"validation experiments targeting {hypothesis.label}-class risks."
                ),
                prediction_if_false=(
                    f"If false, alternative explanations in cluster {cluster_id} "
                    "likely dominate — revisit positioning and ICP assumptions."
                ),
                selected=False,
            )
            if score > best_score:
                best_score = score
                best = debate

        if best is not None:
            best = best.model_copy(update={"selected": True})
            debates.append(best)
        debates.extend(
            d
            for d in [
                HypothesisDebate(
                    hypothesis_id=h.hypothesis_id,
                    supporting_atom_ids=[],
                    contradicting_atom_ids=[],
                    confidence="low",
                    prediction_if_true=f"Hold {h.label} as a secondary explanation.",
                    prediction_if_false=f"Deprioritize {h.label} if validation contradicts it.",
                    selected=False,
                )
                for h in cluster_hypotheses
                if best is None or h.hypothesis_id != best.hypothesis_id
            ]
        )
    return debates


def _generate_predictions(mechanisms: list[Mechanism]) -> list[Prediction]:
    predictions: list[Prediction] = []
    for index, mechanism in enumerate(mechanisms):
        predictions.append(
            Prediction(
                prediction_id=f"p-{index + 1}",
                mechanism_id=mechanism.mechanism_id,
                statement=(
                    f"Unless the founder addresses the mechanism above, "
                    f"similar startups in this space will repeat the same "
                    f"{mechanism.statement[:120].lower()} pattern."
                ),
                confidence=mechanism.confidence,
            )
        )
    return predictions


def _generate_founder_decisions(
    debates: list[HypothesisDebate],
    hypotheses: list[Hypothesis],
    mechanisms: list[Mechanism],
    clusters: list[EvidenceCluster],
) -> list[FounderDecision]:
    hypothesis_by_id = {h.hypothesis_id: h for h in hypotheses}
    mechanism_by_id = {m.mechanism_id: m for m in mechanisms}
    cluster_by_id = {c.cluster_id: c for c in clusters}
    decisions: list[FounderDecision] = []

    for index, debate in enumerate([d for d in debates if d.selected]):
        hypothesis = hypothesis_by_id.get(debate.hypothesis_id)
        if hypothesis is None:
            continue
        cluster = cluster_by_id.get(hypothesis.cluster_id)
        theme = cluster.theme if cluster else "general"
        mechanism = (
            mechanism_by_id.get(hypothesis.mechanism_id)
            if hypothesis.mechanism_id
            else None
        )
        decisions.append(
            FounderDecision(
                decision_id=f"d-{index + 1}",
                insight=hypothesis.statement,
                business_implication=(
                    mechanism.statement[:400] if mechanism else hypothesis.statement
                ),
                action=_DECISION_ACTIONS.get(theme, _DECISION_ACTIONS["general"]),
                related_hypothesis_id=hypothesis.hypothesis_id,
                related_mechanism_id=mechanism.mechanism_id if mechanism else None,
                confidence=debate.confidence,
            )
        )
    return decisions


def _construct_business_components(
    refined_idea: RefinedIdea,
    decisions: list[FounderDecision],
    mechanisms: list[Mechanism],
) -> list[BusinessComponent]:
    decision_ids = [d.decision_id for d in decisions]
    mechanism_ids = [m.mechanism_id for m in mechanisms]
    confidence = decisions[0].confidence if decisions else "medium"

    specs: list[tuple[BusinessComponentType, str, str]] = [
        (
            "customer_definition",
            "Customer definition",
            refined_idea.target_audience,
        ),
        (
            "positioning",
            "Positioning",
            refined_idea.refined_one_liner,
        ),
        (
            "value_proposition",
            "Value proposition",
            refined_idea.value_proposition,
        ),
        (
            "distribution_strategy",
            "Distribution strategy",
            next(
                (d.action for d in decisions if d.decision_id.startswith("d-")),
                "Validate one primary acquisition channel before scaling spend.",
            ),
        ),
        (
            "market_wedge",
            "Market wedge",
            (
                mechanisms[0].statement[:500]
                if mechanisms
                else "Narrow to the highest-signal customer wedge from research."
            ),
        ),
        (
            "pricing_logic",
            "Pricing logic",
            "Anchor pricing to validated willingness-to-pay from ICP interviews — not competitor list prices alone.",
        ),
        (
            "business_model",
            "Business model",
            f"Deliver {refined_idea.refined_one_liner[:200]} with measurable activation and retention milestones.",
        ),
        (
            "competitive_differentiation",
            "Competitive differentiation",
            (
                mechanisms[1].statement[:500]
                if len(mechanisms) > 1
                else "Differentiate on speed-to-value and trust signals competitors under-serve."
            ),
        ),
        (
            "validation_experiments",
            "Validation experiments",
            "; ".join(d.action for d in decisions[:3])
            or "Run a 2-week smoke test on the riskiest assumption.",
        ),
        (
            "execution_priorities",
            "Execution priorities",
            "; ".join(d.insight for d in decisions[:3])
            or "Sharpen ICP, prove demand proxy, then expand scope.",
        ),
    ]

    return [
        BusinessComponent(
            component_type=component_type,
            title=title,
            content=content,
            supporting_decision_ids=decision_ids[:5],
            supporting_mechanism_ids=mechanism_ids[:5],
            confidence=confidence,
        )
        for component_type, title, content in specs
    ]


def execute_reasoning_engine(
    *,
    refined_idea: RefinedIdea,
    evidence_analysis: EvidenceAnalysisResult,
) -> ReasoningEngineOutput:
    """Run all Reasoning Engine stages and return structured business intelligence."""
    clusters = evidence_analysis.clusters
    mechanisms = _build_mechanisms(clusters, evidence_analysis)
    hypotheses = _generate_hypotheses(clusters, mechanisms)
    debates = _run_debate_layer(hypotheses, evidence_analysis)
    predictions = _generate_predictions(mechanisms)
    founder_decisions = _generate_founder_decisions(
        debates, hypotheses, mechanisms, clusters
    )
    business_components = _construct_business_components(
        refined_idea, founder_decisions, mechanisms
    )

    output = ReasoningEngineOutput(
        engine_version=_ENGINE_VERSION,
        clusters=clusters,
        mechanisms=mechanisms,
        hypotheses=hypotheses,
        debates=debates,
        predictions=predictions,
        founder_decisions=founder_decisions,
        business_components=business_components,
    )

    _logger.info(
        "reasoning engine complete",
        engine_version=_ENGINE_VERSION,
        cluster_count=len(clusters),
        mechanism_count=len(mechanisms),
        hypothesis_count=len(hypotheses),
        founder_decision_count=len(founder_decisions),
        business_component_count=len(business_components),
    )
    return output
