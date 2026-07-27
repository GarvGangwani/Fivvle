"""PR-4 Step 2 — V2 landing generator reads edited_doc + cascade stamps."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.llm.prompts.landing_page_v2_narrative import (
    LP_RUNTIME_NARRATIVE_PROMPT_NAME,
    build_lp_runtime_narrative_user_prompt,
)
from app.schemas.landing_page_v2 import (
    ComponentPlanSpec,
    ComponentPlannerOutput,
    CreativeDirectorOutput,
    DesignTokenSpec,
    GlobalCreativeDirection,
    NarrativeArchitectOutput,
    NarrativeStageGoal,
    SectionCreativeBrief,
    SectionMetadata,
    VisualComposerOutput,
    VisualElementSpec,
)
from app.schemas.refinement import RefinedIdea
from app.services.validation_report_for_landing import ValidationReportForLanding
from tests.services.test_validation_report_editor import _make_report as make_report


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


def _stage(stage_id: str) -> NarrativeStageGoal:
    return NarrativeStageGoal(
        stage_id=stage_id,
        label=f"Label {stage_id}",
        goal="Make the visitor feel understood about their handoff pain.",
        visitor_feeling="Seen and hopeful",
        objection_addressed=None,
    )


def _minimal_narrative() -> NarrativeArchitectOutput:
    ids = ["shock", "empathy", "hope", "cta"]
    return NarrativeArchitectOutput(
        business_archetype="b2b_saas",
        story_summary="A journey from end-of-shift exhaustion to structured handoff relief.",
        stages=[_stage(i) for i in ids],
        key_objections=["Will this slow me down?"],
        desired_end_state="Visitor joins the waitlist feeling confident.",
        stage_order=ids,
    )


def _minimal_creative(narrative: NarrativeArchitectOutput) -> CreativeDirectorOutput:
    briefs = [
        SectionCreativeBrief(
            stage_id=s.stage_id,
            purpose="Move emotion forward",
            emotional_objective="Build trust",
            visual_objective="Support the copy",
            emotion="hope",
            theme="light",
            layout_intent="centered",
            visual_weight="medium",
            pacing="medium",
            hierarchy="balanced",
            storytelling_role="Advance the journey",
            transition_style="fade",
            atmosphere="calm clinical",
            component_priority=["headline"],
        )
        for s in narrative.stages
    ]
    return CreativeDirectorOutput(
        global_direction=GlobalCreativeDirection(
            visual_style="minimal",
            tone="confident",
            pace="steady",
            typography="minimal_sans",
            color_mode="light",
            accent_family="slate",
            visual_personality="Clean clinical clarity",
        ),
        section_briefs=briefs,
    )


def _minimal_visual(narrative: NarrativeArchitectOutput) -> VisualComposerOutput:
    return VisualComposerOutput(
        visuals=[
            VisualElementSpec(
                stage_id=narrative.stages[0].stage_id,
                visual_type="illustration",
                purpose="Show the handoff moment clearly",
            ),
            VisualElementSpec(
                stage_id=narrative.stages[1].stage_id,
                visual_type="diagram",
                purpose="Explain the capture flow at a glance",
            ),
        ],
        rhythm_notes="Alternate text-heavy beats with a single visual beat.",
    )


def _minimal_planner(narrative: NarrativeArchitectOutput) -> ComponentPlannerOutput:
    components = [
        ComponentPlanSpec(
            id=f"comp-{s.stage_id}",
            stage_id=s.stage_id,
            component="HeroSection" if i == 0 else "FeatureGrid",
            variant="centered",
            headline=f"Headline for {s.stage_id}",
            metadata=SectionMetadata(
                purpose="Advance journey",
                emotion="hope",
                conversion_goal="waitlist",
            ),
        )
        for i, s in enumerate(narrative.stages)
    ]
    return ComponentPlannerOutput(
        design_tokens=DesignTokenSpec(
            color_mode="light",
            accent_family="slate",
            card_style="flat",
            cta_emphasis="bold",
        ),
        components=components,
    )


def test_narrative_prompt_name_is_v2() -> None:
    assert LP_RUNTIME_NARRATIVE_PROMPT_NAME == "lp_runtime_narrative_architect_v2"


def test_narrative_prompt_includes_founder_narrative_when_present() -> None:
    prompt = build_lp_runtime_narrative_user_prompt(
        validation_report=make_report(),
        refined_idea=_minimal_refined_idea(),
        page_goal="waitlist",
        regeneration_hint=None,
        edited_narrative="# Founder edit\n\nCanonical framing here.",
    )
    assert "<founder_edited_narrative>" in prompt
    assert "Canonical framing here." in prompt
    assert "prefer the founder's narrative" in prompt


def test_narrative_prompt_omits_narrative_block_when_absent() -> None:
    prompt = build_lp_runtime_narrative_user_prompt(
        validation_report=make_report(),
        refined_idea=_minimal_refined_idea(),
        page_goal="waitlist",
        regeneration_hint=None,
        edited_narrative=None,
    )
    assert "Their edited narrative is below" not in prompt
    assert "</founder_edited_narrative>" not in prompt


@pytest.mark.asyncio
async def test_load_validation_report_flattens_edited_doc() -> None:
    from app.services import landing_page_v2_service as v2s

    exp_id = uuid4()
    doc = {
        "type": "doc",
        "content": [
            {
                "type": "paragraph",
                "content": [{"type": "text", "text": "Founder Voice Prefer this."}],
            }
        ],
    }
    row = SimpleNamespace(
        raw_report=make_report().model_dump(mode="json"),
        edited_doc=doc,
        edited_doc_version=2,
    )

    class _Result:
        def scalar_one_or_none(self) -> object:
            return row

    db = SimpleNamespace(execute=AsyncMock(return_value=_Result()))
    bundle = await v2s._load_validation_report(db, exp_id)
    assert isinstance(bundle, ValidationReportForLanding)
    assert bundle.edited_doc_version == 2
    assert bundle.edited_narrative is not None
    assert "Founder Voice Prefer this." in bundle.edited_narrative


@pytest.mark.asyncio
async def test_load_validation_report_without_edited_doc() -> None:
    from app.services import landing_page_v2_service as v2s

    exp_id = uuid4()
    row = SimpleNamespace(
        raw_report=make_report().model_dump(mode="json"),
        edited_doc=None,
        edited_doc_version=0,
    )

    class _Result:
        def scalar_one_or_none(self) -> object:
            return row

    db = SimpleNamespace(execute=AsyncMock(return_value=_Result()))
    bundle = await v2s._load_validation_report(db, exp_id)
    assert bundle.edited_narrative is None
    assert bundle.edited_doc_version == 0


@pytest.mark.asyncio
async def test_generate_v2_passes_flattened_edited_doc_and_stamps(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When load returns edited_narrative, narrative prompt includes it; stamps set."""
    from app.services import landing_page_v2_service as v2s

    exp_id = uuid4()
    spark_id = uuid4()
    captured_prompts: list[str] = []
    narrative = _minimal_narrative()
    creative = _minimal_creative(narrative)
    visual = _minimal_visual(narrative)
    planner = _minimal_planner(narrative)

    experiment = SimpleNamespace(
        id=exp_id,
        refined_idea=_minimal_refined_idea().model_dump(mode="json"),
        refined_idea_version=3,
        name="Edit Gen V2",
    )
    v2_row = SimpleNamespace(
        spec_json=None,
        generation_status="idle",
        generation_phase="idle",
        error_detail=None,
        spark_version_id=None,
        refined_idea_version=None,
        edited_doc_version=None,
    )

    async def _fake_load(db, experiment_id):  # type: ignore[no-untyped-def]
        return ValidationReportForLanding(
            report=make_report(),
            edited_narrative="# Founder Voice\n\nPrefer this framing.",
            edited_doc_version=2,
        )

    async def _fake_run(db, **kwargs):  # type: ignore[no-untyped-def]
        if kwargs.get("prompt_name") == LP_RUNTIME_NARRATIVE_PROMPT_NAME:
            captured_prompts.append(kwargs["user"])
            return narrative
        rm = kwargs.get("response_model")
        if rm is CreativeDirectorOutput:
            return creative
        if rm is VisualComposerOutput:
            return visual
        if rm is ComponentPlannerOutput:
            return planner
        raise AssertionError(f"unexpected response_model {rm}")

    class _ExpResult:
        def scalar_one_or_none(self) -> object:
            return experiment

    class _LpResult:
        def scalar_one_or_none(self) -> object:
            return None

    execute_calls = {"n": 0}

    async def _fake_execute(stmt):  # type: ignore[no-untyped-def]
        execute_calls["n"] += 1
        if execute_calls["n"] == 1:
            return _ExpResult()
        return _LpResult()

    db = SimpleNamespace(
        execute=AsyncMock(side_effect=_fake_execute),
        commit=AsyncMock(),
        flush=AsyncMock(),
    )

    monkeypatch.setattr(v2s, "_load_validation_report", _fake_load)
    monkeypatch.setattr(v2s, "_set_generation_phase", AsyncMock())
    monkeypatch.setattr(v2s, "_run_structured", _fake_run)
    monkeypatch.setattr(v2s, "_get_or_create_v2_row", AsyncMock(return_value=v2_row))
    monkeypatch.setattr(v2s, "get_settings", lambda: SimpleNamespace())
    monkeypatch.setattr(
        v2s, "_landing_page_provider_and_model", lambda s: ("anthropic", "claude-test")
    )
    monkeypatch.setattr(
        "app.services.spark_version_service.get_latest_spark_version_id",
        AsyncMock(return_value=spark_id),
    )

    await v2s.generate_landing_page_v2_spec(db, experiment_id=exp_id)

    assert len(captured_prompts) == 1
    assert "Their edited narrative is below" in captured_prompts[0]
    assert "Founder Voice" in captured_prompts[0]
    assert v2_row.spark_version_id == spark_id
    assert v2_row.refined_idea_version == 3
    assert v2_row.edited_doc_version == 2
    assert v2_row.generation_status == "ready"


