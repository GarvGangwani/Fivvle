"""Tests for opt-in Reader drift capture (READER_DRIFT_CAPTURE_DIR)."""

from __future__ import annotations

import json
import os
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

import app.services.reader_service as reader_svc
from app.config import get_settings
from app.integrations.tavily import TavilyResult
from app.llm.client import LLMResult
from app.schemas.planner import ResearchQuestion
from app.schemas.reader import ExtractedEvidenceDraft, ReaderOutputDraft
from app.services.reader_service import _extract_for_question
from tests.services.test_reader_service import _llm_meta, _minimal_refined_idea


def _tavily(url: str, content: str) -> TavilyResult:
    return TavilyResult(title="t", url=url, content=content, score=0.9)


def _question(qid: str = "q1") -> ResearchQuestion:
    return ResearchQuestion(
        id=qid,
        question="What is the market size?",
        rationale="r",
        search_queries=["sq"],
    )


def _passing_and_drifting_draft(qid: str, url_pass: str, url_drift: str) -> ReaderOutputDraft:
    return ReaderOutputDraft(
        question_id=qid,
        extracted_evidence=[
            ExtractedEvidenceDraft(
                source_url=url_pass,
                relevance="high",
                verbatim_quote="exact match phrase",
                paraphrase="passing paraphrase",
                named_entities=[],
            ),
            ExtractedEvidenceDraft(
                source_url=url_drift,
                relevance="medium",
                verbatim_quote="this quote is not in the source",
                paraphrase="drifting paraphrase",
                named_entities=[],
            ),
        ],
    )


async def _run_extract(
    *,
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
    env_value: str | None,
) -> None:
    capture_root = tmp_path / "capture"
    capture_root.mkdir()
    if env_value is not None:
        monkeypatch.setenv("READER_DRIFT_CAPTURE_DIR", env_value)

    exp_id = uuid4()
    url_pass = "https://example.com/pass"
    url_drift = "https://example.com/drift"
    question = _question()
    draft = _passing_and_drifting_draft("q1", url_pass, url_drift)

    async def fake_complete(*_a, **_kw):
        return draft, _llm_meta()

    db = MagicMock(spec=[])
    with patch(
        "app.services.reader_service.llm_client.complete_structured",
        AsyncMock(side_effect=fake_complete),
    ):
        await _extract_for_question(
            db=db,
            experiment_id=exp_id,
            question=question,
            tavily_results=[
                _tavily(url_pass, "prefix exact match phrase suffix"),
                _tavily(url_drift, "totally different body text"),
            ],
            refined_idea=_minimal_refined_idea(),
            research_questions=[question],
            settings=get_settings(),
        )


@pytest.mark.asyncio
async def test_drift_capture_unset_writes_no_file(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("READER_DRIFT_CAPTURE_DIR", raising=False)
    await _run_extract(tmp_path=tmp_path, monkeypatch=monkeypatch, env_value=None)
    assert os.listdir(tmp_path / "capture") == []


@pytest.mark.asyncio
async def test_drift_capture_set_writes_json_with_expected_keys(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    capture_root = tmp_path / "capture"
    await _run_extract(
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
        env_value=str(capture_root),
    )

    exp_dirs = [d for d in capture_root.iterdir() if d.is_dir()]
    assert len(exp_dirs) == 1
    json_files = list(exp_dirs[0].glob("*.json"))
    assert len(json_files) == 1

    payload = json.loads(json_files[0].read_text(encoding="utf-8"))
    assert set(payload) == {
        "experiment_id",
        "question_id",
        "question_text",
        "prompt_name",
        "model",
        "tavily_results",
        "raw_draft",
        "final_output",
        "per_quote_classifications",
        "stats",
    }
    assert len(payload["per_quote_classifications"]) == 2
    failure_classes = {
        item["failure_class"] for item in payload["per_quote_classifications"]
    }
    assert None in failure_classes
    assert "unmatched" in failure_classes
    assert payload["stats"]["cost_usd"] == "0.01"


@pytest.mark.asyncio
async def test_drift_capture_write_failure_does_not_raise(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    capture_root = tmp_path / "capture"
    capture_root.mkdir()
    monkeypatch.setenv("READER_DRIFT_CAPTURE_DIR", str(capture_root))

    exp_id = uuid4()
    url = "https://example.com/a"
    question = _question()
    draft = ReaderOutputDraft(
        question_id="q1",
        extracted_evidence=[
            ExtractedEvidenceDraft(
                source_url=url,
                relevance="high",
                verbatim_quote=None,
                paraphrase="ok",
                named_entities=[],
            ),
        ],
    )

    async def fake_complete(*_a, **_kw):
        return draft, LLMResult(
            text="{}",
            provider="anthropic",
            model="claude-sonnet-4-6",
            prompt_tokens=1,
            completion_tokens=1,
            cost_usd=Decimal("0"),
            latency_ms=1,
        )

    db = MagicMock(spec=[])
    with (
        patch(
            "app.services.reader_service.llm_client.complete_structured",
            AsyncMock(side_effect=fake_complete),
        ),
        patch("builtins.open", side_effect=OSError("permission denied")),
        patch.object(reader_svc._logger, "warning") as warn_mock,
    ):
        out, stats = await _extract_for_question(
            db=db,
            experiment_id=exp_id,
            question=question,
            tavily_results=[_tavily(url, "hello")],
            refined_idea=_minimal_refined_idea(),
            research_questions=[question],
            settings=get_settings(),
        )

    assert len(out.extracted_evidence) == 1
    assert stats["sentinel_reason"] is None
    warn_mock.assert_called()
    capture_msgs = [
        c.args[0] for c in warn_mock.call_args_list if c.args and isinstance(c.args[0], str)
    ]
    assert "reader drift capture failed" in capture_msgs
