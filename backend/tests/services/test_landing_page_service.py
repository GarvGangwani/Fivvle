"""Unit tests for landing page copy normalization helpers."""

from __future__ import annotations

import pytest

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


@pytest.mark.asyncio
async def test_persist_landing_page_row_stamps_refined_idea_version() -> None:
    from uuid import uuid4

    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from app.config import get_settings
    from app.db.enums import ExperimentStatus
    from app.db.models.experiment import Experiment
    from app.db.models.landing_page import LandingPage
    from app.db.models.user import User
    from app.services.landing_page_service import _persist_landing_page_row

    exp_id = uuid4()
    engine = create_async_engine(get_settings().database_url, pool_size=1, max_overflow=0)
    sm = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
    try:
        async with sm() as session:
            user = User(
                firebase_uid=f"lp-riv-{exp_id}",
                email=f"lp-riv-{exp_id}@example.com",
                name="t",
            )
            session.add(user)
            await session.flush()
            experiment = Experiment(
                id=exp_id,
                user_id=user.id,
                raw_idea="idea long enough for landing page stamp test content",
                refined_idea=_minimal_refined_idea().model_dump(mode="json"),
                refined_idea_version=4,
                status=ExperimentStatus.RESEARCH_READY,
                name="Stamp Test",
            )
            session.add(experiment)
            await session.commit()

        async with sm() as session:
            experiment = (
                await session.execute(select(Experiment).where(Experiment.id == exp_id))
            ).scalar_one()
            row = await _persist_landing_page_row(
                session,
                experiment=experiment,
                copy_json={"hero": {"headline": "H", "subheadline": "S", "cta": "Join"}},
                page_json={"meta": {}},
                template_id="dark-premium",
                refined_idea=_minimal_refined_idea(),
                input_model=_minimal_input_model(),
                page_goal="waitlist",
            )
            await session.commit()
            assert row.refined_idea_version == 4

        async with sm() as session:
            stored = (
                await session.execute(
                    select(LandingPage.refined_idea_version).where(
                        LandingPage.experiment_id == exp_id
                    )
                )
            ).scalar_one()
        assert stored == 4
    finally:
        await engine.dispose()
