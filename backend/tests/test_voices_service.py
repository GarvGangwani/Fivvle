"""Unit tests for voices_service."""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import httpx
import pytest

from app.integrations.perplexity import PerplexityResult
from app.llm.prompts.voices import VoicesExtractionDraft
from app.schemas.planner import ResearchPlan, ResearchQuestion
from app.schemas.refinement import RefinedIdea
from app.schemas.voices import VoicesEvidenceDraft
from app.services.voices_service import _serialize_reddit_content, execute_voices


def _refined_idea() -> RefinedIdea:
    return RefinedIdea(
        refined_one_liner="HR policy bot in Slack",
        target_audience="Ops managers at mid-size companies",
        value_proposition="Cuts repeat policy questions",
        risks=[
            "Do teams already use Guru?",
            "Is handbook freshness the blocker?",
            "Will HR approve a bot?",
        ],
        headline="Policy answers in Slack",
        subheadline="Connect your handbook once",
        cta_text="Join waitlist",
    )


def _plan() -> ResearchPlan:
    return ResearchPlan(
        questions=[
            ResearchQuestion(
                id=f"q{i}",
                question=f"Question {i}?",
                rationale="r",
                search_queries=[f"q{i}"],
            )
            for i in range(1, 6)
        ]
    )


def _settings() -> MagicMock:
    s = MagicMock()
    s.voices_max_subreddits = 3
    s.voices_threads_per_subreddit = 5
    s.voices_comments_per_thread = 7
    s.voices_post_max_age_days = 1095
    s.voices_reddit_concurrency = 3
    s.voices_extraction_provider = "kimi"
    s.voices_extraction_model = "kimi-k2.6"
    return s


def _perplexity_post(
    *,
    url: str = "https://www.reddit.com/r/startups/comments/abc123/",
    title: str = "Need a better HR tool",
    snippet: str = "We tried Guru and it failed us",
) -> PerplexityResult:
    return PerplexityResult(title=title, url=url, snippet=snippet)


@pytest.mark.asyncio
async def test_happy_path_returns_atoms() -> None:
    db = AsyncMock()
    post_url = "https://www.reddit.com/r/startups/comments/abc123/"
    quote = "We tried Guru and it failed us"
    draft = VoicesExtractionDraft(
        atoms=[
            VoicesEvidenceDraft(
                source_url=post_url,
                subreddit="startups",
                kind="post",
                verbatim_quote=quote,
                pain_pattern="Teams find incumbent tools disappointing.",
                on_target_geography=False,
                signal_strength="strong",
            )
        ]
    )

    with (
        patch(
            "app.services.voices_service.get_subreddits_for_topic",
            AsyncMock(return_value=["startups", "entrepreneur", "saas"]),
        ),
        patch(
            "app.services.voices_service.perplexity_integration.search",
            AsyncMock(return_value=[_perplexity_post(url=post_url, snippet=quote)]),
        ),
        patch(
            "app.services.voices_service.llm_client.complete_structured",
            AsyncMock(return_value=(draft, MagicMock(cost_usd=Decimal("0.05"), latency_ms=200))),
        ),
    ):
        out = await execute_voices(
            db=db,
            refined_idea=_refined_idea(),
            research_plan=_plan(),
            targeting=None,
            experiment_id=uuid4(),
            settings=_settings(),
        )

    assert len(out.atoms) == 1
    assert out.threads_fetched >= 1
    assert out.comments_fetched == 0
    assert out.skipped_reason is None


@pytest.mark.asyncio
async def test_empty_subreddit_selection() -> None:
    db = AsyncMock()
    with patch(
        "app.services.voices_service.get_subreddits_for_topic",
        AsyncMock(return_value=[]),
    ):
        out = await execute_voices(
            db=db,
            refined_idea=_refined_idea(),
            research_plan=_plan(),
            targeting=None,
            experiment_id=uuid4(),
            settings=_settings(),
        )
    assert out.atoms == []
    assert out.skipped_reason == "subreddit_selection_returned_empty"


@pytest.mark.asyncio
async def test_all_praw_fails() -> None:
    db = AsyncMock()
    with (
        patch(
            "app.services.voices_service.get_subreddits_for_topic",
            AsyncMock(return_value=["startups"]),
        ),
        patch(
            "app.services.voices_service.perplexity_integration.search",
            AsyncMock(side_effect=httpx.HTTPStatusError(
                "forbidden",
                request=httpx.Request("POST", "https://api.perplexity.ai/chat/completions"),
                response=httpx.Response(403, request=httpx.Request("POST", "https://api.perplexity.ai/chat/completions")),
            )),
        ),
    ):
        out = await execute_voices(
            db=db,
            refined_idea=_refined_idea(),
            research_plan=_plan(),
            targeting=None,
            experiment_id=uuid4(),
            settings=_settings(),
        )
    assert out.skipped_reason == "praw_all_failed"


