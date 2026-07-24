"""Universal chat service — canvas coach / future agent surface.

Independent of chat_service.py and evidence_chat_service.py by design. Messages
carry ``turn_kind=UNIVERSAL_CHAT`` on an isolated ``experiments.universal_thread_id``
ChatThread so Refine and Evidence histories never mix.

v1 is linear only: each user message hangs off the current active leaf; the
assistant reply becomes the new leaf. No edit / regenerate / sibling navigation.

Tool rows (``tool_call`` / ``tool_result``) are not produced by this service in
v1, but ``list_universal_chat_messages`` serializes them if present. See
``ChatMessage.tool_payload`` for branching semantics when tools land.

Per AGENTS.md: project context and chat history are untrusted data — wrapped in
tagged sections in the prompt (see app/llm/prompts/universal_chat.py).
LLMCall cost logging happens inside llm_client (phase=universal_chat).
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import app.llm.client as llm_client
from app.config import get_settings
from app.db.enums import ChatRole, ChatTurnKind, ExperimentStatus
from app.db.models.chat_message import ChatMessage
from app.db.models.chat_thread import ChatThread
from app.db.models.experiment import Experiment
from app.db.models.user import User
from app.llm.prompts.universal_chat import (
    PROMPT_NAME_UNIVERSAL_CHAT,
    UNIVERSAL_CHAT_SYSTEM_PROMPT,
    build_universal_chat_user_prompt,
)
from app.logging_config import get_logger
from app.services.chat_tree_service import get_active_branch, set_active_leaf
from app.services.experiment_project_context import get_experiment_project_context

_logger = get_logger(__name__)

_MAX_TOKENS = 1024
_TEMPERATURE = 0.7
# ~3k-token proxy. Drop oldest full user+assistant pairs until under budget.
_HISTORY_CHAR_BUDGET = 12000

_FALLBACK_TEXT = (
    "I couldn't generate a response for that. Please try rephrasing your question."
)


class UniversalChatNotFound(Exception):
    """Experiment not found / not owned.

    Mapped to HTTP 404 by the router — never reveal existence for another user
    (AGENTS.md "Authentication and authorization").
    """


class UniversalChatUnavailable(Exception):
    """Chat is not available for this experiment (e.g. archived).

    Mapped to HTTP 409 by the router.
    """


@dataclass(frozen=True)
class UniversalChatResult:
    user_message: ChatMessage
    assistant_message: ChatMessage
    thread_id: UUID


@dataclass(frozen=True)
class UniversalChatMessages:
    thread_id: UUID | None
    active_leaf_message_id: UUID | None
    messages: list[ChatMessage]


def _sanitize(message: str) -> str:
    return message.strip()


def _project_name(experiment: Experiment) -> str:
    name = (experiment.name or "").strip()
    return name or "Untitled project"


def _history_for_prompt(messages: list[ChatMessage]) -> str:
    """Render prior turns for the prompt, bounded by char budget.

    Includes tool_call / tool_result rows as labeled lines so a future agent
    turn can see prior tool exchanges. Drops oldest messages first.
    """
    lines: list[str] = []
    for msg in messages:
        role = msg.role.value
        lines.append(f"[{role}]: {msg.content}")

    while lines and sum(len(line) + 1 for line in lines) > _HISTORY_CHAR_BUDGET:
        lines.pop(0)
    return "\n".join(lines)


async def _load_owned_experiment(
    db: AsyncSession,
    current_user: User,
    experiment_id: UUID,
) -> Experiment:
    result = await db.execute(select(Experiment).where(Experiment.id == experiment_id))
    experiment = result.scalar_one_or_none()
    if experiment is None or experiment.user_id != current_user.id:
        raise UniversalChatNotFound("Experiment not found")
    if experiment.status == ExperimentStatus.ARCHIVED:
        raise UniversalChatUnavailable(
            "Chat is not available for archived experiments"
        )
    return experiment


async def _resolve_universal_thread(
    db: AsyncSession,
    user: User,
    experiment: Experiment,
) -> ChatThread:
    if experiment.universal_thread_id is not None:
        result = await db.execute(
            select(ChatThread).where(ChatThread.id == experiment.universal_thread_id)
        )
        thread = result.scalar_one_or_none()
        if thread is not None and thread.user_id == user.id:
            return thread

    thread = ChatThread(
        user_id=user.id,
        title=f"Universal chat: {_project_name(experiment)}",
    )
    db.add(thread)
    await db.flush()
    experiment.universal_thread_id = thread.id
    await db.flush()
    return thread


async def send_universal_chat_message(
    db: AsyncSession,
    current_user: User,
    experiment_id: UUID,
    message: str,
) -> UniversalChatResult:
    """Send one universal-chat turn and persist both rows.

    Creates ``universal_thread_id`` on first call. Linear parent chain only.

    Raises:
        UniversalChatNotFound: experiment not found / not owned.
        UniversalChatUnavailable: archived experiment.
        ValueError: message empty after sanitization.
        LLM provider errors propagate (mapped to 502 by the router).
    """
    clean_message = _sanitize(message)
    if not clean_message:
        raise ValueError("message must not be empty")

    experiment = await _load_owned_experiment(db, current_user, experiment_id)
    thread = await _resolve_universal_thread(db, current_user, experiment)

    parent_id = thread.active_leaf_message_id
    history = await get_active_branch(db, thread.id) if parent_id is not None else []

    project_context = await get_experiment_project_context(db, experiment)
    user_prompt = build_universal_chat_user_prompt(
        project_context=project_context.to_prompt_block(),
        chat_history=_history_for_prompt(history),
        user_message=clean_message,
    )

    user_msg = ChatMessage(
        thread_id=thread.id,
        role=ChatRole.USER,
        content=clean_message,
        experiment_id=experiment.id,
        turn_kind=ChatTurnKind.UNIVERSAL_CHAT,
        parent_message_id=parent_id,
    )
    db.add(user_msg)
    await db.flush()

    settings = get_settings()
    result = await llm_client.complete(
        db,
        provider=settings.refinement_provider,
        model=settings.refinement_model,
        prompt_name=PROMPT_NAME_UNIVERSAL_CHAT,
        system=UNIVERSAL_CHAT_SYSTEM_PROMPT,
        user=user_prompt,
        max_tokens=_MAX_TOKENS,
        temperature=_TEMPERATURE,
        experiment_id=experiment.id,
        phase="universal_chat",
    )
    assistant_text = result.text.strip() or _FALLBACK_TEXT

    assistant_msg = ChatMessage(
        thread_id=thread.id,
        role=ChatRole.ASSISTANT,
        content=assistant_text,
        experiment_id=experiment.id,
        turn_kind=ChatTurnKind.UNIVERSAL_CHAT,
        parent_message_id=user_msg.id,
    )
    db.add(assistant_msg)
    await db.flush()
    await set_active_leaf(db, thread.id, assistant_msg.id)
    await db.commit()
    await db.refresh(user_msg)
    await db.refresh(assistant_msg)

    _logger.info(
        "universal chat turn completed",
        experiment_id=str(experiment.id),
        thread_id=str(thread.id),
        current_act=project_context.current_act,
        history_turns=len(history),
    )

    return UniversalChatResult(
        user_message=user_msg,
        assistant_message=assistant_msg,
        thread_id=thread.id,
    )


async def list_universal_chat_messages(
    db: AsyncSession,
    current_user: User,
    experiment_id: UUID,
) -> UniversalChatMessages:
    """Return the active branch (root→leaf) for the universal thread.

    Empty / absent thread → thread_id/active_leaf None, empty messages.
    Includes tool_call / tool_result rows if present (future compatibility).

    Raises:
        UniversalChatNotFound: experiment not found / not owned.
    """
    exp_result = await db.execute(
        select(Experiment).where(Experiment.id == experiment_id)
    )
    experiment = exp_result.scalar_one_or_none()
    if experiment is None or experiment.user_id != current_user.id:
        raise UniversalChatNotFound("Experiment not found")

    if experiment.universal_thread_id is None:
        return UniversalChatMessages(
            thread_id=None,
            active_leaf_message_id=None,
            messages=[],
        )

    thread = await db.get(ChatThread, experiment.universal_thread_id)
    active_leaf_id = thread.active_leaf_message_id if thread is not None else None
    branch = await get_active_branch(db, experiment.universal_thread_id)

    return UniversalChatMessages(
        thread_id=experiment.universal_thread_id,
        active_leaf_message_id=active_leaf_id,
        messages=branch,
    )
