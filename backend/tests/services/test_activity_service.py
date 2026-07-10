"""Tests for human-facing experiment activity summarization."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from app.db.enums import ChatRole
from app.db.models.chat_message import ChatMessage
from app.db.models.experiment_event import ExperimentEvent
from app.db.models.llm_call import LLMCall
from app.services.activity_service import (
    deduplicate_activity,
    merge_activity_items,
    summarize_experiment_event,
    summarize_llm_call,
)


def _llm_call(**overrides: object) -> LLMCall:
    defaults = {
        "id": uuid4(),
        "experiment_id": uuid4(),
        "phase": "planner",
        "cost_category": "research",
        "provider": "kimi",
        "model": "kimi-k2.6",
        "prompt_name": "planner_v1",
        "prompt_tokens": 100,
        "completion_tokens": 50,
        "called_at": datetime(2026, 7, 9, 12, 0, tzinfo=timezone.utc),
    }
    defaults.update(overrides)
    return LLMCall(**defaults)  # type: ignore[arg-type]


def test_summarize_llm_call_planner() -> None:
    item = summarize_llm_call(_llm_call(phase="planner"))
    assert item is not None
    assert item.summary == "Research plan generated"
    assert item.event_type == "pipeline"


def test_summarize_llm_call_skips_refinement_chat() -> None:
    item = summarize_llm_call(
        _llm_call(phase="refinement", prompt_name="refinement_chat_v1")
    )
    assert item is None


def test_summarize_llm_call_tag_generator_by_prompt_name() -> None:
    item = summarize_llm_call(
        _llm_call(phase="refinement", prompt_name="tag_generator_v1")
    )
    assert item is not None
    assert item.summary == "Experiment tags generated"


def test_summarize_experiment_event_resource_added() -> None:
    event = ExperimentEvent(
        id=uuid4(),
        experiment_id=uuid4(),
        user_id=uuid4(),
        event_type="resource_added",
        payload={"title": "Competitor deck"},
        occurred_at=datetime(2026, 7, 9, 12, 0, tzinfo=timezone.utc),
    )
    item = summarize_experiment_event(event)
    assert item is not None
    assert item.summary == "Added resource: Competitor deck"


def test_summarize_experiment_event_skips_node_moved() -> None:
    event = ExperimentEvent(
        id=uuid4(),
        experiment_id=uuid4(),
        user_id=uuid4(),
        event_type="node_moved",
        payload={"summary": "node moved"},
        occurred_at=datetime(2026, 7, 9, 12, 0, tzinfo=timezone.utc),
    )
    assert summarize_experiment_event(event) is None


def test_merge_activity_items_limits_user_chat_to_three() -> None:
    experiment_id = uuid4()
    thread_id = uuid4()
    chat_rows = [
        ChatMessage(
            id=uuid4(),
            thread_id=thread_id,
            role=ChatRole.USER,
            content=f"message {idx}",
            experiment_id=experiment_id,
            created_at=datetime(2026, 7, 9, 12, idx, tzinfo=timezone.utc),
        )
        for idx in range(5)
    ]

    items = merge_activity_items([], chat_rows, [], limit=30)
    chat_items = [item for item in items if item.event_type == "chat_message"]
    assert len(chat_items) == 1
    assert chat_items[0].summary == "You sent 3 messages"


def test_merge_activity_items_empty_sources() -> None:
    assert merge_activity_items([], [], [], limit=30) == []


def test_deduplicate_reader_calls_within_five_minutes() -> None:
    reader_calls = [
        _llm_call(
            phase="reader",
            called_at=datetime(2026, 7, 9, 12, 0, idx, tzinfo=timezone.utc),
        )
        for idx in range(7)
    ]
    items = [summarize_llm_call(call) for call in reader_calls]
    items = [item for item in items if item is not None]

    deduped = deduplicate_activity(items)
    assert len(deduped) == 1
    assert deduped[0].summary == "Evidence extracted from 7 sources"
    assert deduped[0].metadata["group_count"] == 7