@pytest.mark.asyncio
async def test_llm_extraction_fails() -> None:
    db = AsyncMock()
    with (
        patch(
            "app.services.voices_service.get_subreddits_for_topic",
            AsyncMock(return_value=["startups"]),
        ),
        patch(
            "app.services.voices_service.perplexity_integration.search",
            AsyncMock(return_value=[_perplexity_post()]),
        ),
        patch(
            "app.services.voices_service.llm_client.complete_structured",
            AsyncMock(side_effect=RuntimeError("llm")),
        ),
    ):
        out = await execute_voices(
            db=db,
            refined_idea=_refined_idea(),
            research_plan=_plan(),
            targeting=None,
            experiment_id=uuid4(),
            settings=_settings(),
        )
    assert out.skipped_reason == "llm_extraction_failed"


@pytest.mark.asyncio
async def test_quote_validation_drops_invalid_atoms() -> None:
    db = AsyncMock()
    post_url = "https://www.reddit.com/r/startups/comments/abc123/"
    draft = VoicesExtractionDraft(
        atoms=[
            VoicesEvidenceDraft(
                source_url=post_url,
                subreddit="startups",
                kind="post",
                verbatim_quote="We tried Guru and it failed us",
                pain_pattern="Incumbent tools disappoint users.",
                on_target_geography=False,
                signal_strength="strong",
            ),
            VoicesEvidenceDraft(
                source_url=post_url,
                subreddit="startups",
                kind="post",
                verbatim_quote="THIS QUOTE IS NOT IN SOURCE",
                pain_pattern="Fake quote should be dropped.",
                on_target_geography=False,
                signal_strength="weak",
            ),
        ]
    )

    with (
        patch(
            "app.services.voices_service.get_subreddits_for_topic",
            AsyncMock(return_value=["startups"]),
        ),
        patch(
            "app.services.voices_service.perplexity_integration.search",
            AsyncMock(return_value=[_perplexity_post(url=post_url)]),
        ),
        patch(
            "app.services.voices_service.llm_client.complete_structured",
            AsyncMock(return_value=(draft, MagicMock(cost_usd=Decimal("0.05"), latency_ms=200))),
        ),
    ):
        out = await execute_voices(
            db=db,
            refined_idea=_refined_idea(),
            research_plan=_plan(),
            targeting=None,
            experiment_id=uuid4(),
            settings=_settings(),
        )

    assert len(out.atoms) == 1


@pytest.mark.asyncio
async def test_perplexity_results_without_dates_are_kept() -> None:
    db = AsyncMock()
    with (
        patch(
            "app.services.voices_service.get_subreddits_for_topic",
            AsyncMock(return_value=["startups"]),
        ),
        patch(
            "app.services.voices_service.perplexity_integration.search",
            AsyncMock(return_value=[_perplexity_post()]),
        ),
        patch(
            "app.services.voices_service.llm_client.complete_structured",
            AsyncMock(side_effect=RuntimeError("llm")),
        ),
    ):
        out = await execute_voices(
            db=db,
            refined_idea=_refined_idea(),
            research_plan=_plan(),
            targeting=None,
            experiment_id=uuid4(),
            settings=_settings(),
        )
    assert out.threads_fetched == 1
    assert out.skipped_reason == "llm_extraction_failed"


def test_serialize_omits_null_score_and_created_utc() -> None:
    from app.services.voices_service import _FetchedPost

    content = _serialize_reddit_content(
        [
            _FetchedPost(
                url="https://www.reddit.com/r/startups/comments/x/",
                subreddit="startups",
                title="Title",
                selftext="Body text",
                score=None,
                created_utc=None,
                post_id=None,
            )
        ]
    )
    assert 'score="' not in content
    assert 'created_utc="' not in content
    assert 'kind="post"' in content


@pytest.mark.asyncio
async def test_reddit_content_never_in_logs(caplog: pytest.LogCaptureFixture) -> None:
    db = AsyncMock()
    sensitive = "SECRET_REDDIT_BODY_TEXT_XYZ"

    with (
        patch(
            "app.services.voices_service.get_subreddits_for_topic",
            AsyncMock(return_value=["startups"]),
        ),
        patch(
            "app.services.voices_service.perplexity_integration.search",
            AsyncMock(return_value=[_perplexity_post(snippet=sensitive)]),
        ),
        patch(
            "app.services.voices_service.llm_client.complete_structured",
            AsyncMock(side_effect=RuntimeError("llm")),
        ),
    ):
        await execute_voices(
            db=db,
            refined_idea=_refined_idea(),
            research_plan=_plan(),
            targeting=None,
            experiment_id=uuid4(),
            settings=_settings(),
        )

    assert sensitive not in caplog.text
