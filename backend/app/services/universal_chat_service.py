"""Universal chat service — canvas coach / agent surface.

Independent of chat_service.py and evidence_chat_service.py by design. Messages
carry ``turn_kind=UNIVERSAL_CHAT`` on an isolated ``experiments.universal_thread_id``
ChatThread so Refine and Evidence histories never mix.

v2 runs an Anthropic tool loop (``complete_with_tools``). Linear persistence:
user → tool_call → tool_result → … → assistant. Tool rows are non-branchable
children; ``content`` is a short label and data lives in ``tool_payload``.

Streaming (``stream_universal_chat_message``): user row committed in prepare;
the turn body runs in a detached ``asyncio.create_task`` (own sessionmaker,
ADR 0009-style). SSE observes an in-process event fan-out — disconnect does
not cancel the task. Explicit ``cancel_universal_turn`` stops it. tool_call /
tool_result commit as they happen (and advance ``active_leaf``); assistant on
success. ``metadata_json.turn_status`` on the turn anchor tracks running/done/failed.

Per AGENTS.md: project context, chat history, and tool results are untrusted
data. LLMCall cost logging happens inside llm_client (phase=universal_chat).
"""

from __future__ import annotations

import asyncio
import contextlib
import json
from collections.abc import AsyncGenerator
from dataclasses import dataclass
from typing import Any, cast
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import app.llm.client as llm_client
from app.config import get_settings
from app.db.enums import ChatRole, ChatTurnKind, ExperimentStatus
from app.db.models.chat_message import ChatMessage
from app.db.models.chat_thread import ChatThread
from app.db.models.experiment import Experiment
from app.db.models.user import User
from app.db.session import get_sessionmaker
from app.llm.prompts.universal_chat import (
    PROMPT_NAME_UNIVERSAL_CHAT,
    UNIVERSAL_CHAT_SYSTEM_PROMPT,
    build_universal_chat_user_prompt,
)
from app.logging_config import get_logger
from app.services.chat_tree_service import (
    get_active_branch,
    get_branch_up_to,
    set_active_leaf,
)
from app.services.chat_attachment_service import (
    build_message_with_attachment_context,
    resolve_chat_attachments,
)
from app.services.experiment_project_context import get_experiment_project_context
from app.services.universal_chat_tools import execute_tool, get_tool_schemas
from app.services.universal_chat_turn_runtime import (
    TURN_ID_KEY,
    TURN_STATUS_DONE,
    TURN_STATUS_FAILED,
    TURN_STATUS_KEY,
    TURN_STATUS_RUNNING,
    UniversalTurnRuntime,
    close_turn_runtime,
    publish_turn_event,
    register_turn_runtime,
    request_turn_cancel,
    subscribe_turn_events,
    unsubscribe_turn_events,
)

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

_TOOL_REFINE = "ask_refine_agent"

# Default pacing for refine / master final text fake-streams.
_DEFAULT_PACING_DELAY_S = 0.03
# Small groups so short answers still visibly stream (same path as long ones).
_CHUNK_WORD_SIZES = (1, 2, 2, 3, 3, 4)


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
    in_progress_turn_id: UUID | None = None


@dataclass(frozen=True)
class UniversalStreamPrep:
    """Request-session prep: user row committed before the turn task starts."""

    experiment_id: UUID
    user_id: UUID
    thread_id: UUID
    user_message_id: UUID | None
    user_prompt: str
    clean_message: str
    provider: str
    model: str
    fallback_provider: str
    fallback_model: str
    turn_id: UUID
    # Message whose metadata_json holds turn_status (user row, or MCQ parent).
    status_message_id: UUID | None
    pacing_delay: float = _DEFAULT_PACING_DELAY_S
    # Exact rail MCQ click — injected into ask_refine_agent once (skips resolver).
    mcq_answer: dict[str, Any] | None = None
    # Card selection/skip: no new USER row in the universal thread (no echo bubble).
    suppress_user_echo: bool = False
    # Agent-initiated post-capture refine handoff (forces ask_refine_agent).
    kick: str | None = None


def _merge_turn_metadata(
    existing: dict[str, Any] | None,
    *,
    turn_id: UUID,
    turn_status: str,
) -> dict[str, Any]:
    meta = dict(existing or {})
    meta[TURN_ID_KEY] = str(turn_id)
    meta[TURN_STATUS_KEY] = turn_status
    return meta


async def _set_turn_status(
    db: AsyncSession,
    message_id: UUID | None,
    *,
    turn_id: UUID,
    status: str,
) -> None:
    if message_id is None:
        return
    row = await db.get(ChatMessage, message_id)
    if row is None:
        return
    row.metadata_json = _merge_turn_metadata(
        row.metadata_json if isinstance(row.metadata_json, dict) else None,
        turn_id=turn_id,
        turn_status=status,
    )
    await db.flush()


def _in_progress_turn_id_from_messages(messages: list[ChatMessage]) -> UUID | None:
    for msg in reversed(messages):
        meta = msg.metadata_json if isinstance(msg.metadata_json, dict) else None
        if not meta or meta.get(TURN_STATUS_KEY) != TURN_STATUS_RUNNING:
            continue
        raw = meta.get(TURN_ID_KEY)
        if isinstance(raw, str) and raw:
            try:
                return UUID(raw)
            except ValueError:
                return msg.id
        return msg.id
    return None


