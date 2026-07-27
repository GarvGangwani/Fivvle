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
                edited_doc_version=3,
            )
            await session.commit()
            assert row.refined_idea_version == 4
            assert row.edited_doc_version == 3

        async with sm() as session:
            stored = (
                await session.execute(
                    select(
                        LandingPage.refined_idea_version,
                        LandingPage.edited_doc_version,
                    ).where(LandingPage.experiment_id == exp_id)
                )
            ).one()
        assert stored[0] == 4
        assert stored[1] == 3

        # Upsert path: re-persist with a newer edited_doc stamp.
        async with sm() as session:
            experiment = (
                await session.execute(select(Experiment).where(Experiment.id == exp_id))
            ).scalar_one()
            row = await _persist_landing_page_row(
                session,
                experiment=experiment,
                copy_json={"hero": {"headline": "H2", "subheadline": "S", "cta": "Join"}},
                page_json={"meta": {}},
                template_id="dark-premium",
                refined_idea=_minimal_refined_idea(),
                input_model=_minimal_input_model(),
                page_goal="waitlist",
                edited_doc_version=5,
            )
            await session.commit()
            assert row.edited_doc_version == 5
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_persist_landing_page_row_stamps_zero_when_edited_doc_version_none() -> None:
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
                firebase_uid=f"lp-edv0-{exp_id}",
                email=f"lp-edv0-{exp_id}@example.com",
                name="t",
            )
            session.add(user)
            await session.flush()
            session.add(
                Experiment(
                    id=exp_id,
                    user_id=user.id,
                    raw_idea="idea long enough for landing page zero stamp test content",
                    refined_idea=_minimal_refined_idea().model_dump(mode="json"),
                    status=ExperimentStatus.RESEARCH_READY,
                    name="Zero Stamp",
                )
            )
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
                edited_doc_version=None,
            )
            await session.commit()
            assert row.edited_doc_version == 0

        async with sm() as session:
            stored = (
                await session.execute(
                    select(LandingPage.edited_doc_version).where(
                        LandingPage.experiment_id == exp_id
                    )
                )
            ).scalar_one()
        assert stored == 0
    finally:
        await engine.dispose()


def test_strategist_prompt_includes_founder_narrative_when_present() -> None:
    from app.llm.prompts.landing_page import build_lp_strategist_user_prompt
    from tests.services.test_validation_report_editor import _make_report as make_report

    prompt = build_lp_strategist_user_prompt(
        make_report(),
        _minimal_refined_idea(),
        "waitlist",
        edited_narrative="# Founder edit\n\nCanonical framing here.",
        for_cache=False,
    )
    assert "<founder_edited_narrative>" in prompt
    assert "Canonical framing here." in prompt
    assert "prefer the founder's narrative" in prompt


def test_strategist_prompt_omits_narrative_block_when_absent() -> None:
    from app.llm.prompts.landing_page import (
        LP_STRATEGIST_PROMPT_NAME,
        build_lp_strategist_user_prompt,
    )
    from tests.services.test_validation_report_editor import _make_report as make_report

    assert LP_STRATEGIST_PROMPT_NAME == "lp_strategist_v2"
    prompt = build_lp_strategist_user_prompt(
        make_report(),
        _minimal_refined_idea(),
        "waitlist",
        edited_narrative=None,
        for_cache=False,
    )
    assert "Their edited narrative is below" not in prompt
    assert "</founder_edited_narrative>" not in prompt