@pytest.mark.asyncio
async def test_generate_v2_omits_narrative_and_stamps_zero_without_edited_doc(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services import landing_page_v2_service as v2s

    exp_id = uuid4()
    spark_id = uuid4()
    captured_prompts: list[str] = []
    narrative = _minimal_narrative()
    creative = _minimal_creative(narrative)
    visual = _minimal_visual(narrative)
    planner = _minimal_planner(narrative)

    experiment = SimpleNamespace(
        id=exp_id,
        refined_idea=_minimal_refined_idea().model_dump(mode="json"),
        refined_idea_version=1,
        name="Raw Gen V2",
    )
    v2_row = SimpleNamespace(
        spec_json=None,
        generation_status="idle",
        generation_phase="idle",
        error_detail=None,
        spark_version_id=None,
        refined_idea_version=None,
        edited_doc_version=None,
    )

    async def _fake_load(db, experiment_id):  # type: ignore[no-untyped-def]
        return ValidationReportForLanding(
            report=make_report(),
            edited_narrative=None,
            edited_doc_version=0,
        )

    async def _fake_run(db, **kwargs):  # type: ignore[no-untyped-def]
        if kwargs.get("prompt_name") == LP_RUNTIME_NARRATIVE_PROMPT_NAME:
            captured_prompts.append(kwargs["user"])
            return narrative
        rm = kwargs.get("response_model")
        if rm is CreativeDirectorOutput:
            return creative
        if rm is VisualComposerOutput:
            return visual
        if rm is ComponentPlannerOutput:
            return planner
        raise AssertionError(f"unexpected response_model {rm}")

    class _ExpResult:
        def scalar_one_or_none(self) -> object:
            return experiment

    class _LpResult:
        def scalar_one_or_none(self) -> object:
            return None

    execute_calls = {"n": 0}

    async def _fake_execute(stmt):  # type: ignore[no-untyped-def]
        execute_calls["n"] += 1
        if execute_calls["n"] == 1:
            return _ExpResult()
        return _LpResult()

    db = SimpleNamespace(
        execute=AsyncMock(side_effect=_fake_execute),
        commit=AsyncMock(),
        flush=AsyncMock(),
    )

    monkeypatch.setattr(v2s, "_load_validation_report", _fake_load)
    monkeypatch.setattr(v2s, "_set_generation_phase", AsyncMock())
    monkeypatch.setattr(v2s, "_run_structured", _fake_run)
    monkeypatch.setattr(v2s, "_get_or_create_v2_row", AsyncMock(return_value=v2_row))
    monkeypatch.setattr(v2s, "get_settings", lambda: SimpleNamespace())
    monkeypatch.setattr(
        v2s, "_landing_page_provider_and_model", lambda s: ("anthropic", "claude-test")
    )
    monkeypatch.setattr(
        "app.services.spark_version_service.get_latest_spark_version_id",
        AsyncMock(return_value=spark_id),
    )

    await v2s.generate_landing_page_v2_spec(db, experiment_id=exp_id)

    assert len(captured_prompts) == 1
    assert "Their edited narrative is below" not in captured_prompts[0]
    assert "</founder_edited_narrative>" not in captured_prompts[0]
    assert v2_row.spark_version_id == spark_id
    assert v2_row.refined_idea_version == 1
    assert v2_row.edited_doc_version == 0
