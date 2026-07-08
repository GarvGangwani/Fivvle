"""Tests for voices_devloop harness wiring."""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.llm.prompts.voices import VoicesExtractionDraft
from app.schemas.voices import VoicesEvidenceDraft
from scripts.voices_devloop.voices_devloop import run_harness


def _voices_draft() -> VoicesExtractionDraft:
    return VoicesExtractionDraft(
        atoms=[
            VoicesEvidenceDraft(
                source_url=(
                    "https://www.reddit.com/r/startups/comments/p1/founders_scattered_tools/"
                ),
                subreddit="startups",
                kind="post",
                verbatim_quote=(
                    "I spent weeks jumping between spreadsheets and random research tabs."
                ),
                pain_pattern="Scattered validation workflow",
                on_target_geography=True,
                signal_strength="strong",
            )
        ]
    )


def _fake_report_dict(voices: str) -> MagicMock:
    mock = MagicMock()
    mock.voices = voices
    mock.model_dump.return_value = {"voices": voices}
    return mock


@pytest.mark.asyncio
async def test_voices_devloop_full_mode_produces_voices_section() -> None:
    with (
        patch(
            "app.services.voices_service.get_subreddits_for_topic",
            new_callable=AsyncMock,
            return_value=["startups", "Entrepreneur"],
        ),
        patch(
            "app.services.voices_service.llm_client.complete_structured",
            new_callable=AsyncMock,
            return_value=(_voices_draft(), MagicMock(cost_usd=Decimal("0.01"))),
        ),
        patch(
            "scripts.voices_devloop.voices_devloop.synthesize_report",
            new_callable=AsyncMock,
            return_value=_fake_report_dict(
                "Community voices surfaced strong founder pain around scattered tools."
            ),
        ),
    ):
        result = await run_harness(
            upstream="us_founder_platform",
            reddit_mode="full",
            skip_synthesizer=False,
            print_voices_only=False,
            print_full_report=False,
            override_model=None,
        )

    assert result["validation_report"]["voices"]
    assert result["voices_output"]["skipped_reason"] is None


@pytest.mark.asyncio
async def test_voices_devloop_empty_mode_produces_absence_sentence() -> None:
    absence = (
        "Reddit fetching failed for this run. No community voices are included in this report."
    )
    with (
        patch(
            "app.services.voices_service.get_subreddits_for_topic",
            new_callable=AsyncMock,
            return_value=["startups"],
        ),
        patch(
            "scripts.voices_devloop.voices_devloop.synthesize_report",
            new_callable=AsyncMock,
            return_value=_fake_report_dict(absence),
        ),
    ):
        result = await run_harness(
            upstream="us_founder_platform",
            reddit_mode="empty",
            skip_synthesizer=False,
            print_voices_only=False,
            print_full_report=False,
            override_model=None,
        )

    assert result["voices_output"]["skipped_reason"] == "praw_all_failed"
    assert absence in result["validation_report"]["voices"]


@pytest.mark.asyncio
async def test_voices_devloop_skip_synthesizer_mode() -> None:
    with (
        patch(
            "app.services.voices_service.get_subreddits_for_topic",
            new_callable=AsyncMock,
            return_value=["startups"],
        ),
        patch(
            "app.services.voices_service.llm_client.complete_structured",
            new_callable=AsyncMock,
            return_value=(_voices_draft(), MagicMock(cost_usd=Decimal("0.01"))),
        ),
        patch(
            "scripts.voices_devloop.voices_devloop.synthesize_report",
            new_callable=AsyncMock,
        ) as mock_synth,
    ):
        result = await run_harness(
            upstream="us_founder_platform",
            reddit_mode="full",
            skip_synthesizer=True,
            print_voices_only=False,
            print_full_report=False,
            override_model=None,
        )

    mock_synth.assert_not_called()
    assert "voices_output" in result
    assert "validation_report" not in result