@pytest.mark.asyncio
async def test_generate_landing_page_passes_flattened_edited_doc(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When fetch returns edited_narrative, strategist prompt includes it."""
    from types import SimpleNamespace
    from unittest.mock import AsyncMock
    from uuid import uuid4

    from app.schemas.landing_page import CopyOutput
    from app.services import landing_page_service as lps
    from app.services.landing_page_service import (
        StrategistOutput,
        ValidationReportForLanding,
    )
    from tests.services.test_validation_report_editor import _make_report as make_report

    exp_id = uuid4()
    captured_prompts: list[str] = []
    experiment = SimpleNamespace(
        id=exp_id,
        refined_idea=_minimal_refined_idea().model_dump(mode="json"),
        refined_idea_version=1,
        name="Edit Gen",
    )

    async def _fake_fetch_vr(db, experiment_id):  # type: ignore[no-untyped-def]
        return ValidationReportForLanding(
            report=make_report(),
            edited_narrative="# Founder Voice\n\nPrefer this framing.",
            edited_doc_version=2,
        )

    async def _fake_fetch_exp(db, experiment_id):  # type: ignore[no-untyped-def]
        return experiment

    async def _fake_complete(db, **kwargs):  # type: ignore[no-untyped-def]
        if kwargs.get("prompt_name") == "lp_strategist_v2":
            captured_prompts.append(kwargs["user"])
            strategist = StrategistOutput(
                input_model=_minimal_input_model(),
                strategy=LandingPageStrategy(
                    page_type="waitlist",
                    messaging_angle="angle",
                    section_sequence=["hero", "problem"],
                    cta_strategy=["Join"],
                    copy_framework="PAS",
                ),
            )
            return strategist, SimpleNamespace(cost_usd=0, latency_ms=1)
        copy = CopyOutput(
            copy_json={
                "hero": {"headline": "H", "subheadline": "S", "cta": "Join"},
                "problem": {"heading": "P", "body": "B"},
            }
        )
        return copy, SimpleNamespace(cost_usd=0, latency_ms=1)

    async def _fake_persist(db, **kwargs):  # type: ignore[no-untyped-def]
        return SimpleNamespace(id=uuid4())

    monkeypatch.setattr(lps, "_fetch_validation_report", _fake_fetch_vr)
    monkeypatch.setattr(lps, "_fetch_experiment", _fake_fetch_exp)
    monkeypatch.setattr(lps.llm_client, "complete_structured", _fake_complete)
    monkeypatch.setattr(lps, "theme_to_page_json", lambda *a, **k: {"meta": {}})
    monkeypatch.setattr(lps, "_persist_landing_page_row", _fake_persist)

    db = SimpleNamespace(flush=AsyncMock())
    await lps.generate_landing_page(db, exp_id)

    assert len(captured_prompts) == 1
    assert "Their edited narrative is below" in captured_prompts[0]
    assert "Founder Voice" in captured_prompts[0]
    assert "Prefer this framing." in captured_prompts[0]


@pytest.mark.asyncio
async def test_generate_landing_page_omits_narrative_when_no_edited_doc(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from types import SimpleNamespace
    from unittest.mock import AsyncMock
    from uuid import uuid4

    from app.schemas.landing_page import CopyOutput
    from app.services import landing_page_service as lps
    from app.services.landing_page_service import (
        StrategistOutput,
        ValidationReportForLanding,
    )
    from tests.services.test_validation_report_editor import _make_report as make_report

    exp_id = uuid4()
    captured_prompts: list[str] = []
    experiment = SimpleNamespace(
        id=exp_id,
        refined_idea=_minimal_refined_idea().model_dump(mode="json"),
        refined_idea_version=1,
        name="Raw Gen",
    )

    async def _fake_fetch_vr(db, experiment_id):  # type: ignore[no-untyped-def]
        return ValidationReportForLanding(
            report=make_report(),
            edited_narrative=None,
            edited_doc_version=0,
        )

    async def _fake_fetch_exp(db, experiment_id):  # type: ignore[no-untyped-def]
        return experiment

    async def _fake_complete(db, **kwargs):  # type: ignore[no-untyped-def]
        if kwargs.get("prompt_name") == "lp_strategist_v2":
            captured_prompts.append(kwargs["user"])
            strategist = StrategistOutput(
                input_model=_minimal_input_model(),
                strategy=LandingPageStrategy(
                    page_type="waitlist",
                    messaging_angle="angle",
                    section_sequence=["hero", "problem"],
                    cta_strategy=["Join"],
                    copy_framework="PAS",
                ),
            )
            return strategist, SimpleNamespace(cost_usd=0, latency_ms=1)
        copy = CopyOutput(
            copy_json={
                "hero": {"headline": "H", "subheadline": "S", "cta": "Join"},
                "problem": {"heading": "P", "body": "B"},
            }
        )
        return copy, SimpleNamespace(cost_usd=0, latency_ms=1)

    async def _fake_persist(db, **kwargs):  # type: ignore[no-untyped-def]
        return SimpleNamespace(id=uuid4())

    monkeypatch.setattr(lps, "_fetch_validation_report", _fake_fetch_vr)
    monkeypatch.setattr(lps, "_fetch_experiment", _fake_fetch_exp)
    monkeypatch.setattr(lps.llm_client, "complete_structured", _fake_complete)
    monkeypatch.setattr(lps, "theme_to_page_json", lambda *a, **k: {"meta": {}})
    monkeypatch.setattr(lps, "_persist_landing_page_row", _fake_persist)

    db = SimpleNamespace(flush=AsyncMock())
    await lps.generate_landing_page(db, exp_id)

    assert len(captured_prompts) == 1
    assert "Their edited narrative is below" not in captured_prompts[0]
    assert "</founder_edited_narrative>" not in captured_prompts[0]