def _raise_if_turn_cancelled(cancel: asyncio.Event | None) -> None:
    if cancel is not None and cancel.is_set():
        raise asyncio.CancelledError()


async def _await_unless_cancelled(
    awaitable: Any,
    cancel: asyncio.Event | None,
) -> Any:
    """Await ``awaitable``, but abort promptly when ``cancel`` is set."""
    if cancel is None:
        return await awaitable
    work = asyncio.ensure_future(awaitable)
    stopper = asyncio.ensure_future(cancel.wait())
    try:
        done, pending = await asyncio.wait(
            {work, stopper},
            return_when=asyncio.FIRST_COMPLETED,
        )
        for task in pending:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task
        if stopper in done and cancel.is_set():
            raise asyncio.CancelledError()
        return work.result()
    finally:
        if not work.done():
            work.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await work
        if not stopper.done():
            stopper.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await stopper


def _sanitize(message: str) -> str:
    return message.strip()


def _display_content_for_attachments(
    clean_message: str,
    filenames: list[str],
) -> str:
    """Visible user-bubble text. Attachment chips render from metadata_json."""
    if clean_message:
        return clean_message
    if filenames:
        return "Shared attachments"
    return ""


async def _prepare_attachment_turn(
    db: AsyncSession,
    *,
    user: User,
    message: str,
    attachment_ids: list[UUID],
    allow_consumed_attachments: bool = False,
) -> tuple[str, str, dict[str, Any] | None]:
    """Resolve uploads and build display text, LLM text, and metadata.

    Reuses the extract-to-text pipeline from ``chat_service`` /
    ``chat_attachment_service`` (no multimodal blocks).
    """
    clean_message = _sanitize(message)
    attachments = await resolve_chat_attachments(
        db,
        user=user,
        attachment_ids=attachment_ids,
        allow_consumed=allow_consumed_attachments,
    )
    filenames = [item.filename for item in attachments]
    display = _display_content_for_attachments(clean_message, filenames)
    llm_message = build_message_with_attachment_context(clean_message, attachments)
    if not display:
        raise ValueError("message or attachment_ids is required")

    metadata: dict[str, Any] | None = None
    if attachments:
        metadata = {
            "attachments": [
                {
                    "id": str(item.id),
                    "filename": item.filename,
                    "content_kind": item.content_kind,
                }
                for item in attachments
            ]
        }
    return display, llm_message, metadata


async def _resolve_edit_parent(
    db: AsyncSession,
    *,
    thread: ChatThread,
    replace_message_id: UUID | None,
) -> tuple[UUID | None, bool]:
    """Return (parent_id for new USER row, is_edit).

    Edit forks a sibling of ``replace_message_id`` (same parent). Append uses
    the thread's active leaf.
    """
    if replace_message_id is None:
        return thread.active_leaf_message_id, False
    old = await db.get(ChatMessage, replace_message_id)
    if (
        old is None
        or old.thread_id != thread.id
        or old.role != ChatRole.USER
    ):
        raise ValueError("replace_message_id is not a user message in this thread")
    return old.parent_message_id, True


async def iter_paced_text_chunks(
    text: str,
    *,
    pacing_delay: float = _DEFAULT_PACING_DELAY_S,
    cancel: asyncio.Event | None = None,
) -> AsyncGenerator[str, None]:
    """Yield word-boundary chunks with optional pacing (refine / master final).

    Splits on whitespace into 3–8 word groups. Tests pass ``pacing_delay=0``.
    """
    cleaned = text.strip()
    if not cleaned:
        return
    words = cleaned.split()
    if not words:
        _raise_if_turn_cancelled(cancel)
        yield cleaned
        return
    i = 0
    size_idx = 0
    while i < len(words):
        _raise_if_turn_cancelled(cancel)
        n = _CHUNK_WORD_SIZES[size_idx % len(_CHUNK_WORD_SIZES)]
        size_idx += 1
        chunk_words = words[i : i + n]
        i += n
        chunk = " ".join(chunk_words)
        if i < len(words):
            chunk += " "
        yield chunk
        if pacing_delay > 0:
            await asyncio.sleep(pacing_delay)


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


def _ensure_original_idea_captured(experiment: Experiment) -> None:
    """Block agent turns until the write-once original idea is captured."""
    if experiment.original_idea is None:
        raise UniversalChatUnavailable(
            "Capture your original idea before chatting with the agent."
        )


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


def _mcq_answer_as_dict(mcq_answer: Any) -> dict[str, Any] | None:
    """Normalize UniversalMcqAnswer / dict into executor-injectable payload."""
    if mcq_answer is None:
        return None
    if hasattr(mcq_answer, "model_dump"):
        dumped = mcq_answer.model_dump(mode="json")
        return {
            "selected_option_indices": list(dumped.get("selected_option_indices") or []),
            "answered_question_id": str(dumped["answered_question_id"]),
            "skipped": bool(dumped.get("skipped")),
        }
    if isinstance(mcq_answer, dict):
        indices = mcq_answer.get("selected_option_indices") or []
        qid = mcq_answer.get("answered_question_id")
        if qid is None:
            return None
        return {
            "selected_option_indices": list(indices),
            "answered_question_id": str(qid),
            "skipped": bool(mcq_answer.get("skipped")),
        }
    return None


def _inject_mcq_into_tool_args(
    tool_name: str,
    args: dict[str, Any] | None,
    mcq_answer: dict[str, Any] | None,
) -> dict[str, Any]:
    merged = dict(args or {})
    if tool_name == _TOOL_REFINE and mcq_answer is not None:
        merged["_mcq_answer"] = mcq_answer
    return merged


