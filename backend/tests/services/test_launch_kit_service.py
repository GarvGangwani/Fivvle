"""Tests for app.services.launch_kit_service.

Two layers:
- Pure unit tests for the deterministic helpers (pick_first_channel,
  derive_first_cohort_hint, default_readiness_checklist, _apply_patch) — no I/O.
- DB-integration tests for generate/get/patch using a real async session with
  the LLM call mocked (mirrors tests/services/test_evidence_chat_service.py).
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings
from app.db.enums import LandingCtaType, LandingDensity
from app.db.models.experiment import Experiment
from app.db.models.landing_page import LandingPage
from app.db.models.launch_kit import LaunchKit as LaunchKitRow
from app.db.models.user import User
from app.db.models.validation_report import ValidationReport
from app.schemas.launch_kit import (
    LaunchChannel,
    LaunchKit,
    LaunchKitLLMOutput,
    LaunchKitPatch,
    LaunchKitRegenLLMOutput,
    ReadinessItemPatch,
    ShareCopyVariant,
    ShareCopyVariantPatch,
    ShareSurface,
)
from app.schemas.refinement import RefinedIdea
from app.services.launch_kit_service import (
    LaunchKitNotFoundError,
    LaunchKitPreconditionError,
    LaunchKitVersionConflictError,
    _apply_patch,
    default_readiness_checklist,
    derive_first_cohort_hint,
    generate_launch_kit,
    get_launch_kit,
    patch_launch_kit,
    pick_first_channel,
    regenerate_variant,
)

_LLM_PATCH_TARGET = "app.services.launch_kit_service.llm_client.complete_structured"


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


def _refined_idea(
    *,
    target_audience: str = "Operations managers at 200-person SaaS companies.",
    one_liner: str = "A Slack bot that answers HR policy questions instantly.",
    value_prop: str = "Cuts repetitive policy questions so ops managers focus on real work.",
) -> RefinedIdea:
    return RefinedIdea.model_validate(
        {
            "refined_one_liner": one_liner,
            "target_audience": target_audience,
            "value_proposition": value_prop,
            "risks": [
                "Do existing Slack HR bots already own this workflow?",
                "Is the policy content fresh enough to trust without review?",
                "Can pricing support a venture-scale business at SMB seat counts?",
            ],
            "headline": "Stop answering the same policy questions every week.",
            "subheadline": "An AI trained on your handbook handles every policy question.",
            "cta_text": "Join the waitlist",
        }
    )


def _validation_report(
    *, distribution_signals: str | None = "Slack App Directory listing is the primary channel."
) -> Any:
    from app.schemas.validation_report import (  # noqa: PLC0415
        Citation,
        Finding,
        QuestionFindings,
    )
    from app.schemas.validation_report import (
        ValidationReport as ValidationReportSchema,
    )

    now = datetime(2026, 7, 17, 12, 0, 0, tzinfo=UTC)

    def _finding(qid: str) -> Finding:
        return Finding(
            question_id=qid,
            claim=f"Buyers actively engage with the {qid} dimension of this idea.",
            evidence_summary=f"Evidence summary paraphrasing sources for {qid}.",
            citations=[
                Citation(
                    url=f"https://reddit.com/{qid}",
                    title="t",
                    source_domain="reddit.com",
                    accessed_at=now,
                )
            ],
            confidence="medium",
            confidence_rationale="One corroborating source.",
        )

    return ValidationReportSchema(
        executive_summary=(
            "Executive summary long enough to satisfy the fifty character minimum "
            "constraint for this field."
        ),
        questions_and_findings=[
            QuestionFindings(
                question_id=qid,
                question=f"Question text for {qid}?",
                findings=[_finding(qid)],
                evidence_gap=None,
            )
            for qid in ("q1", "q2", "q3", "q4", "q5")
        ],
        competitors=[],
        market_signals="Active buyer demand; no reliable TAM figure in results.",
        distribution_signals=distribution_signals,
        regulatory_signals=None,
        risks_assessment="Competitor risk partially confirmed; staleness risk open.",
        overall_recommendation="iterate",
        recommendation_rationale=(
            "q1 confirms demand; iterate on the always-current handbook wedge."
        ),
        research_limitations="Market size data was not found in the search results.",
        voices=None,
        rubric_version_used="v1",
        section_scores=[],
        overall_score=None,
    )


def _llm_output(
    *,
    rationale: str = "Ops managers gather on LinkedIn — start the first ten there.",
    surfaces: tuple[ShareSurface, ...] = (
        ShareSurface.LINKEDIN_POST,
        ShareSurface.DM_OPENER,
        ShareSurface.TWEET,
    ),
) -> LaunchKitLLMOutput:
    return LaunchKitLLMOutput(
        first_channel_rationale=rationale,
        share_copy_variants=[
            ShareCopyVariant(surface=s, text=f"Ready-to-post copy for {s.value}.")
            for s in surfaces
        ],
    )


def _llm_result() -> SimpleNamespace:
    return SimpleNamespace(cost_usd=Decimal("0.01"), latency_ms=120)


# ---------------------------------------------------------------------------
# Pure unit tests — deterministic helpers
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("audience", "distribution", "expected"),
    [
        ("Backend developers building APIs and CLI tools.", None, LaunchChannel.HACKERNEWS),
        ("B2B sales teams at mid-market SaaS companies.", None, LaunchChannel.LINKEDIN),
        (
            "Hobbyist board game enthusiasts in niche communities.",
            None,
            LaunchChannel.REDDIT,
        ),
        (
            "Indie makers launching consumer apps.",
            "Product Hunt is the main launch channel here.",
            LaunchChannel.PRODUCT_HUNT,
        ),
        ("People who love cooking at home on weekends.", None, LaunchChannel.TWITTER),
    ],
)
def test_pick_first_channel(
    audience: str, distribution: str | None, expected: LaunchChannel
) -> None:
    ri = _refined_idea(target_audience=audience, one_liner="An app.", value_prop="It helps.")
    vr = _validation_report(distribution_signals=distribution)
    assert pick_first_channel(ri, vr) == expected


def test_derive_first_cohort_hint_mentions_audience_and_is_bounded() -> None:
    ri = _refined_idea(target_audience="nurses on understaffed night shifts")
    hint = derive_first_cohort_hint(ri)
    assert "nurses on understaffed night shifts" in hint
    assert 1 <= len(hint) <= 500


def test_derive_first_cohort_hint_truncates_long_audience() -> None:
    ri = _refined_idea(target_audience="x" * 300)
    hint = derive_first_cohort_hint(ri)
    assert len(hint) <= 500


def test_default_readiness_checklist_shape() -> None:
    items = default_readiness_checklist()
    assert len(items) == 5
    assert [i.id for i in items] == [
        "landing_live",
        "waitlist_works",
        "share_copy_ready",
        "first_cohort_listed",
        "tracking_on",
    ]
    assert all(i.checked_at is None for i in items)


def _launch_kit(landing_page_id: Any) -> LaunchKit:
    return LaunchKit(
        schema_version=1,
        landing_page_id=landing_page_id,
        first_channel=LaunchChannel.LINKEDIN,
        first_channel_rationale="Because that is where the audience is.",
        first_cohort_hint="Start with 10 ops managers you know.",
        share_copy_variants=[
            ShareCopyVariant(surface=ShareSurface.TWEET, text="Tweet copy."),
            ShareCopyVariant(surface=ShareSurface.DM_OPENER, text="DM copy."),
            ShareCopyVariant(surface=ShareSurface.LINKEDIN_POST, text="LinkedIn copy."),
        ],
        readiness_checklist=default_readiness_checklist(),
        generated_at=datetime.now(UTC),
        founder_edited=False,
        raw_report={"first_channel_rationale": "x", "share_copy_variants": []},
    )


def test_apply_patch_updates_scalar_fields() -> None:
    current = _launch_kit(uuid4())
    patched = _apply_patch(
        current,
        LaunchKitPatch(
            first_channel=LaunchChannel.REDDIT,
            first_channel_rationale="New rationale.",
            first_cohort_hint="New hint.",
        ),
    )
    assert patched.first_channel == LaunchChannel.REDDIT
    assert patched.first_channel_rationale == "New rationale."
    assert patched.first_cohort_hint == "New hint."
    # Original is untouched (copy semantics).
    assert current.first_channel == LaunchChannel.LINKEDIN


def test_apply_patch_updates_variant_text_by_index() -> None:
    current = _launch_kit(uuid4())
    patched = _apply_patch(
        current,
        LaunchKitPatch(
            share_copy_variants=[ShareCopyVariantPatch(index=1, text="Edited DM copy.")]
        ),
    )
    assert patched.share_copy_variants[1].text == "Edited DM copy."
    assert patched.share_copy_variants[0].text == "Tweet copy."


def test_apply_patch_out_of_range_index_raises_valueerror() -> None:
    current = _launch_kit(uuid4())
    with pytest.raises(ValueError):
        _apply_patch(
            current,
            LaunchKitPatch(
                share_copy_variants=[ShareCopyVariantPatch(index=9, text="nope")]
            ),
        )


def test_apply_patch_checks_readiness_item_by_id() -> None:
    current = _launch_kit(uuid4())
    ts = datetime.now(UTC)
    patched = _apply_patch(
        current,
        LaunchKitPatch(
            readiness_checklist=[ReadinessItemPatch(id="landing_live", checked_at=ts)]
        ),
    )
    checked = {i.id: i.checked_at for i in patched.readiness_checklist}
    assert checked["landing_live"] == ts
    assert checked["waitlist_works"] is None


def test_apply_patch_unknown_readiness_id_raises_valueerror() -> None:
    current = _launch_kit(uuid4())
    with pytest.raises(ValueError):
        _apply_patch(
            current,
            LaunchKitPatch(
                readiness_checklist=[ReadinessItemPatch(id="does_not_exist", checked_at=None)]
            ),
        )


# ---------------------------------------------------------------------------
# DB-integration tests
# ---------------------------------------------------------------------------


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine(get_settings().database_url, pool_size=1, max_overflow=0)
    sm = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
    try:
        async with sm() as session:
            yield session
    finally:
        await engine.dispose()


async def _persist_user(db: AsyncSession) -> User:
    user = User(
        firebase_uid=f"lk-svc-{uuid4()}",
        email=f"lk-{uuid4()}@example.com",
        name="Launch Kit Test User",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def _persist_experiment(
    db: AsyncSession,
    user: User,
    *,
    with_report: bool = True,
    with_landing: bool = True,
    target_geography: str | None = "United States",
) -> Experiment:
    experiment = Experiment(
        user_id=user.id,
        raw_idea="A Slack app that answers HR policy questions.",
        name="PolicyPal",
        refined_idea=_refined_idea().model_dump(mode="json"),
        target_geography=target_geography,
    )
    db.add(experiment)
    await db.flush()
    if with_report:
        db.add(
            ValidationReport(
                experiment_id=experiment.id,
                raw_report=_validation_report().model_dump(mode="json"),
            )
        )
    if with_landing:
        db.add(
            LandingPage(
                experiment_id=experiment.id,
                template_id="minimal",
                palette_id="default",
                font_pair_id="sans",
                density=LandingDensity.ROOMY,
                headline="Launch kit test headline",
                problem_desc="Problem description for launch kit tests.",
                solution_desc="Solution description for launch kit tests.",
                cta_text="Join the waitlist",
                cta_type=LandingCtaType.WAITLIST,
                slug=f"lk-{uuid4().hex[:12]}",
            )
        )
    await db.commit()
    await db.refresh(experiment)
    return experiment


@pytest.mark.asyncio
@pytest.mark.usefixtures("mock_firebase")
async def test_generate_launch_kit_happy_path(db_session: AsyncSession) -> None:
    from unittest.mock import AsyncMock, patch  # noqa: PLC0415

    user = await _persist_user(db_session)
    experiment = await _persist_experiment(db_session, user)

    with patch(_LLM_PATCH_TARGET, new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = (_llm_output(), _llm_result())
        kit = await generate_launch_kit(db_session, experiment.id)
        await db_session.commit()

    assert kit.schema_version == 1
    assert kit.first_channel == LaunchChannel.LINKEDIN
    assert len(kit.share_copy_variants) == 3
    assert len(kit.readiness_checklist) == 5
    assert kit.founder_edited is False

    # LLM call used the launch-kit prompt name + phase.
    kwargs = mock_llm.call_args.kwargs
    assert kwargs["prompt_name"] == "launch_kit_v1"
    assert kwargs["phase"] == "launch_kit"

    row = (
        await db_session.execute(
            select(LaunchKitRow).where(LaunchKitRow.experiment_id == experiment.id)
        )
    ).scalar_one()
    assert row.version == 1
    assert row.edited_doc is None
    assert row.raw_report["first_channel"] == "linkedin"


@pytest.mark.asyncio
@pytest.mark.usefixtures("mock_firebase")
async def test_generate_launch_kit_missing_landing_page_raises(
    db_session: AsyncSession,
) -> None:
    from unittest.mock import AsyncMock, patch  # noqa: PLC0415

    user = await _persist_user(db_session)
    experiment = await _persist_experiment(db_session, user, with_landing=False)

    with patch(_LLM_PATCH_TARGET, new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = (_llm_output(), _llm_result())
        with pytest.raises(LaunchKitPreconditionError):
            await generate_launch_kit(db_session, experiment.id)
    # LLM must not be called when a precondition fails.
    assert mock_llm.await_count == 0


@pytest.mark.asyncio
@pytest.mark.usefixtures("mock_firebase")
async def test_regeneration_bumps_version_and_clears_edits(
    db_session: AsyncSession,
) -> None:
    from unittest.mock import AsyncMock, patch  # noqa: PLC0415

    user = await _persist_user(db_session)
    experiment = await _persist_experiment(db_session, user)

    with patch(_LLM_PATCH_TARGET, new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = (_llm_output(), _llm_result())
        await generate_launch_kit(db_session, experiment.id)
        await db_session.commit()

        # Founder edits → version 2, edited_doc set.
        await patch_launch_kit(
            db_session,
            experiment.id,
            expected_version=1,
            patch=LaunchKitPatch(first_channel_rationale="Founder edit."),
        )
        await db_session.commit()

        # Regenerate → version bumps again, edited_doc cleared.
        await generate_launch_kit(db_session, experiment.id)
        await db_session.commit()

    row = (
        await db_session.execute(
            select(LaunchKitRow).where(LaunchKitRow.experiment_id == experiment.id)
        )
    ).scalar_one()
    assert row.version == 3
    assert row.edited_doc is None


@pytest.mark.asyncio
@pytest.mark.usefixtures("mock_firebase")
async def test_get_launch_kit_none_then_envelope(db_session: AsyncSession) -> None:
    from unittest.mock import AsyncMock, patch  # noqa: PLC0415

    user = await _persist_user(db_session)
    experiment = await _persist_experiment(db_session, user)

    assert await get_launch_kit(db_session, experiment.id) is None

    with patch(_LLM_PATCH_TARGET, new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = (_llm_output(), _llm_result())
        await generate_launch_kit(db_session, experiment.id)
        await db_session.commit()

    envelope = await get_launch_kit(db_session, experiment.id)
    assert envelope is not None
    assert envelope.version == 1
    assert envelope.launch_kit.first_channel == LaunchChannel.LINKEDIN


@pytest.mark.asyncio
@pytest.mark.usefixtures("mock_firebase")
async def test_patch_launch_kit_applies_and_bumps_version(
    db_session: AsyncSession,
) -> None:
    from unittest.mock import AsyncMock, patch  # noqa: PLC0415

    user = await _persist_user(db_session)
    experiment = await _persist_experiment(db_session, user)

    with patch(_LLM_PATCH_TARGET, new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = (_llm_output(), _llm_result())
        await generate_launch_kit(db_session, experiment.id)
        await db_session.commit()

    envelope = await patch_launch_kit(
        db_session,
        experiment.id,
        expected_version=1,
        patch=LaunchKitPatch(first_cohort_hint="Reach 10 ops leads you already know."),
    )
    await db_session.commit()

    assert envelope.version == 2
    assert envelope.launch_kit.founder_edited is True
    assert envelope.launch_kit.first_cohort_hint == "Reach 10 ops leads you already know."

    row = (
        await db_session.execute(
            select(LaunchKitRow).where(LaunchKitRow.experiment_id == experiment.id)
        )
    ).scalar_one()
    assert row.edited_at is not None
    assert row.edited_doc is not None


@pytest.mark.asyncio
@pytest.mark.usefixtures("mock_firebase")
async def test_patch_launch_kit_version_conflict(db_session: AsyncSession) -> None:
    from unittest.mock import AsyncMock, patch  # noqa: PLC0415

    user = await _persist_user(db_session)
    experiment = await _persist_experiment(db_session, user)

    with patch(_LLM_PATCH_TARGET, new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = (_llm_output(), _llm_result())
        await generate_launch_kit(db_session, experiment.id)
        await db_session.commit()

    with pytest.raises(LaunchKitVersionConflictError):
        await patch_launch_kit(
            db_session,
            experiment.id,
            expected_version=99,
            patch=LaunchKitPatch(first_cohort_hint="stale write"),
        )


@pytest.mark.asyncio
@pytest.mark.usefixtures("mock_firebase")
async def test_regenerate_variant_happy_path(db_session: AsyncSession) -> None:
    from unittest.mock import AsyncMock, patch  # noqa: PLC0415

    user = await _persist_user(db_session)
    experiment = await _persist_experiment(db_session, user)

    with patch(_LLM_PATCH_TARGET, new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = (_llm_output(), _llm_result())
        await generate_launch_kit(db_session, experiment.id)
        await db_session.commit()

        mock_llm.return_value = (
            LaunchKitRegenLLMOutput(text="Fresh LinkedIn rewrite."),
            _llm_result(),
        )
        envelope = await regenerate_variant(
            db_session, experiment.id, surface=ShareSurface.LINKEDIN_POST
        )
        await db_session.commit()

    assert envelope.version == 2
    assert envelope.launch_kit.founder_edited is True
    variants = envelope.launch_kit.share_copy_variants
    linkedin = next(v for v in variants if v.surface == ShareSurface.LINKEDIN_POST)
    tweet = next(v for v in variants if v.surface == ShareSurface.TWEET)
    assert linkedin.text == "Fresh LinkedIn rewrite."
    assert linkedin.regenerated_count == 1
    assert tweet.text == "Ready-to-post copy for tweet."
    assert tweet.regenerated_count == 0

    row = (
        await db_session.execute(
            select(LaunchKitRow).where(LaunchKitRow.experiment_id == experiment.id)
        )
    ).scalar_one()
    assert row.edited_doc is not None
    assert row.raw_report["share_copy_variants"][0]["text"].startswith(
        "Ready-to-post copy"
    )
    assert mock_llm.call_args.kwargs["prompt_name"] == "launch_kit_regen_v1"


@pytest.mark.asyncio
@pytest.mark.usefixtures("mock_firebase")
async def test_regenerate_variant_preserves_raw_report_column(
    db_session: AsyncSession,
) -> None:
    from unittest.mock import AsyncMock, patch  # noqa: PLC0415

    user = await _persist_user(db_session)
    experiment = await _persist_experiment(db_session, user)

    with patch(_LLM_PATCH_TARGET, new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = (_llm_output(), _llm_result())
        await generate_launch_kit(db_session, experiment.id)
        await db_session.commit()

        row_before = (
            await db_session.execute(
                select(LaunchKitRow).where(LaunchKitRow.experiment_id == experiment.id)
            )
        ).scalar_one()
        raw_before = dict(row_before.raw_report)

        mock_llm.return_value = (
            LaunchKitRegenLLMOutput(text="Another rewrite."),
            _llm_result(),
        )
        await regenerate_variant(
            db_session, experiment.id, surface=ShareSurface.TWEET
        )
        await db_session.commit()

    row_after = (
        await db_session.execute(
            select(LaunchKitRow).where(LaunchKitRow.experiment_id == experiment.id)
        )
    ).scalar_one()
    assert row_after.raw_report == raw_before


@pytest.mark.asyncio
@pytest.mark.usefixtures("mock_firebase")
async def test_regenerate_variant_missing_kit_raises(
    db_session: AsyncSession,
) -> None:
    user = await _persist_user(db_session)
    experiment = await _persist_experiment(db_session, user)

    with pytest.raises(LaunchKitNotFoundError):
        await regenerate_variant(
            db_session, experiment.id, surface=ShareSurface.TWEET
        )


@pytest.mark.asyncio
@pytest.mark.usefixtures("mock_firebase")
async def test_regenerate_variant_unknown_surface_raises(
    db_session: AsyncSession,
) -> None:
    from unittest.mock import AsyncMock, patch  # noqa: PLC0415

    user = await _persist_user(db_session)
    experiment = await _persist_experiment(db_session, user)

    with patch(_LLM_PATCH_TARGET, new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = (_llm_output(), _llm_result())
        await generate_launch_kit(db_session, experiment.id)
        await db_session.commit()

        with pytest.raises(ValueError, match="reddit_post"):
            await regenerate_variant(
                db_session, experiment.id, surface=ShareSurface.REDDIT_POST
            )
    assert mock_llm.await_count == 1  # generate only; regen never called LLM
