"""In-process durable universal-chat turns (ADR 0009-style detach).

The turn body runs in ``asyncio.create_task`` with its own DB sessionmaker.
SSE subscribers observe an in-memory event fan-out; disconnect does not cancel
the task. Explicit ``cancel_universal_turn`` sets a flag the task checks.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from app.logging_config import get_logger

_logger = get_logger(__name__)

TURN_STATUS_KEY = "turn_status"
TURN_ID_KEY = "turn_id"
TURN_STATUS_RUNNING = "running"
TURN_STATUS_DONE = "done"
TURN_STATUS_FAILED = "failed"


@dataclass
class UniversalTurnRuntime:
    turn_id: UUID
    experiment_id: UUID
    thread_id: UUID
    status_message_id: UUID | None
    cancel: asyncio.Event = field(default_factory=asyncio.Event)
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    history: list[tuple[str, dict[str, Any]]] = field(default_factory=list)
    subscribers: list[asyncio.Queue[tuple[str, dict[str, Any]] | None]] = field(
        default_factory=list
    )
    closed: bool = False
    task: asyncio.Task[None] | None = None


_active_turns: dict[UUID, UniversalTurnRuntime] = {}


def get_active_turn(turn_id: UUID) -> UniversalTurnRuntime | None:
    return _active_turns.get(turn_id)


def request_turn_cancel(turn_id: UUID) -> bool:
    """Signal cancel for an in-process turn. Returns False if not running here."""
    runtime = _active_turns.get(turn_id)
    if runtime is None:
        return False
    runtime.cancel.set()
    _logger.info(
        "universal chat turn cancel requested",
        turn_id=str(turn_id),
        experiment_id=str(runtime.experiment_id),
    )
    return True


async def publish_turn_event(
    runtime: UniversalTurnRuntime,
    event_name: str,
    payload: dict[str, Any],
) -> None:
    event = (event_name, payload)
    async with runtime.lock:
        runtime.history.append(event)
        for queue in list(runtime.subscribers):
            queue.put_nowait(event)


async def close_turn_runtime(runtime: UniversalTurnRuntime) -> None:
    async with runtime.lock:
        runtime.closed = True
        for queue in list(runtime.subscribers):
            queue.put_nowait(None)
        runtime.subscribers.clear()
    _active_turns.pop(runtime.turn_id, None)


def register_turn_runtime(
    *,
    turn_id: UUID,
    experiment_id: UUID,
    thread_id: UUID,
    status_message_id: UUID | None,
) -> UniversalTurnRuntime:
    existing = _active_turns.get(turn_id)
    if existing is not None and existing.task is not None and not existing.task.done():
        return existing
    runtime = UniversalTurnRuntime(
        turn_id=turn_id,
        experiment_id=experiment_id,
        thread_id=thread_id,
        status_message_id=status_message_id,
    )
    _active_turns[turn_id] = runtime
    return runtime


async def subscribe_turn_events(
    runtime: UniversalTurnRuntime,
) -> asyncio.Queue[tuple[str, dict[str, Any]] | None]:
    """Replay buffered events, then receive live ones until close sentinel."""
    queue: asyncio.Queue[tuple[str, dict[str, Any]] | None] = asyncio.Queue()
    async with runtime.lock:
        for event in runtime.history:
            queue.put_nowait(event)
        if runtime.closed:
            queue.put_nowait(None)
        else:
            runtime.subscribers.append(queue)
    return queue


async def unsubscribe_turn_events(
    runtime: UniversalTurnRuntime,
    queue: asyncio.Queue[tuple[str, dict[str, Any]] | None],
) -> None:
    async with runtime.lock:
        if queue in runtime.subscribers:
            runtime.subscribers.remove(queue)


def clear_turn_registry_for_tests() -> None:
    """Test helper — drop in-memory turn handles."""
    _active_turns.clear()