def _synthetic_mcq_assistant_turn(
    provider: str,
    tool_use: llm_client.ToolUseRequest,
) -> dict[str, Any]:
    if provider == "anthropic":
        return {
            "role": "assistant",
            "content": [
                {
                    "type": "tool_use",
                    "id": tool_use.id,
                    "name": tool_use.name,
                    "input": tool_use.input,
                }
            ],
        }
    if provider == "kimi":
        return {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": tool_use.id,
                    "type": "function",
                    "function": {
                        "name": tool_use.name,
                        "arguments": json.dumps(tool_use.input),
                    },
                }
            ],
        }
    raise ValueError(f"unsupported tool loop provider: {provider}")


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
    *,
    attachment_ids: list[UUID] | None = None,
    current_open_phase: str | None = None,
    mcq_answer: Any = None,
) -> UniversalChatResult:
    """Send one universal-chat turn (tool loop) and persist rows.

    Creates ``universal_thread_id`` on first call. Linear parent chain only.
    Primary provider from settings; falls back to Anthropic only if the
    *initial* ``complete_with_tools`` call fails before any tool rows persist.

    Raises:
        UniversalChatNotFound: experiment not found / not owned.
        UniversalChatUnavailable: archived experiment.
        ValueError: message empty after sanitization (and no attachments).
        ChatAttachmentValidationError / ChatAttachmentAccessError: bad uploads.
        LLM provider errors propagate (mapped to 502 by the router).
    """
    ids = list(attachment_ids or [])
    display_content, llm_message, attachment_meta = await _prepare_attachment_turn(
        db,
        user=current_user,
        message=message,
        attachment_ids=ids,
    )
    clean_message = _sanitize(message)

    mcq_inject = _mcq_answer_as_dict(mcq_answer)

    experiment = await _load_owned_experiment(db, current_user, experiment_id)
    _ensure_original_idea_captured(experiment)
    thread = await _resolve_universal_thread(db, current_user, experiment)

    parent_id = thread.active_leaf_message_id
    history = await get_active_branch(db, thread.id) if parent_id is not None else []

    project_context = await get_experiment_project_context(
        db, experiment, current_open_phase=current_open_phase
    )
    user_prompt = build_universal_chat_user_prompt(
        project_context=project_context.to_prompt_block(),
        chat_history=_history_for_prompt(history),
        user_message=llm_message,
    )

    user_msg = ChatMessage(
        thread_id=thread.id,
        role=ChatRole.USER,
        content=display_content,
        experiment_id=experiment.id,
        turn_kind=ChatTurnKind.UNIVERSAL_CHAT,
        parent_message_id=parent_id,
        metadata_json=attachment_meta,
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
    mcq_forced = False

    while True:
        if mcq_inject is not None and not mcq_forced:
            mcq_forced = True
            tool_rounds += 1
            tool_use = llm_client.ToolUseRequest(
                id=f"mcq-click-{user_msg.id}",
                name=_TOOL_REFINE,
                input={"query": clean_message or display_content},
            )
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

            exec_args = _inject_mcq_into_tool_args(
                tool_use.name, tool_use.input, mcq_inject
            )
            mcq_inject = None
            exec_result = await execute_tool(
                tool_use.name,
                exec_args,
                db,
                experiment,
                user=current_user,
            )
            refreshed = await db.get(Experiment, experiment.id)
            if refreshed is not None:
                experiment = refreshed
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
            _append_tool_followups(
                provider,
                api_messages,
                assistant_turn=_synthetic_mcq_assistant_turn(provider, tool_use),
                tool_uses=[tool_use],
                result_contents=[_tool_result_content_json(payload)],
            )
            continue

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
            end_after_refine = False
            refine_text = ""

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

                exec_args = _inject_mcq_into_tool_args(
                    tool_use.name, tool_use.input, mcq_inject
                )
                if tool_use.name == _TOOL_REFINE and mcq_inject is not None:
                    mcq_inject = None
                exec_result = await execute_tool(
                    tool_use.name,
                    exec_args,
                    db,
                    experiment,
                    user=current_user,
                )
                payload = _tool_result_payload(tool_use.name, exec_result)
                if tool_use.name == _TOOL_REFINE and "error" not in payload:
                    end_after_refine = True
                    if isinstance(exec_result.get("assistant_text"), str):
                        refine_text = exec_result["assistant_text"].strip()
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

            if end_after_refine:
                assistant_text = refine_text
                break

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

    if assistant_text:
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
    elif chain_parent_id is not None:
        await set_active_leaf(db, thread.id, chain_parent_id)
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
        has_assistant_text=bool(assistant_text),
    )

    # Non-stream callers historically always received an assistant message.
    # Refine MCQ-only turns may have none — synthesize a stub for the result type.
    if not assistant_text:
        assistant_msg = ChatMessage(
            thread_id=thread.id,
            role=ChatRole.ASSISTANT,
            content="",
            experiment_id=experiment.id,
            turn_kind=ChatTurnKind.UNIVERSAL_CHAT,
            parent_message_id=chain_parent_id,
        )
        # Not persisted — result envelope only for type compatibility.
        turn_messages.append(assistant_msg)

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
            in_progress_turn_id=None,
        )

    thread = await db.get(ChatThread, experiment.universal_thread_id)
    active_leaf_id = thread.active_leaf_message_id if thread is not None else None
    branch = await get_active_branch(db, experiment.universal_thread_id)

    return UniversalChatMessages(
        thread_id=experiment.universal_thread_id,
        active_leaf_message_id=active_leaf_id,
        messages=branch,
        in_progress_turn_id=_in_progress_turn_id_from_messages(branch),
    )


