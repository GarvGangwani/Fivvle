"""Chat message tree helpers — active branch, siblings, leaf navigation."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.chat_message import ChatMessage
from app.db.models.chat_thread import ChatThread


async def get_branch_up_to(
    db: AsyncSession,
    message_id: UUID,
) -> list[ChatMessage]:
    """Return the chain of messages from root to (and including) ``message_id``."""
    reverse_chain: list[ChatMessage] = []
    current_id: UUID | None = message_id
    seen: set[UUID] = set()

    while current_id is not None:
        if current_id in seen:
            break
        seen.add(current_id)
        msg = await db.get(ChatMessage, current_id)
        if msg is None:
            break
        reverse_chain.append(msg)
        current_id = msg.parent_message_id

    return list(reversed(reverse_chain))


async def get_active_branch(
    db: AsyncSession,
    thread_id: UUID,
) -> list[ChatMessage]:
    """Walk from the thread's active leaf back to the root (root first)."""
    thread = await db.get(ChatThread, thread_id)
    if thread is None or thread.active_leaf_message_id is None:
        return []
    return await get_branch_up_to(db, thread.active_leaf_message_id)


async def get_siblings(
    db: AsyncSession,
    message_id: UUID,
) -> list[ChatMessage]:
    """Return all messages that share a parent with ``message_id`` (incl. self)."""
    msg = await db.get(ChatMessage, message_id)
    if msg is None:
        return []

    if msg.parent_message_id is None:
        result = await db.execute(
            select(ChatMessage)
            .where(
                ChatMessage.thread_id == msg.thread_id,
                ChatMessage.parent_message_id.is_(None),
            )
            .order_by(ChatMessage.created_at.asc(), ChatMessage.id.asc())
        )
    else:
        result = await db.execute(
            select(ChatMessage)
            .where(ChatMessage.parent_message_id == msg.parent_message_id)
            .order_by(ChatMessage.created_at.asc(), ChatMessage.id.asc())
        )
    return list(result.scalars().all())


async def get_leaf_of_branch(
    db: AsyncSession,
    message_id: UUID,
) -> ChatMessage:
    """Walk forward taking the latest child at each fork until a leaf."""
    current = await db.get(ChatMessage, message_id)
    if current is None:
        raise ValueError(f"Message {message_id} not found")

    while True:
        result = await db.execute(
            select(ChatMessage)
            .where(ChatMessage.parent_message_id == current.id)
            .order_by(ChatMessage.created_at.desc(), ChatMessage.id.desc())
            .limit(1)
        )
        next_child = result.scalar_one_or_none()
        if next_child is None:
            return current
        current = next_child


async def set_active_leaf(
    db: AsyncSession,
    thread_id: UUID,
    leaf_message_id: UUID,
) -> ChatThread:
    """Point the thread's active branch at ``leaf_message_id`` (must be in thread)."""
    thread = await db.get(ChatThread, thread_id)
    if thread is None:
        raise ValueError(f"Thread {thread_id} not found")

    leaf = await db.get(ChatMessage, leaf_message_id)
    if leaf is None or leaf.thread_id != thread_id:
        raise ValueError("Leaf message does not belong to thread")

    thread.active_leaf_message_id = leaf_message_id
    await db.flush()
    return thread


async def sibling_position(
    db: AsyncSession,
    message_id: UUID,
) -> tuple[int, int]:
    """Return ``(sibling_index, sibling_count)`` for ``message_id``."""
    siblings = await get_siblings(db, message_id)
    if not siblings:
        return 0, 1
    index = next((i for i, s in enumerate(siblings) if s.id == message_id), 0)
    return index, len(siblings)


async def enrich_messages_with_sibling_info(
    db: AsyncSession,
    messages: list[ChatMessage],
) -> list[tuple[ChatMessage, int, int]]:
    """Attach ``(message, sibling_index, sibling_count)`` for API responses."""
    enriched: list[tuple[ChatMessage, int, int]] = []
    for msg in messages:
        index, count = await sibling_position(db, msg.id)
        enriched.append((msg, index, count))
    return enriched


def history_tuples_from_branch(
    messages: list[ChatMessage],
    *,
    exclude_system_kinds: frozenset | None = None,
    plain_chat_only: bool = False,
    plain_chat_kinds: frozenset | None = None,
) -> list[tuple[str, str]]:
    """Convert ORM messages to ``(role, content)`` history for LLM calls."""
    history: list[tuple[str, str]] = []
    for row in messages:
        if exclude_system_kinds and row.turn_kind in exclude_system_kinds:
            continue
        if (
            plain_chat_only
            and row.turn_kind is not None
            and (plain_chat_kinds is None or row.turn_kind not in plain_chat_kinds)
        ):
            continue
        history.append((row.role.value, row.content))
    return history
