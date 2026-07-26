"""Universal chat service — canvas coach / agent surface.

Independent of chat_service.py and evidence_chat_service.py by design. Messages
carry ``turn_kind=UNIVERSAL_CHAT`` on an isolated ``experiments.universal_thread_id``
ChatThread so Refine and Evidence histories never mix.

v2 runs an Anthropic tool loop (``complete_with_tools``). Linear persistence:
user → tool_call → tool_result → … → assistant. Tool rows are non-branchable
children; ``content`` is a short label and data lives in ``tool_payload``.

Per AGENTS.md: project context, chat history, and tool results are untrusted
data. LLMCall cost logging happens inside llm_client (phase=universal_chat).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, cast
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
from app.services.universal_chat_tools import execute_tool, get_tool_schemas

_logger = get_logger(__name__)

_MAX_TOKENS = 1024
_TEMPERATURE = 0.7
# ~3k-token proxy. Drop oldest full user+assistant pairs until under budget.
_HISTORY_CHAR_BUDGET = 12000
# Max rounds that may execute tools; then one forced text-only call.
_MAX_TOOL_ROUNDS = 3

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
    # All rows created this turn, in order (user → tools → assistant).
    messages: list[ChatMessage]
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


def _tool_result_payload(
    tool_name: str,
    result: dict[str, Any],
) -> dict[str, Any]:
    if "error" in result and len(result) == 1:
        return {"tool_name": tool_name, "error": result["error"]}
    if "error" in result:
        return {"tool_name": tool_name, "error": result["error"], "result": result}
    return {"tool_name": tool_name, "result": result}


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


def _tool_result_content_json(payload: dict[str, Any]) -> str:
    if "error" in payload and "result" not in payload:
        return json.dumps({"error": payload["error"]})
    return json.dumps(payload.get("result", payload))


def _cap_round_tools_args(
    provider: str,
    *,
    force_text: bool,
    tool_schemas: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    """Return (tools, tool_choice) for this round, provider-specific on cap."""
    if not force_text:
        return tool_schemas, None
    if provider == "anthropic":
        # Anthropic rejects tool_choice without a tools list.
        return tool_schemas, {"type": "none"}
    if provider == "kimi":
        # OpenAI/Kimi: omit tools entirely to force a text answer.
        return [], None
    return tool_schemas, None


def _append_tool_followups(
    provider: str,
    api_messages: list[dict[str, Any]],
    *,
    assistant_turn: dict[str, Any],
    tool_uses: list[Any],
    result_contents: list[str],
) -> None:
    """Append provider-native assistant + tool-result turns to the in-memory messages."""
    api_messages.append(assistant_turn)
    if provider == "anthropic":
        blocks = [
            {
                "type": "tool_result",
                "tool_use_id": tool_use.id,
                "content": content,
            }
            for tool_use, content in zip(tool_uses, result_contents, strict=True)
        ]
        api_messages.append({"role": "user", "content": blocks})
        return
    if provider == "kimi":
        for tool_use, content in zip(tool_uses, result_contents, strict=True):
            api_messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_use.id,
                    "content": content,
                }
            )
        return
    raise ValueError(f"unsupported tool loop provider: {provider}")


async def send_universal_chat_message(
    db: AsyncSession,
    current_user: User,
    experiment_id: UUID,
    message: str,
) -> UniversalChatResult:
    """Send one universal-chat turn (tool loop) and persist rows.

    Creates ``universal_thread_id`` on first call. Linear parent chain only.
    Primary provider from settings; falls back to Anthropic only if the
    *initial* ``complete_with_tools`` call fails before any tool rows persist.

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

    turn_messages: list[ChatMessage] = [user_msg]
    chain_parent_id: UUID | None = user_msg.id

    seed_user_message: dict[str, Any] = {"role": "user", "content": user_prompt}
    api_messages: list[dict[str, Any]] = [dict(seed_user_message)]

    settings = get_settings()
    provider = settings.universal_chat_tools_provider
    model = settings.universal_chat_tools_model
    if provider not in ("anthropic", "kimi"):
        raise NotImplementedError(
            f"universal chat tools provider {provider!r} is not supported"
        )

    tool_schemas = get_tool_schemas(provider)
    tool_rounds = 0
    assistant_text = _FALLBACK_TEXT
    fallback_armed = True

    while True:
        force_text = tool_rounds >= _MAX_TOOL_ROUNDS
        tools_arg, tool_choice = _cap_round_tools_args(
            provider, force_text=force_text, tool_schemas=tool_schemas
        )

        try:
            result = await llm_client.complete_with_tools(
                db,
                provider=cast(Any, provider),
                model=model,
                prompt_name=PROMPT_NAME_UNIVERSAL_CHAT,
                system=UNIVERSAL_CHAT_SYSTEM_PROMPT,
                messages=api_messages,
                tools=tools_arg,
                tool_choice=tool_choice,
                max_tokens=_MAX_TOKENS,
                temperature=_TEMPERATURE,
                experiment_id=experiment.id,
                phase="universal_chat",
            )
        except Exception as exc:
            # Initial-call fallback only: no tool rows yet, not already on fallback.
            only_user_row = len(turn_messages) == 1
            if (
                fallback_armed
                and only_user_row
                and tool_rounds == 0
                and provider == settings.universal_chat_tools_provider
            ):
                _logger.warning(
                    "universal_chat_tool_fallback",
                    primary_provider=provider,
                    fallback_provider=settings.universal_chat_tools_fallback_provider,
                    error_type=type(exc).__name__,
                    experiment_id=str(experiment.id),
                )
                provider = settings.universal_chat_tools_fallback_provider
                model = settings.universal_chat_tools_fallback_model
                if provider not in ("anthropic", "kimi"):
                    raise
                tool_schemas = get_tool_schemas(provider)
                api_messages = [dict(seed_user_message)]
                fallback_armed = False
                continue
            raise

        if result.tool_uses and not force_text:
            tool_rounds += 1
            result_contents: list[str] = []

            for tool_use in result.tool_uses:
                tool_call_msg = ChatMessage(
                    thread_id=thread.id,
                    role=ChatRole.TOOL_CALL,
                    content=f"Called: {tool_use.name}",
                    experiment_id=experiment.id,
                    turn_kind=ChatTurnKind.UNIVERSAL_CHAT,
                    parent_message_id=chain_parent_id,
                    tool_payload={
                        "tool_name": tool_use.name,
                        "arguments": tool_use.input,
                    },
                )
                db.add(tool_call_msg)
                await db.flush()
                turn_messages.append(tool_call_msg)
                chain_parent_id = tool_call_msg.id

                exec_result = await execute_tool(
                    tool_use.name,
                    tool_use.input,
                    db,
                    experiment,
                )
                payload = _tool_result_payload(tool_use.name, exec_result)
                tool_result_msg = ChatMessage(
                    thread_id=thread.id,
                    role=ChatRole.TOOL_RESULT,
                    content="Result received",
                    experiment_id=experiment.id,
                    turn_kind=ChatTurnKind.UNIVERSAL_CHAT,
                    parent_message_id=chain_parent_id,
                    tool_payload=payload,
                )
                db.add(tool_result_msg)
                await db.flush()
                turn_messages.append(tool_result_msg)
                chain_parent_id = tool_result_msg.id
                result_contents.append(_tool_result_content_json(payload))

            _append_tool_followups(
                provider,
                api_messages,
                assistant_turn=result.assistant_turn,
                tool_uses=result.tool_uses,
                result_contents=result_contents,
            )
            continue

        assistant_text = (result.assistant_text or "").strip() or _FALLBACK_TEXT
        break

    assistant_msg = ChatMessage(
        thread_id=thread.id,
        role=ChatRole.ASSISTANT,
        content=assistant_text,
        experiment_id=experiment.id,
        turn_kind=ChatTurnKind.UNIVERSAL_CHAT,
        parent_message_id=chain_parent_id,
    )
    db.add(assistant_msg)
    await db.flush()
    turn_messages.append(assistant_msg)
    await set_active_leaf(db, thread.id, assistant_msg.id)
    await db.commit()

    for msg in turn_messages:
        await db.refresh(msg)

    _logger.info(
        "universal chat turn completed",
        experiment_id=str(experiment.id),
        thread_id=str(thread.id),
        current_act=project_context.current_act,
        history_turns=len(history),
        tool_rounds=tool_rounds,
        turn_message_count=len(turn_messages),
        provider=provider,
    )

    return UniversalChatResult(
        user_message=user_msg,
        assistant_message=assistant_msg,
        messages=turn_messages,
        thread_id=thread.id,
    )


async def list_universal_chat_messages(
    db: AsyncSession,
    current_user: User,
    experiment_id: UUID,
) -> UniversalChatMessages:
    """Return the active branch (root→leaf) for the universal thread.

    Empty / absent thread → thread_id/active_leaf None, empty messages.
    Includes tool_call / tool_result rows if present.

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