async def prepare_universal_stream(
    db: AsyncSession,
    current_user: User,
    experiment_id: UUID,
    message: str,
    *,
    attachment_ids: list[UUID] | None = None,
    pacing_delay: float = _DEFAULT_PACING_DELAY_S,
    current_open_phase: str | None = None,
    mcq_answer: Any = None,
    replace_message_id: UUID | None = None,
    kick: str | None = None,
) -> UniversalStreamPrep:
    """Persist + commit the user row before the SSE generator starts.

    Mirrors evidence-chat prepare: mid-stream disconnect never loses the user
    message; active leaf points at the user until the assistant lands.

    Card MCQ selections (structured ``mcq_answer``) do **not** create a new
    USER row — the answer stays invisible in the rail and attaches under the
    existing active leaf. Attachment IDs are ignored on that path.

    ``kick="post_capture_refine"`` is agent-initiated after idea capture: no
    new USER row; forces ``ask_refine_agent`` on the frozen original idea.

    ``replace_message_id`` forks the active branch (message edit): history is
    the chain up to that message's parent; the new USER row becomes the leaf.
    """
    mcq_inject = _mcq_answer_as_dict(mcq_answer)
    kick_refine = kick == "post_capture_refine"
    suppress_user_echo = mcq_inject is not None or kick_refine
    # MCQ / kick clicks are invisible — do not consume / inject attachments.
    ids = [] if suppress_user_echo else list(attachment_ids or [])

    experiment = await _load_owned_experiment(db, current_user, experiment_id)
    _ensure_original_idea_captured(experiment)
    thread = await _resolve_universal_thread(db, current_user, experiment)

    if suppress_user_echo:
        parent_id = thread.active_leaf_message_id
        is_edit = False
    else:
        parent_id, is_edit = await _resolve_edit_parent(
            db, thread=thread, replace_message_id=replace_message_id
        )

    if kick_refine:
        original = (experiment.original_idea or "").strip()
        clean_message = (
            "The founder just sealed their original idea. Pressure-test it now: "
            "ask one sharp clarifying question via ask_refine_agent.\n\n"
            f"<original_idea>\n{original}\n</original_idea>"
        )
        display_content = clean_message
        llm_message = clean_message
        attachment_meta = None
    else:
        display_content, llm_message, attachment_meta = await _prepare_attachment_turn(
            db,
            user=current_user,
            message=message,
            attachment_ids=ids,
            allow_consumed_attachments=is_edit,
        )
        clean_message = _sanitize(message)

    if parent_id is not None:
        history = await get_branch_up_to(db, parent_id)
    else:
        history = []

    project_context = await get_experiment_project_context(
        db, experiment, current_open_phase=current_open_phase
    )
    user_prompt = build_universal_chat_user_prompt(
        project_context=project_context.to_prompt_block(),
        chat_history=_history_for_prompt(history),
        user_message=llm_message,
    )

    user_message_id: UUID | None = parent_id
    turn_id = uuid4()
    status_message_id: UUID | None = None
    if not suppress_user_echo:
        turn_meta = _merge_turn_metadata(
            attachment_meta,
            turn_id=turn_id,
            turn_status=TURN_STATUS_RUNNING,
        )
        user_msg = ChatMessage(
            thread_id=thread.id,
            role=ChatRole.USER,
            content=display_content,
            experiment_id=experiment.id,
            turn_kind=ChatTurnKind.UNIVERSAL_CHAT,
            parent_message_id=parent_id,
            metadata_json=turn_meta,
        )
        db.add(user_msg)
        await db.flush()
        await set_active_leaf(db, thread.id, user_msg.id)
        await db.commit()
        await db.refresh(user_msg)
        user_message_id = user_msg.id
        status_message_id = user_msg.id
    else:
        status_message_id = parent_id
        if parent_id is not None:
            await _set_turn_status(
                db,
                parent_id,
                turn_id=turn_id,
                status=TURN_STATUS_RUNNING,
            )
        await db.commit()

    settings = get_settings()
    return UniversalStreamPrep(
        experiment_id=experiment.id,
        user_id=current_user.id,
        thread_id=thread.id,
        user_message_id=user_message_id,
        user_prompt=user_prompt,
        clean_message=clean_message or display_content,
        provider=settings.universal_chat_tools_provider,
        model=settings.universal_chat_tools_model,
        fallback_provider=settings.universal_chat_tools_fallback_provider,
        fallback_model=settings.universal_chat_tools_fallback_model,
        turn_id=turn_id,
        status_message_id=status_message_id,
        pacing_delay=pacing_delay,
        mcq_answer=mcq_inject,
        suppress_user_echo=suppress_user_echo,
        kick=kick if kick_refine else None,
    )


