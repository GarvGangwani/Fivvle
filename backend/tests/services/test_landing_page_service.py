"""Unit tests for landing page copy normalization helpers."""

from __future__ import annotations

from app.schemas.landing_page import (
    BrandDirection,
    CustomerIntelligence,
    LandingPageInputModel,
    LandingPageStrategy,
    OfferCore,
    PositioningIntelligence,
    ProblemIntelligence,
    ProofIntelligence,
)
from app.schemas.refinement import RefinedIdea
from app.services.landing_page_service import (
    _ensure_complete_copy_json,
    _scrub_competitor_names_from_copy,
)


def _minimal_input_model(*, competitors: list[str] | None = None) -> LandingPageInputModel:
    return LandingPageInputModel(
        offer_core=OfferCore(
            core_offer="Voice handoff notes",
            one_line_pitch="Speak notes; get structured handoff output fast.",
            transformation_promise="Cut typing time before shift change.",
        ),
        problem_intelligence=ProblemIntelligence(
            pain_points=["Handoff notes eat the last minutes of every shift."],
            urgency="Every delayed handoff slows the next team.",
            alternatives="Typing into shared docs and copy-paste workarounds.",
        ),
        customer_intelligence=CustomerIntelligence(
            icp="Clinical staff on busy shifts",
            buyer_psychology="Frustrated by repetitive typing",
            barriers="No time to learn new tools",
            willingness_to_pay="Unknown for waitlist",
        ),
        positioning_intelligence=PositioningIntelligence(
            competitors=competitors or ["Notion", "Epic"],
            gaps="Faster structured capture",
            differentiators="Voice-first structured output",
            white_space="Shift-change workflow",
        ),
        brand_direction=BrandDirection(
            tone="confident",
            visual_direction="clean clinical",
            trust_style="practical",
        ),
        proof_intelligence=ProofIntelligence(
            traction_signals=["Strong demand in shift-work settings"],
            social_proof_hooks=["Structured output without template setup"],
            top_objections=["Will this slow me down?"],
            objection_rebuttals={
                "Will this slow me down?": "Capture takes under five minutes.",
            },
        ),
        page_goal="waitlist",
    )


def _minimal_refined_idea() -> RefinedIdea:
    return RefinedIdea.model_validate(
        {
            "refined_one_liner": "Voice handoff notes for busy shifts.",
            "target_audience": "Clinical staff drowning in end-of-shift typing.",
            "value_proposition": "Turn spoken notes into structured handoff output fast.",
            "risks": [
                "Do teams already use an approved documentation tool?",
                "Will voice capture work in noisy environments?",
                "Can output match existing handoff formats?",
            ],
            "headline": "Handoff notes written for you — fast",
            "subheadline": "Speak your notes; get structured output ready to hand off.",
            "cta_text": "Join the waitlist",
        }
    )


def test_comparison_fallback_uses_generic_label_not_competitor() -> None:
    input_model = _minimal_input_model(competitors=["Notion"])
    strategy = LandingPageStrategy(
        page_type="waitlist",
        messaging_angle="Faster handoff capture",
        section_sequence=["comparison"],
        cta_strategy=["Early access scarcity"],
        copy_framework="PAS",
    )

    completed = _ensure_complete_copy_json(
        copy_json={},
        strategy=strategy,
        input_model=input_model,
        refined_idea=_minimal_refined_idea(),
    )

    assert completed["comparison"]["competitor_name"] == "The old way"


def test_scrub_competitor_names_from_copy_replaces_known_names() -> None:
    copy_json = {
        "hero": {
            "headline": "Leave Notion docs behind",
            "subheadline": "A better path than Epic workflows",
            "cta": "Join the waitlist",
        },
        "comparison": {
            "metric_label": "Speed",
            "competitor_name": "Notion",
            "our_features": ["Faster capture"],
            "competitor_features": ["Manual copying"],
        },
    }

    scrubbed = _scrub_competitor_names_from_copy(copy_json, ["Notion", "Epic"])

    assert scrubbed["comparison"]["competitor_name"] == "The old way"
    assert "notion" not in scrubbed["hero"]["headline"].lower()
    assert "epic" not in scrubbed["hero"]["subheadline"].lower()
