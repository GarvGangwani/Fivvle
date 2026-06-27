"""Tests for experiment display name helpers."""

from app.db.models.experiment import Experiment
from app.schemas.refinement import RefinedIdea
from app.utils.experiment_naming import (
    apply_llm_name_if_unset,
    resolve_name_from_refined,
    resolve_slug_base_from_experiment,
    slugify_for_url,
    sync_landing_page_project_name,
)
from uuid import uuid4


def _refined(**overrides: object) -> RefinedIdea:
    defaults = {
        "refined_one_liner": "A tool that cuts nurse shift-handoff time from 40 min to 5.",
        "target_audience": "Night-shift nurses at regional hospitals.",
        "value_proposition": "Reduces handoff documentation time by 87%.",
        "risks": ["Risk one?", "Risk two?", "Risk three?"],
        "headline": "Cut shift-handoff time from 40 minutes to 5.",
        "subheadline": "AI handles every handoff note automatically.",
        "cta_text": "Join the waitlist",
    }
    defaults.update(overrides)
    return RefinedIdea(**defaults)  # type: ignore[arg-type]


def test_resolve_name_prefers_project_name() -> None:
    refined = _refined(project_name="Shift Handoff AI")
    assert resolve_name_from_refined(refined) == "Shift Handoff AI"


def test_resolve_name_falls_back_to_one_liner() -> None:
    refined = _refined(refined_one_liner="Async standup tool for remote teams")
    assert resolve_name_from_refined(refined) == "Async standup tool for remote teams"


def test_apply_llm_name_if_unset_skips_existing_user_name() -> None:
    experiment = Experiment(
        user_id=uuid4(),
        raw_idea="idea",
        name="My Custom Name",
    )
    apply_llm_name_if_unset(experiment, _refined(project_name="LLM Name"))
    assert experiment.name == "My Custom Name"


def test_apply_llm_name_if_unset_sets_from_refined() -> None:
    experiment = Experiment(user_id=uuid4(), raw_idea="idea", name=None)
    apply_llm_name_if_unset(experiment, _refined(project_name="LLM Name"))
    assert experiment.name == "LLM Name"


def test_sync_landing_page_project_name() -> None:
    updated = sync_landing_page_project_name({"template_id": "minimal"}, "Acme")
    assert updated["publish"]["project_name"] == "Acme"


def test_slugify_for_url_shortens_long_names() -> None:
    slug = slugify_for_url("My Very Long Startup Name That Should Be Trimmed")
    assert len(slug) <= 28
    assert slug == "my-very-long-startup-name-th"


def test_resolve_slug_base_prefers_experiment_name() -> None:
    experiment = Experiment(
        user_id=uuid4(),
        raw_idea="A long raw idea sentence that should never become the slug",
        name="Shift Handoff AI",
        refined_idea=_refined(
            project_name="Other Name",
            headline="Cut shift-handoff time from 40 minutes to 5.",
        ).model_dump(),
    )
    assert resolve_slug_base_from_experiment(experiment) == "shift-handoff-ai"


def test_resolve_slug_base_uses_project_name_when_no_user_name() -> None:
    experiment = Experiment(
        user_id=uuid4(),
        raw_idea="idea",
        name=None,
        refined_idea=_refined(project_name="Nurse Handoff Bot").model_dump(),
    )
    assert resolve_slug_base_from_experiment(experiment) == "nurse-handoff-bot"