def start_universal_turn(prep: UniversalStreamPrep) -> UniversalTurnRuntime:
    """Kick off the detached turn task (idempotent per turn_id)."""
    existing = register_turn_runtime(
        turn_id=prep.turn_id,
        experiment_id=prep.experiment_id,
        thread_id=prep.thread_id,
        status_message_id=prep.status_message_id,
    )
    if existing.task is not None and not existing.task.done():
        return existing

    def _on_done(task: asyncio.Task[None]) -> None:
        if task.cancelled():
            return
        exc = task.exception()
        if exc is not None:
            _logger.warning(
                "universal chat turn task crashed",
                turn_id=str(prep.turn_id),
                error_type=type(exc).__name__,
            )

    existing.task = asyncio.create_task(
        _run_universal_turn_task(prep, existing),
        name=f"universal_chat_turn_{prep.turn_id}",
    )
    existing.task.add_done_callback(_on_done)
    return existing


async def _run_universal_turn_task(
    prep: UniversalStreamPrep,
    runtime: UniversalTurnRuntime,
) -> None:
    """Background worker: own sessionmaker path via _iter_universal_turn_events."""
    try:
        async for event_name, payload in _iter_universal_turn_events(
            prep, cancel=runtime.cancel
        ):
            if event_name.startswith("_"):
                continue
            await publish_turn_event(runtime, event_name, payload)
    except asyncio.CancelledError:
        _logger.info(
            "universal chat turn cancelled",
            turn_id=str(prep.turn_id),
            experiment_id=str(prep.experiment_id),
        )
        # Swallow — task should finish cleanly after status=failed is written.
    except Exception as exc:
        _logger.error(
            "universal chat turn task failed",
            turn_id=str(prep.turn_id),
            error_type=type(exc).__name__,
            exc_info=exc,
        )
    finally:
        await close_turn_runtime(runtime)


async def stream_universal_chat_message(
    prep: UniversalStreamPrep,
) -> AsyncGenerator[tuple[str, dict[str, Any]], None]:
    """Observe a detached turn (SSE live view). Disconnect does not cancel work.

    Yields ``turn_started``, ``tool_call``, ``tool_result``, ``assistant_token``,
    ``done``, ``error``.
    """
    runtime = start_universal_turn(prep)
    yield (
        "turn_started",
        {
            "turn_id": str(prep.turn_id),
            "user_message_id": (
                str(prep.user_message_id)
                if prep.user_message_id and not prep.suppress_user_echo
                else None
            ),
            "thread_id": str(prep.thread_id),
        },
    )
    queue = await subscribe_turn_events(runtime)
    try:
        while True:
            item = await queue.get()
            if item is None:
                break
            yield item
    except (asyncio.CancelledError, GeneratorExit):
        _logger.info(
            "universal chat SSE observer cancelled",
            turn_id=str(prep.turn_id),
            experiment_id=str(prep.experiment_id),
        )
        raise
    finally:
        await unsubscribe_turn_events(runtime, queue)


async def cancel_universal_turn(
    db: AsyncSession,
    current_user: User,
    experiment_id: UUID,
    turn_id: UUID,
) -> bool:
    """Explicit stop: signal in-process task (reload must NOT call this)."""
    await _load_owned_experiment(db, current_user, experiment_id)
    return request_turn_cancel(turn_id)


