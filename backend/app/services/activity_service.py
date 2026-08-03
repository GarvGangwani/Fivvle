"""Human-facing activity stream summarizers for the experiment canvas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from app.db.enums import ChatRole
from app.db.models.chat_message import ChatMessage
from app.db.models.experiment_event import ExperimentEvent
from app.db.models.llm_call import LLMCall
from app.schemas.experiment_canvas import ActivityItem

ALLOWED_EXPERIMENT_EVENT_TYPES = frozenset(
    {
        "resource_added",
        "resource_deleted",
        "phase_completed",
        "verdict_rendered",
    }
)

UI_TELEMETRY_EVENT_TYPES = frozenset(
    {
        "node_moved",
        "layout_reset",
        "nodes_repositioned",
    }
)

MAX_USER_CHAT_ACTIVITY = 3
_DEDUP_WINDOW_SECONDS = 300


def summarize_llm_call(call: LLMCall) -> ActivityItem | None:
    """Return an ActivityItem for user-facing LLM events, or None to skip."""
    phase = call.phase or ""

    if phase == "planner":
        return ActivityItem(
            id=f"llm-{call.id}",
            event_type="pipeline",
            summary="Research plan generated",
            metadata={"phase": phase},
            occurred_at=call.called_at,
        )

    if phase == "reader":
        return ActivityItem(
            id=f"llm-{call.id}",
            event_type="pipeline",
            summary="Evidence extracted from sources",
            metadata={"phase": phase},
            occurred_at=call.called_at,
        )

    if phase == "reflector":
        return ActivityItem(
            id=f"llm-{call.id}",
            event_type="pipeline",
            summary="Evidence quality reviewed",
            metadata={"phase": phase},
            occurred_at=call.called_at,
        )

    if phase == "synthesizer":
        return ActivityItem(
            id=f"llm-{call.id}",
            event_type="pipeline",
            summary="Validation report ready",
            metadata={"phase": phase},
            occurred_at=call.called_at,
        )

    if "tag_generator" in call.prompt_name:
        return ActivityItem(
            id=f"llm-{call.id}",
            event_type="pipeline",
            summary="Experiment tags generated",
            metadata={"phase": phase},
            occurred_at=call.called_at,
        )

    if phase == "landing_page":
        return ActivityItem(
            id=f"llm-{call.id}",
            event_type="pipeline",
            summary="Landing page draft ready",
            metadata={"phase": phase},
            occurred_at=call.called_at,
        )

    return None


def summarize_chat_message(message: ChatMessage) -> ActivityItem | None:
    """Return an ActivityItem for user chat messages only."""
    if message.role != ChatRole.USER:
        return None
    return ActivityItem(
        id=f"chat-{message.id}",
        event_type="chat_message",
        summary="You sent a message",
        metadata={"turn_kind": message.turn_kind.value if message.turn_kind else None},
        occurred_at=message.created_at,
    )


def summarize_experiment_event(event: ExperimentEvent) -> ActivityItem | None:
    """Return an ActivityItem for allowed experiment events, or None to skip."""
    if event.event_type in UI_TELEMETRY_EVENT_TYPES:
        return None
    if event.event_type not in ALLOWED_EXPERIMENT_EVENT_TYPES:
        return None

    payload = event.payload or {}
    title = str(payload.get("title") or "").strip()

    if event.event_type == "resource_added":
        summary = f"Added resource: {title}" if title else "Added resource"
    elif event.event_type == "resource_deleted":
        summary = f"Removed resource: {title}" if title else "Removed resource"
    elif event.event_type == "phase_completed":
        act = str(payload.get("act") or payload.get("phase") or "Phase")
        summary = f"{act} phase completed"
    elif event.event_type == "verdict_rendered":
        verdict = str(payload.get("verdict") or "updated")
        summary = f"Verdict: {verdict}"
    else:
        summary = str(payload.get("summary") or event.event_type.replace("_", " "))

    return ActivityItem(
        id=str(event.id),
        event_type=event.event_type,
        summary=summary,
        metadata=payload,
        occurred_at=event.occurred_at,
    )


def deduplicate_activity(items: list[ActivityItem]) -> list[ActivityItem]:
    """Collapse consecutive same-type activity items within a 5-minute window."""
    if not items:
        return items

    sorted_items = sorted(items, key=_sort_key)
    result: list[ActivityItem] = []

    for item in sorted_items:
        if result and _same_group(result[-1], item):
            prev = result[-1]
            prev_last = _last_occurred_at(prev)
            if abs((item.occurred_at - prev_last).total_seconds()) < _DEDUP_WINDOW_SECONDS:
                count = int(prev.metadata.get("group_count", 1)) + 1
                phase = prev.metadata.get("phase")
                result[-1] = prev.model_copy(
                    update={
                        "summary": _regroup_summary(prev.event_type, phase, count),
                        "metadata": {
                            **prev.metadata,
                            "group_count": count,
                            "last_occurred_at": item.occurred_at.isoformat(),
                        },
                    }
                )
                continue
        result.append(item)

    result.sort(key=_sort_key, reverse=True)
    return result


def merge_activity_items(
    llm_calls: list[LLMCall],
    chat_messages: list[ChatMessage],
    experiment_events: list[ExperimentEvent],
    *,
    limit: int,
    universal_thread_id: UUID | None = None,
) -> list[ActivityItem]:
    """Merge and sort activity sources into a user-facing feed.

    Chat rows are scoped to ``universal_thread_id`` only (master rail). Refine
    and evidence thread messages are implementation detail of sub-agents and
    do not surface in activity — including when ``universal_thread_id`` is
    unset (no master-rail history yet).
    """
    items: list[ActivityItem] = []

    for call in llm_calls:
        item = summarize_llm_call(call)
        if item is not None:
            items.append(item)

    if universal_thread_id is not None:
        scoped_chat = [
            msg
            for msg in chat_messages
            if msg.thread_id == universal_thread_id
        ]
    else:
        scoped_chat = []

    user_messages = [msg for msg in scoped_chat if msg.role == ChatRole.USER]
    user_messages.sort(key=lambda row: (row.created_at, str(row.id)), reverse=True)
    for message in user_messages[:MAX_USER_CHAT_ACTIVITY]:
        item = summarize_chat_message(message)
        if item is not None:
            items.append(item)

    for event in experiment_events:
        item = summarize_experiment_event(event)
        if item is not None:
            items.append(item)

    items = deduplicate_activity(items)
    return items[:limit]


def _group_key(item: ActivityItem) -> tuple[str, ...]:
    if item.event_type == "pipeline":
        phase = item.metadata.get("phase")
        return (item.event_type, str(phase) if phase is not None else "")
    return (item.event_type,)


def _same_group(a: ActivityItem, b: ActivityItem) -> bool:
    return _group_key(a) == _group_key(b)


def _last_occurred_at(item: ActivityItem) -> datetime:
    raw = item.metadata.get("last_occurred_at")
    if isinstance(raw, str):
        return datetime.fromisoformat(raw)
    return item.occurred_at


def _regroup_summary(event_type: str, phase: object, count: int) -> str:
    if event_type == "pipeline" and phase == "reader":
        return f"Evidence extracted from {count} sources"
    if event_type == "chat_message":
        if count == 1:
            return "You sent a message"
        return f"You sent {count} messages"
    if event_type == "pipeline" and phase == "planner":
        return "Research plan generated"
    if event_type == "pipeline" and phase == "reflector":
        return "Evidence quality reviewed"
    if event_type == "pipeline" and phase == "synthesizer":
        return "Validation report ready"
    return f"{count} events"


def _sort_key(item: ActivityItem) -> tuple[datetime, str]:
    return (item.occurred_at, item.id)
