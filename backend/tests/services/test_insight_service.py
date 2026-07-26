"""Unit tests for app.services.insight_service.

Uses a live async DB session for ValidationReport / analytics fixtures.
LLM calls are mocked via AsyncMock on llm_client.complete_structured.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
import structlog.testing
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings
from app.db.enums import ExperimentStatus, InsightRecommendation, LandingCtaType, LandingDensity
from app.db.models.experiment import Experiment
from app.db.models.insight_report import InsightReport
from app.db.models.landing_page import LandingPage
from app.db.models.page_view import PageView
from app.db.models.user import User
from app.db.models.validation_report import ValidationReport as ValidationReportRow
from app.db.models.waitlist_signup import WaitlistSignup
from app.llm.prompts.insight import PROMPT_NAME, _compute_finding_ids
from app.schemas.insight import (
    ConversionBySourceDraft,
    ConversionSourceCommentaryDraft,
    InsightReportOutputDraft,
    ResearchTakeawayDraft,
    TrafficSummaryDraft,
)
from app.schemas.validation_report import Citation, Finding, QuestionFindings, ValidationReport
from app.services.analytics_aggregator import LandingPageNotLiveError
from app.services.insight_service import (
    INSIGHT_CACHE_BREAKPOINTS,
    InsightCitationHallucinatedError,
    MissingValidationReportError,
    _fetch_validation_report,
    generate_insight_report,
)

_NOW = datetime.now(timezone.utc)


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine(get_settings().database_url, pool_size=1, max_overflow=0)
    sm = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
    try:
        async with sm() as session:
            yield session
    finally:
        await engine.dispose()


def _make_mock_llm_meta() -> MagicMock:
    meta = MagicMock()
    meta.prompt_tokens = 3000
    meta.completion_tokens = 1500
    meta.cost_usd = Decimal("0.020000")
    meta.latency_ms = 8000
    return meta


def _make_finding(question_id: str, claim: str) -> Finding:
    return Finding(
        question_id=question_id,
        claim=claim,
        evidence_summary="Evidence summary citing one source for the claim.",
        citations=[
            Citation(
                url="https://example.com/article",
                title="Example Article",
                source_domain="example.com",
                accessed_at=_NOW,
            )
        ],
        confidence="medium",
        confidence_rationale="Single source; directional only.",
    )


def _make_validation_report_pydantic() -> ValidationReport:
    """5 questions; q1 and q2 each have 2 findings for directory ID tests."""
    return ValidationReport(
        executive_summary=(
            "Research confirms moderate demand for the proposed Slack HR bot. "
            "Competitors exist but differentiation is possible via handbook freshness. "
            "Behavioral validation is still needed before a proceed verdict."
        ),
        questions_and_findings=[
            QuestionFindings(
                question_id="q1",
                question="Research question 1 about market viability?",
                findings=[
                    _make_finding("q1", "First finding claim for question q1."),
                    _make_finding("q1", "Second finding claim for question q1."),
                ],
            ),
            QuestionFindings(
                question_id="q2",
                question="Research question 2 about competition?",
                findings=[
                    _make_finding("q2", "First finding claim for question q2."),
                    _make_finding("q2", "Second finding claim for question q2."),
                ],
            ),
            *[
                QuestionFindings(
                    question_id=f"q{i}",
                    question=f"Research question {i} about market viability?",
                    findings=[_make_finding(f"q{i}", f"Finding claim for question q{i}.")],
                )
                for i in range(3, 6)
            ],
        ],
        competitors=[],
        market_signals="No reliable TAM data found in search results.",
        distribution_signals=None,
        regulatory_signals=None,
        risks_assessment=(
            "Competitor risk is confirmed by q2 findings. Handbook staleness risk "
            "is partially confirmed. Procurement complexity remains unaddressed."
        ),
        overall_recommendation="iterate",
        recommendation_rationale=(
            "q2 confirms overlap with existing tools. Iterate on differentiation "
            "before scaling distribution."
        ),
        research_limitations="Market size data was not found.",
        rubric_version_used="v1",
    )


def _valid_finding_ids(vr: ValidationReport) -> set[str]:
    return {fid for fid, _ in _compute_finding_ids(vr)}


def _build_valid_draft(valid_ids: set[str]) -> InsightReportOutputDraft:
    cited = sorted(valid_ids)[:3]
    return InsightReportOutputDraft(
        traffic_summary=TrafficSummaryDraft(
            narrative=(
                "Traffic over three days shows modest cold-traffic interest with "
                "47 total page views and a single Twitter spike on day two."
            ),
            headline_metric="47 page views in 3 days",
            confidence="medium",
            confidence_rationale="Sample size is small but directional signal exists.",
            source_type="BEHAVIORAL",
        ),
        conversion_by_source=ConversionBySourceDraft(
            per_source=[
                ConversionSourceCommentaryDraft(
                    source_name="twitter",
                    views=30,
                    signups=4,
                    conversion_rate=0.133,
                    commentary=(
                        "Twitter drove most signups but likely reflects warm-network "
                        "bias from the founder's post rather than cold demand."
                    ),
                    confidence="medium",
                ),
            ],
            warm_network_bias_commentary=(
                "Warm-network bias index is elevated — interpret conversion cautiously."
            ),
            confidence="medium",
            confidence_rationale="Single dominant source limits generalization.",
        ),
        research_takeaways=[
            ResearchTakeawayDraft(
                claim=(
                    f"Cognitive evidence from {cited[0]} supports iterating on "
                    "differentiation before scaling cold distribution channels."
                ),
                cited_finding_ids=[cited[0]],
                source_type="COGNITIVE",
                confidence="medium",
                confidence_rationale="Backed by validation findings with citations.",
            ),
            ResearchTakeawayDraft(
                claim=(
                    f"Behavioral conversion at 8.5% on small N aligns with {cited[1]} "
                    "suggesting the value proposition may land without social proof."
                ),
                cited_finding_ids=[cited[1]],
                source_type="SYNTHESIZED",
                confidence="low",
                confidence_rationale="Tiny sample; directional only.",
            ),
            ResearchTakeawayDraft(
                claim=(
                    f"Risk from {cited[2]} remains unaddressed by behavioral data — "
                    "iterate landing copy before a proceed verdict."
                ),
                cited_finding_ids=[cited[2]],
                source_type="COGNITIVE",
                confidence="medium",
                confidence_rationale="Finding directly flags the primary objection.",
            ),
        ],
        recommendation_type=InsightRecommendation.ITERATE,
        recommendation=(
            "ITERATE. Behavioral signals are encouraging but premature: 8.5% conversion "
            "on 47 page views (4 signups) outperforms category benchmarks in finding "
            f"{cited[1]}. However, warm-network bias is high and finding {cited[2]} "
            "flags integration complexity. Iterate landing copy, then re-distribute to "
            "cold sources to re-measure conversion before proceeding."
        ),
        recommendation_confidence="medium",
        recommendation_rationale=(
            "Behavioral N is too small for proceed; cognitive findings support iterate."
        ),
        what_would_change_this=(
            "If cold-traffic signups exceed 5% over 200+ views in 14 days, shift to PROCEED."
        ),
    )


def _build_invalid_draft(invalid_id: str) -> InsightReportOutputDraft:
    draft = _build_valid_draft({"q1.f0", "q1.f1", "q2.f0"})
    draft.research_takeaways[0].cited_finding_ids = [invalid_id]
    return draft


async def _persist_user_and_experiment(
    db: AsyncSession,
    *,
    status: ExperimentStatus = ExperimentStatus.LANDING_LIVE,
) -> Experiment:
    user = User(
        firebase_uid=f"insight-svc-{uuid4()}",
        email=f"insight-svc-{uuid4()}@example.com",
        name="Insight Service Test User",
    )
    db.add(user)
    await db.flush()
    experiment = Experiment(
        user_id=user.id,
        raw_idea="A slack bot that answers HR policy questions so ops managers don't have to.",
        status=status,
    )
    db.add(experiment)
    await db.commit()
    await db.refresh(experiment)
    return experiment


async def _persist_validation_report(
    db: AsyncSession,
    experiment_id: object,
    *,
    raw_report: dict | None = None,
) -> ValidationReportRow:
    vr = _make_validation_report_pydantic()
    row = ValidationReportRow(
        experiment_id=experiment_id,
        raw_report=raw_report if raw_report is not None else vr.model_dump(mode="json"),
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


async def _persist_landing_page_with_telemetry(
    db: AsyncSession,
    experiment_id: object,
    *,
    days_live: int = 3,
) -> None:
    live_at = _NOW - timedelta(days=days_live)
    landing_page = LandingPage(
        experiment_id=experiment_id,
        template_id="minimal",
        palette_id="default",
        font_pair_id="sans",
        density=LandingDensity.ROOMY,
        headline="Test headline for insight service fixture",
        problem_desc="Problem description for the test landing page fixture.",
        solution_desc="Solution description for the test landing page fixture.",
        cta_text="Join the waitlist",
        cta_type=LandingCtaType.WAITLIST,
        slug=f"insight-svc-{uuid4().hex[:12]}",
        live_at=live_at,
    )
    db.add(landing_page)
    await db.flush()

    live_date = live_at.astimezone(timezone.utc).date()
    for day_idx in range(days_live):
        day_ts = datetime.combine(
            live_date + timedelta(days=day_idx),
            datetime.min.time(),
            tzinfo=timezone.utc,
        ) + timedelta(hours=12)
        for _ in range(5):
            db.add(
                PageView(
                    experiment_id=experiment_id,
                    source_tag="twitter" if day_idx % 2 == 0 else "google",
                    ts=day_ts,
                    ip_address=f"10.0.0.{day_idx + 1}",
                    time_on_page_sec=45,
                )
            )
        if day_idx == 1:
            db.add(
                WaitlistSignup(
                    experiment_id=experiment_id,
                    email=f"signup-{uuid4()}@example.com",
                    source_tag="twitter",
                    ts=day_ts,
                )
            )
    await db.commit()


async def _insight_report_count(db: AsyncSession, experiment_id: object) -> int:
    result = await db.execute(
        select(func.count())
        .select_from(InsightReport)
        .where(InsightReport.experiment_id == experiment_id)
    )
    return int(result.scalar_one())


# ---------------------------------------------------------------------------
# 1. Happy path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_happy_path_persists_insight_report(db_session: AsyncSession) -> None:
    experiment = await _persist_user_and_experiment(db_session)
    experiment.refined_idea_version = 5
    await db_session.commit()
    await db_session.refresh(experiment)
    vr = _make_validation_report_pydantic()
    valid_ids = _valid_finding_ids(vr)
    draft = _build_valid_draft(valid_ids)
    await _persist_validation_report(db_session, experiment.id)
    await _persist_landing_page_with_telemetry(db_session, experiment.id)

    status_before = experiment.status
    mock_complete = AsyncMock(return_value=(draft, _make_mock_llm_meta()))

    with patch(
        "app.services.insight_service.llm_client.complete_structured",
        mock_complete,
    ):
        row = await generate_insight_report(db_session, experiment.id)

    await db_session.refresh(experiment)
    assert experiment.status == status_before
    assert mock_complete.call_count == 1

    assert row.recommendation_type == draft.recommendation_type
    assert row.raw_output is not None
    assert row.raw_output["what_would_change_this"] == draft.what_would_change_this
    assert row.research_takeaways == {
        "items": [tk.model_dump(mode="json") for tk in draft.research_takeaways]
    }
    assert row.refined_idea_version == experiment.refined_idea_version


# ---------------------------------------------------------------------------
# 2. Citation hallucination then valid retry
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_citation_hallucination_retries_then_succeeds(db_session: AsyncSession) -> None:
    experiment = await _persist_user_and_experiment(db_session)
    vr = _make_validation_report_pydantic()
    valid_ids = _valid_finding_ids(vr)
    valid_draft = _build_valid_draft(valid_ids)
    invalid_draft = _build_invalid_draft("q99.f0")
    await _persist_validation_report(db_session, experiment.id)
    await _persist_landing_page_with_telemetry(db_session, experiment.id)

    mock_complete = AsyncMock(
        side_effect=[
            (invalid_draft, _make_mock_llm_meta()),
            (valid_draft, _make_mock_llm_meta()),
        ]
    )

    with patch(
        "app.services.insight_service.llm_client.complete_structured",
        mock_complete,
    ), structlog.testing.capture_logs() as cap:
        row = await generate_insight_report(db_session, experiment.id)

    assert mock_complete.call_count == 2
    second_user = mock_complete.call_args_list[1].kwargs["user"]
    assert "<previous_attempt_feedback>" in second_user
    assert row.recommendation_type == valid_draft.recommendation_type

    warning_events = [
        e for e in cap if e.get("event") == "insight citation hallucination — retrying with feedback"
    ]
    assert len(warning_events) == 1


# ---------------------------------------------------------------------------
# 3. Citation hallucination both attempts
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_citation_hallucination_both_attempts_raises(db_session: AsyncSession) -> None:
    experiment = await _persist_user_and_experiment(db_session)
    vr = _make_validation_report_pydantic()
    valid_ids = _valid_finding_ids(vr)
    invalid_draft = _build_invalid_draft("q99.f0")
    await _persist_validation_report(db_session, experiment.id)
    await _persist_landing_page_with_telemetry(db_session, experiment.id)

    count_before = await _insight_report_count(db_session, experiment.id)
    mock_complete = AsyncMock(
        side_effect=[
            (invalid_draft, _make_mock_llm_meta()),
            (invalid_draft, _make_mock_llm_meta()),
        ]
    )

    with patch(
        "app.services.insight_service.llm_client.complete_structured",
        mock_complete,
    ):
        with pytest.raises(InsightCitationHallucinatedError) as exc_info:
            await generate_insight_report(db_session, experiment.id)

    assert mock_complete.call_count == 2
    assert "q99.f0" in exc_info.value.invalid_ids
    assert exc_info.value.valid_ids == valid_ids
    count_after = await _insight_report_count(db_session, experiment.id)
    assert count_after == count_before


# ---------------------------------------------------------------------------
# 4. Missing ValidationReport
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_missing_validation_report_raises(db_session: AsyncSession) -> None:
    experiment = await _persist_user_and_experiment(db_session)
    await _persist_landing_page_with_telemetry(db_session, experiment.id)

    with patch(
        "app.services.insight_service.llm_client.complete_structured",
        AsyncMock(),
    ):
        with pytest.raises(MissingValidationReportError):
            await generate_insight_report(db_session, experiment.id)


# ---------------------------------------------------------------------------
# 5. NULL raw_report
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_null_raw_report_raises() -> None:
    db = AsyncMock(spec=AsyncSession)
    mock_row = MagicMock()
    mock_row.raw_report = None
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_row
    db.execute = AsyncMock(return_value=mock_result)

    with pytest.raises(MissingValidationReportError):
        await _fetch_validation_report(db, uuid4())


# ---------------------------------------------------------------------------
# 6. Settings drive provider + model
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_settings_drive_provider_and_model(db_session: AsyncSession) -> None:
    experiment = await _persist_user_and_experiment(db_session)
    vr = _make_validation_report_pydantic()
    draft = _build_valid_draft(_valid_finding_ids(vr))
    await _persist_validation_report(db_session, experiment.id)
    await _persist_landing_page_with_telemetry(db_session, experiment.id)
    settings = get_settings()

    mock_complete = AsyncMock(return_value=(draft, _make_mock_llm_meta()))
    with patch(
        "app.services.insight_service.llm_client.complete_structured",
        mock_complete,
    ):
        await generate_insight_report(db_session, experiment.id)

    kwargs = mock_complete.call_args.kwargs
    assert kwargs["provider"] == settings.insight_provider
    assert kwargs["model"] == settings.insight_model


# ---------------------------------------------------------------------------
# 7. Cache breakpoints passed
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cache_breakpoints_passed(db_session: AsyncSession) -> None:
    experiment = await _persist_user_and_experiment(db_session)
    vr = _make_validation_report_pydantic()
    draft = _build_valid_draft(_valid_finding_ids(vr))
    await _persist_validation_report(db_session, experiment.id)
    await _persist_landing_page_with_telemetry(db_session, experiment.id)

    mock_complete = AsyncMock(return_value=(draft, _make_mock_llm_meta()))
    with patch(
        "app.services.insight_service.llm_client.complete_structured",
        mock_complete,
    ):
        await generate_insight_report(db_session, experiment.id)

    assert mock_complete.call_args.kwargs["cache_breakpoints"] == INSIGHT_CACHE_BREAKPOINTS


# ---------------------------------------------------------------------------
# 8. phase + prompt_name passed
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_phase_and_prompt_name_passed(db_session: AsyncSession) -> None:
    experiment = await _persist_user_and_experiment(db_session)
    vr = _make_validation_report_pydantic()
    draft = _build_valid_draft(_valid_finding_ids(vr))
    await _persist_validation_report(db_session, experiment.id)
    await _persist_landing_page_with_telemetry(db_session, experiment.id)

    mock_complete = AsyncMock(return_value=(draft, _make_mock_llm_meta()))
    with patch(
        "app.services.insight_service.llm_client.complete_structured",
        mock_complete,
    ):
        await generate_insight_report(db_session, experiment.id)

    kwargs = mock_complete.call_args.kwargs
    assert kwargs["phase"] == "insight"
    assert kwargs["prompt_name"] == PROMPT_NAME


# ---------------------------------------------------------------------------
# 9. Logging hygiene
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_logging_hygiene_no_draft_prose(db_session: AsyncSession) -> None:
    experiment = await _persist_user_and_experiment(db_session)
    vr = _make_validation_report_pydantic()
    draft = _build_valid_draft(_valid_finding_ids(vr))
    await _persist_validation_report(db_session, experiment.id)
    await _persist_landing_page_with_telemetry(db_session, experiment.id)

    mock_complete = AsyncMock(return_value=(draft, _make_mock_llm_meta()))
    with patch(
        "app.services.insight_service.llm_client.complete_structured",
        mock_complete,
    ), structlog.testing.capture_logs() as cap:
        await generate_insight_report(db_session, experiment.id)

    forbidden = {
        draft.recommendation,
        draft.traffic_summary.narrative,
        draft.research_takeaways[0].claim,
        draft.what_would_change_this,
    }
    for event in cap:
        serialized = str(event)
        for text in forbidden:
            assert text not in serialized

    generated = [e for e in cap if e.get("event") == "insight report generated"]
    assert len(generated) == 1
    assert generated[0]["experiment_id"] == str(experiment.id)
    assert generated[0]["recommendation_type"] == draft.recommendation_type.value
    assert "retry_count" in generated[0]


# ---------------------------------------------------------------------------
# 10. LandingPageNotLiveError propagates
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_landing_page_not_live_propagates(db_session: AsyncSession) -> None:
    experiment = await _persist_user_and_experiment(db_session)
    await _persist_validation_report(db_session, experiment.id)

    with patch(
        "app.services.insight_service.llm_client.complete_structured",
        AsyncMock(),
    ):
        with pytest.raises(LandingPageNotLiveError):
            await generate_insight_report(db_session, experiment.id)