async def _iter_universal_turn_events(
    prep: UniversalStreamPrep,
    *,
    cancel: asyncio.Event | None = None,
) -> AsyncGenerator[tuple[str, dict[str, Any]], None]:
    """Turn body (tool loop + final text). Runs inside the detached task.
    """
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        user = await db.get(User, prep.user_id)
        experiment = await db.get(Experiment, prep.experiment_id)
        if user is None or experiment is None:
            await _set_turn_status(
                db,
                prep.status_message_id,
                turn_id=prep.turn_id,
                status=TURN_STATUS_FAILED,
            )
            await db.commit()
            yield ("error", {"message": "Universal chat failed, please try again"})
            return

        seed_user_message: dict[str, Any] = {
            "role": "user",
            "content": prep.user_prompt,
        }
        api_messages: list[dict[str, Any]] = [dict(seed_user_message)]
        chain_parent_id: UUID | None = prep.user_message_id

        provider = prep.provider
        model = prep.model
        if provider not in ("anthropic", "kimi"):
            await _set_turn_status(
                db,
                prep.status_message_id,
                turn_id=prep.turn_id,
                status=TURN_STATUS_FAILED,
            )
            await db.commit()
            yield ("error", {"message": "Universal chat failed, please try again"})
            return

        tool_schemas = get_tool_schemas(provider)
        tool_rounds = 0
        fallback_armed = True
        assistant_text = _FALLBACK_TEXT
        skip_master_final = False
        refine_already_streamed = False
        mcq_inject = dict(prep.mcq_answer) if prep.mcq_answer else None
        mcq_forced = False
        kick_forced = False

        try:
            while True:
                _raise_if_turn_cancelled(cancel)
                if prep.kick == "post_capture_refine" and not kick_forced:
                    kick_forced = True
                    tool_rounds += 1
                    tool_use = llm_client.ToolUseRequest(
                        id=f"capture-refine-{prep.turn_id}",
                        name=_TOOL_REFINE,
                        input={"query": prep.clean_message},
                    )
                    tool_call_msg = ChatMessage(
                        thread_id=prep.thread_id,
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
                    await set_active_leaf(db, prep.thread_id, tool_call_msg.id)
                    await db.commit()
                    chain_parent_id = tool_call_msg.id
                    yield (
                        "tool_call",
                        {
                            "tool_name": tool_use.name,
                            "message_id": str(tool_call_msg.id),
                        },
                    )
                    in_flight_tool_result_id: UUID | None = None
                    refine_owned = False
                    refine_text = ""
                    try:
                        async for evt in _stream_refine_tool(
                            db,
                            experiment,
                            user,
                            tool_use,
                            prep,
                            chain_parent_id,
                            mcq_answer=None,
                            cancel=cancel,
                        ):
                            if evt[0] == "_refine_outcome":
                                refine_owned = bool(evt[1].get("ok"))
                                refine_text = str(evt[1].get("assistant_text") or "")
                                if evt[1].get("already_streamed"):
                                    refine_already_streamed = True
                            elif evt[0] == "_chain_parent":
                                chain_parent_id = evt[1]["id"]  # type: ignore[index]
                                result_content = evt[1]["content_json"]
                                in_flight_tool_result_id = None
                                _append_tool_followups(
                                    provider,
                                    api_messages,
                                    assistant_turn=_synthetic_mcq_assistant_turn(
                                        provider, tool_use
                                    ),
                                    tool_uses=[tool_use],
                                    result_contents=[result_content],
                                )
                            elif evt[0] == "_in_flight_tool_result":
                                in_flight_tool_result_id = evt[1]["id"]
                            else:
                                yield evt
                    except (asyncio.CancelledError, GeneratorExit):
                        await _delete_in_flight_tool_result(
                            db, in_flight_tool_result_id
                        )
                        raise
                    refreshed = await db.get(Experiment, experiment.id)
                    if refreshed is not None:
                        experiment = refreshed
                    if refine_owned:
                        skip_master_final = True
                        assistant_text = refine_text
                        break
                    continue

                if mcq_inject is not None and not mcq_forced:
                    mcq_forced = True
                    tool_rounds += 1
                    tool_use = llm_client.ToolUseRequest(
                        id=f"mcq-click-{prep.user_message_id or prep.thread_id}",
                        name=_TOOL_REFINE,
                        input={"query": prep.clean_message},
                    )
                    tool_call_msg = ChatMessage(
                        thread_id=prep.thread_id,
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
                    await set_active_leaf(db, prep.thread_id, tool_call_msg.id)
                    await db.commit()
                    chain_parent_id = tool_call_msg.id
                    yield (
                        "tool_call",
                        {
                            "tool_name": tool_use.name,
                            "message_id": str(tool_call_msg.id),
                        },
                    )
                    in_flight_tool_result_id: UUID | None = None
                    refine_owned = False
                    refine_text = ""
                    try:
                        async for evt in _stream_refine_tool(
                            db,
                            experiment,
                            user,
                            tool_use,
                            prep,
                            chain_parent_id,
                            mcq_answer=mcq_inject,
                            cancel=cancel,
                        ):
                            if evt[0] == "_refine_outcome":
                                refine_owned = bool(evt[1].get("ok"))
                                refine_text = str(evt[1].get("assistant_text") or "")
                                if evt[1].get("already_streamed"):
                                    refine_already_streamed = True
                            elif evt[0] == "_chain_parent":
                                chain_parent_id = evt[1]["id"]  # type: ignore[index]
                                result_content = evt[1]["content_json"]
                                in_flight_tool_result_id = None
                                _append_tool_followups(
                                    provider,
                                    api_messages,
                                    assistant_turn=_synthetic_mcq_assistant_turn(
                                        provider, tool_use
                                    ),
                                    tool_uses=[tool_use],
                                    result_contents=[result_content],
                                )
                            elif evt[0] == "_in_flight_tool_result":
                                in_flight_tool_result_id = evt[1]["id"]
                            else:
                                yield evt
                    except (asyncio.CancelledError, GeneratorExit):
                        await _delete_in_flight_tool_result(
                            db, in_flight_tool_result_id
                        )
                        raise
                    mcq_inject = None
                    refreshed = await db.get(Experiment, experiment.id)
                    if refreshed is not None:
                        experiment = refreshed
                    if refine_owned:
                        skip_master_final = True
                        assistant_text = refine_text
                        break
                    continue

                force_text = tool_rounds >= _MAX_TOOL_ROUNDS
                tools_arg, tool_choice = _cap_round_tools_args(
                    provider, force_text=force_text, tool_schemas=tool_schemas
                )

                _raise_if_turn_cancelled(cancel)
                try:
                    result = await _await_unless_cancelled(
                        llm_client.complete_with_tools(
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
                        ),
                        cancel,
                    )
                except Exception as exc:
                    only_user = (
                        not prep.suppress_user_echo
                        and chain_parent_id == prep.user_message_id
                    )
                    if (
                        fallback_armed
                        and only_user
                        and tool_rounds == 0
                        and provider == prep.provider
                    ):
                        _logger.warning(
                            "universal_chat_stream_tool_fallback",
                            primary_provider=provider,
                            fallback_provider=prep.fallback_provider,
                            error_type=type(exc).__name__,
                            experiment_id=str(experiment.id),
                        )
                        provider = prep.fallback_provider
                        model = prep.fallback_model
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
                    in_flight_tool_result_id = None
                    end_after_refine = False
                    refine_text = ""

                    for tool_use in result.tool_uses:
                        tool_call_msg = ChatMessage(
                            thread_id=prep.thread_id,
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
                        await set_active_leaf(db, prep.thread_id, tool_call_msg.id)
                        await db.commit()
                        chain_parent_id = tool_call_msg.id
                        yield (
                            "tool_call",
                            {
                                "tool_name": tool_use.name,
                                "message_id": str(tool_call_msg.id),
                            },
                        )

                        if tool_use.name == _TOOL_REFINE:
                            refine_mcq = mcq_inject
                            if refine_mcq is not None:
                                mcq_inject = None
                            try:
                                async for evt in _stream_refine_tool(
                                    db,
                                    experiment,
                                    user,
                                    tool_use,
                                    prep,
                                    chain_parent_id,
                                    mcq_answer=refine_mcq,
                                    cancel=cancel,
                                ):
                                    if evt[0] == "_refine_outcome":
                                        if evt[1].get("ok"):
                                            end_after_refine = True
                                            refine_text = str(
                                                evt[1].get("assistant_text") or ""
                                            )
                                            if evt[1].get("already_streamed"):
                                                refine_already_streamed = True
                                    elif evt[0] == "_chain_parent":
                                        chain_parent_id = evt[1]["id"]  # type: ignore[index]
                                        result_contents.append(
                                            evt[1]["content_json"]
                                        )
                                        in_flight_tool_result_id = None
                                    elif evt[0] == "_in_flight_tool_result":
                                        in_flight_tool_result_id = evt[1]["id"]
                                    else:
                                        yield evt
                            except (asyncio.CancelledError, GeneratorExit):
                                await _delete_in_flight_tool_result(
                                    db, in_flight_tool_result_id
                                )
                                raise
                            refreshed = await db.get(Experiment, experiment.id)
                            if refreshed is not None:
                                experiment = refreshed
                            # Keep going so open_phase_panel in the same round still runs.
                            continue

                        exec_result = await _await_unless_cancelled(
                            execute_tool(
                                tool_use.name,
                                tool_use.input,
                                db,
                                experiment,
                                user=user,
                            ),
                            cancel,
                        )
                        refreshed = await db.get(Experiment, experiment.id)
                        if refreshed is not None:
                            experiment = refreshed

                        payload = _tool_result_payload(tool_use.name, exec_result)
                        tool_result_msg = ChatMessage(
                            thread_id=prep.thread_id,
                            role=ChatRole.TOOL_RESULT,
                            content="Result received",
                            experiment_id=experiment.id,
                            turn_kind=ChatTurnKind.UNIVERSAL_CHAT,
                            parent_message_id=chain_parent_id,
                            tool_payload=payload,
                        )
                        db.add(tool_result_msg)
                        await db.flush()
                        await set_active_leaf(db, prep.thread_id, tool_result_msg.id)
                        await db.commit()
                        chain_parent_id = tool_result_msg.id
                        content_json = _tool_result_content_json(payload)
                        result_contents.append(content_json)
                        yield (
                            "tool_result",
                            {
                                "tool_name": tool_use.name,
                                "message_id": str(tool_result_msg.id),
                                "payload": payload,
                            },
                        )

                    if end_after_refine:
                        # Refine owned the turn — do not call the master again.
                        skip_master_final = True
                        assistant_text = refine_text
                        break

                    _append_tool_followups(
                        provider,
                        api_messages,
                        assistant_turn=result.assistant_turn,
                        tool_uses=result.tool_uses,
                        result_contents=result_contents,
                    )
                    continue

                assistant_text = (
                    (result.assistant_text or "").strip() or _FALLBACK_TEXT
                )
                break

            if assistant_text:
                if not refine_already_streamed:
                    async for chunk in iter_paced_text_chunks(
                        assistant_text,
                        pacing_delay=prep.pacing_delay,
                        cancel=cancel,
                    ):
                        yield ("assistant_token", {"text": chunk})

                assistant_msg = ChatMessage(
                    thread_id=prep.thread_id,
                    role=ChatRole.ASSISTANT,
                    content=assistant_text,
                    experiment_id=experiment.id,
                    turn_kind=ChatTurnKind.UNIVERSAL_CHAT,
                    parent_message_id=chain_parent_id,
                )
                db.add(assistant_msg)
                await db.flush()
                await set_active_leaf(db, prep.thread_id, assistant_msg.id)
                await _set_turn_status(
                    db,
                    prep.status_message_id,
                    turn_id=prep.turn_id,
                    status=TURN_STATUS_DONE,
                )
                await db.commit()
                assistant_message_id = str(assistant_msg.id)
            else:
                # Refine MCQ-only (or empty refine prose): no master bubble.
                if chain_parent_id is not None:
                    await set_active_leaf(db, prep.thread_id, chain_parent_id)
                await _set_turn_status(
                    db,
                    prep.status_message_id,
                    turn_id=prep.turn_id,
                    status=TURN_STATUS_DONE,
                )
                await db.commit()
                assistant_message_id = ""

            _logger.info(
                "universal chat stream completed",
                experiment_id=str(experiment.id),
                thread_id=str(prep.thread_id),
                tool_rounds=tool_rounds,
                provider=provider,
                skip_master_final=skip_master_final,
                has_assistant_text=bool(assistant_text),
                refine_already_streamed=refine_already_streamed,
            )
            yield (
                "done",
                {
                    "assistant_message_id": assistant_message_id,
                    "thread_id": str(prep.thread_id),
                    "turn_id": str(prep.turn_id),
                    "user_message_id": (
                        str(prep.user_message_id)
                        if prep.user_message_id and not prep.suppress_user_echo
                        else None
                    ),
                },
            )
        except (asyncio.CancelledError, GeneratorExit):
            _logger.info(
                "universal chat turn cancelled",
                experiment_id=str(prep.experiment_id),
                thread_id=str(prep.thread_id),
                turn_id=str(prep.turn_id),
            )
            with contextlib.suppress(Exception):
                await _set_turn_status(
                    db,
                    prep.status_message_id,
                    turn_id=prep.turn_id,
                    status=TURN_STATUS_FAILED,
                )
                await db.commit()
            raise
        except Exception as exc:
            _logger.warning(
                "universal chat turn failed",
                experiment_id=str(prep.experiment_id),
                thread_id=str(prep.thread_id),
                turn_id=str(prep.turn_id),
                error_type=type(exc).__name__,
            )
            with contextlib.suppress(Exception):
                await db.rollback()
            err_text = "Universal chat failed, please try again"
            with contextlib.suppress(Exception):
                err_msg = ChatMessage(
                    thread_id=prep.thread_id,
                    role=ChatRole.ASSISTANT,
                    content=err_text,
                    experiment_id=prep.experiment_id,
                    turn_kind=ChatTurnKind.UNIVERSAL_CHAT,
                    parent_message_id=chain_parent_id,
                )
                db.add(err_msg)
                await db.flush()
                await set_active_leaf(db, prep.thread_id, err_msg.id)
                await _set_turn_status(
                    db,
                    prep.status_message_id,
                    turn_id=prep.turn_id,
                    status=TURN_STATUS_FAILED,
                )
                await db.commit()
                yield (
                    "assistant_token",
                    {"text": err_text},
                )
                yield (
                    "done",
                    {
                        "assistant_message_id": str(err_msg.id),
                        "thread_id": str(prep.thread_id),
                        "turn_id": str(prep.turn_id),
                        "user_message_id": (
                            str(prep.user_message_id)
                            if prep.user_message_id and not prep.suppress_user_echo
                            else None
                        ),
                    },
                )
                return
            await _set_turn_status(
                db,
                prep.status_message_id,
                turn_id=prep.turn_id,
                status=TURN_STATUS_FAILED,
            )
            with contextlib.suppress(Exception):
                await db.commit()
            yield ("error", {"message": err_text})


async def _delete_in_flight_tool_result(
    db: AsyncSession,
    message_id: UUID | None,
) -> None:
    """Remove an unfinalized sub-agent tool_result row on cancel (best-effort)."""
    if message_id is None:
        return
    try:
        row = await db.get(ChatMessage, message_id)
        if row is not None and row.role == ChatRole.TOOL_RESULT:
            await db.delete(row)
            await db.commit()
    except Exception:
        with contextlib.suppress(Exception):
            await db.rollback()
        _logger.warning(
            "failed to delete in-flight tool_result on cancel",
            message_id=str(message_id),
        )


async def _stream_refine_tool(
    db: AsyncSession,
    experiment: Experiment,
    user: User,
    tool_use: Any,
    prep: UniversalStreamPrep,
    chain_parent_id: UUID | None,
    *,
    mcq_answer: dict[str, Any] | None = None,
    cancel: asyncio.Event | None = None,
) -> AsyncGenerator[tuple[str, Any], None]:
    """Refine: sync execute, pace assistant tokens, then emit tool_result.

    Tokens are yielded here (not after the whole tool batch) so refine prose
    streams progressively like master text. Yields ``_refine_outcome`` so the
    stream loop can skip the master's final text call and avoid double-pacing.
    """
    exec_args = _inject_mcq_into_tool_args(
        tool_use.name, tool_use.input, mcq_answer
    )
    exec_result = await _await_unless_cancelled(
        execute_tool(
            tool_use.name,
            exec_args,
            db,
            experiment,
            user=user,
        ),
        cancel,
    )
    payload = _tool_result_payload(tool_use.name, exec_result)
    refine_ok = "error" not in payload
    refine_text = ""
    if refine_ok and isinstance(exec_result.get("assistant_text"), str):
        refine_text = exec_result["assistant_text"].strip()

    # Pace refine prose immediately — before tool_result / sibling tools.
    if refine_text:
        async for chunk in iter_paced_text_chunks(
            refine_text, pacing_delay=prep.pacing_delay, cancel=cancel
        ):
            yield ("assistant_token", {"text": chunk})

    yield (
        "_refine_outcome",
        {
            "ok": refine_ok,
            "assistant_text": refine_text,
            "already_streamed": bool(refine_text),
            "has_pending_mcq": bool(
                isinstance(exec_result.get("has_pending_mcq"), bool)
                and exec_result.get("has_pending_mcq")
            )
            or bool(exec_result.get("mcq_question")),
        },
    )

    tool_result_msg = ChatMessage(
        thread_id=prep.thread_id,
        role=ChatRole.TOOL_RESULT,
        content="Result received",
        experiment_id=experiment.id,
        turn_kind=ChatTurnKind.UNIVERSAL_CHAT,
        parent_message_id=chain_parent_id,
        tool_payload=payload,
    )
    db.add(tool_result_msg)
    await db.flush()
    yield ("_in_flight_tool_result", {"id": tool_result_msg.id})
    await set_active_leaf(db, prep.thread_id, tool_result_msg.id)
    await db.commit()

    yield (
        "tool_result",
        {
            "tool_name": tool_use.name,
            "message_id": str(tool_result_msg.id),
            "payload": payload,
        },
    )
    yield (
        "_chain_parent",
        {
            "id": tool_result_msg.id,
            "content_json": _tool_result_content_json(payload),
        },
    )
