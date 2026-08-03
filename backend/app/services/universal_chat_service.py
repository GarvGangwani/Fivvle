"""Universal chat service — canvas coach / agent surface.

Independent of chat_service.py and evidence_chat_service.py by design. Messages
carry ``turn_kind=UNIVERSAL_CHAT`` on an isolated ``experiments.universal_thread_id``
ChatThread so Refine and Evidence histories never mix.

v2 runs an Anthropic tool loop (``complete_with_tools``). Linear persistence:
user → tool_call → tool_result → … → assistant. Tool rows are non-branchable
children; ``content`` is a short label and data lives in ``tool_payload``.

Streaming (``stream_universal_chat_message``): user row committed pre-stream;
tool_call / tool_result committed as they happen; assistant only on success.
Tool decisions are batched per loop iteration (non-stream ``complete_with_tools``);
sub-agent + final assistant text stream to the client as SSE events.

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
from app.db.session import get_sessionmaker
from app.llm.prompts.universal_chat import (
    PROMPT_NAME_UNIVERSAL_CHAT,
    UNIVERSAL_CHAT_SYSTEM_PROMPT,
    build_universal_chat_user_prompt,
)
from app.logging_config import get_logger
from app.services.chat_tree_service import get_active_branch, set_active_leaf
from app.services.experiment_project_context import get_experiment_project_context
from app.services.subagent_executors import exec_ask_research_agent_stream
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

_TOOL_REFINE = "ask_refine_agent"
_TOOL_RESEARCH = "ask_research_agent"

# Default pacing for refine / master final text fake-streams.
_DEFAULT_PACING_DELAY_S = 0.04
_CHUNK_WORD_SIZES = (3, 4, 5, 6, 7, 8)


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


@dataclass(frozen=True)
class UniversalStreamPrep:
    """Request-session prep: user row committed before the SSE generator starts."""

    experiment_id: UUID
    user_id: UUID
    thread_id: UUID
    user_message_id: UUID
    user_prompt: str
    provider: str
    model: str
    fallback_provider: str
    fallback_model: str
    pacing_delay: float = _DEFAULT_PACING_DELAY_S


def _sanitize(message: str) -> str:
    return message.strip()


async def iter_paced_text_chunks(
    text: str,
    *,
    pacing_delay: float = _DEFAULT_PACING_DELAY_S,
) -> AsyncGenerator[str, None]:
    """Yield word-boundary chunks with optional pacing (refine / master final).

    Splits on whitespace into 3–8 word groups. Tests pass ``pacing_delay=0``.
    """
    cleaned = text.strip()
    if not cleaned:
        return
    words = cleaned.split()
    if not words:
        yield cleaned
        return
    i = 0
    size_idx = 0
    while i < len(words):
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
    *,
    current_open_phase: str | None = None,
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

    project_context = await get_experiment_project_context(
        db, experiment, current_open_phase=current_open_phase
    )
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
                    user=current_user,
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


async def prepare_universal_stream(
    db: AsyncSession,
    current_user: User,
    experiment_id: UUID,
    message: str,
    *,
    pacing_delay: float = _DEFAULT_PACING_DELAY_S,
    current_open_phase: str | None = None,
) -> UniversalStreamPrep:
    """Persist + commit the user row before the SSE generator starts.

    Mirrors evidence-chat prepare: mid-stream disconnect never loses the user
    message; active leaf points at the user until the assistant lands.
    """
    clean_message = _sanitize(message)
    if not clean_message:
        raise ValueError("message must not be empty")

    experiment = await _load_owned_experiment(db, current_user, experiment_id)
    thread = await _resolve_universal_thread(db, current_user, experiment)

    parent_id = thread.active_leaf_message_id
    history = await get_active_branch(db, thread.id) if parent_id is not None else []

    project_context = await get_experiment_project_context(
        db, experiment, current_open_phase=current_open_phase
    )
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
    await set_active_leaf(db, thread.id, user_msg.id)
    await db.commit()
    await db.refresh(user_msg)

    settings = get_settings()
    return UniversalStreamPrep(
        experiment_id=experiment.id,
        user_id=current_user.id,
        thread_id=thread.id,
        user_message_id=user_msg.id,
        user_prompt=user_prompt,
        provider=settings.universal_chat_tools_provider,
        model=settings.universal_chat_tools_model,
        fallback_provider=settings.universal_chat_tools_fallback_provider,
        fallback_model=settings.universal_chat_tools_fallback_model,
        pacing_delay=pacing_delay,
    )


async def stream_universal_chat_message(
    prep: UniversalStreamPrep,
) -> AsyncGenerator[tuple[str, dict[str, Any]], None]:
    """SSE event tuples for one universal-chat turn (own DB session).

    Yields ``(event_name, payload)`` for:
    ``tool_call``, ``tool_result``, ``subagent_token``, ``assistant_token``,
    ``done``, ``error``.

    Final master text is paced-chunked from ``complete_with_tools`` (not
    ``complete_stream``): the LLM client stream API only accepts a single user
    string and cannot carry the multi-turn tool-loop messages.
    """
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        user = await db.get(User, prep.user_id)
        experiment = await db.get(Experiment, prep.experiment_id)
        if user is None or experiment is None:
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
            yield ("error", {"message": "Universal chat failed, please try again"})
            return

        tool_schemas = get_tool_schemas(provider)
        tool_rounds = 0
        fallback_armed = True
        assistant_text = _FALLBACK_TEXT

        try:
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
                    only_user = chain_parent_id == prep.user_message_id
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
                    in_flight_tool_result_id: UUID | None = None

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
                        await db.commit()
                        chain_parent_id = tool_call_msg.id
                        yield (
                            "tool_call",
                            {
                                "tool_name": tool_use.name,
                                "message_id": str(tool_call_msg.id),
                            },
                        )

                        if tool_use.name == _TOOL_RESEARCH:
                            try:
                                async for evt in _stream_research_tool(
                                    db,
                                    experiment,
                                    user,
                                    tool_use,
                                    prep,
                                    chain_parent_id,
                                ):
                                    if evt[0] == "_chain_parent":
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
                            continue

                        if tool_use.name == _TOOL_REFINE:
                            try:
                                async for evt in _stream_refine_tool(
                                    db,
                                    experiment,
                                    user,
                                    tool_use,
                                    prep,
                                    chain_parent_id,
                                ):
                                    if evt[0] == "_chain_parent":
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
                            # handle_turn may have committed/expired identity
                            refreshed = await db.get(Experiment, experiment.id)
                            if refreshed is not None:
                                experiment = refreshed
                            continue

                        exec_result = await execute_tool(
                            tool_use.name,
                            tool_use.input,
                            db,
                            experiment,
                            user=user,
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

            async for chunk in iter_paced_text_chunks(
                assistant_text, pacing_delay=prep.pacing_delay
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
            await db.commit()

            _logger.info(
                "universal chat stream completed",
                experiment_id=str(experiment.id),
                thread_id=str(prep.thread_id),
                tool_rounds=tool_rounds,
                provider=provider,
            )
            yield (
                "done",
                {
                    "assistant_message_id": str(assistant_msg.id),
                    "thread_id": str(prep.thread_id),
                    "user_message_id": str(prep.user_message_id),
                },
            )
        except (asyncio.CancelledError, GeneratorExit):
            _logger.info(
                "universal chat stream cancelled",
                experiment_id=str(prep.experiment_id),
                thread_id=str(prep.thread_id),
            )
            raise
        except Exception as exc:
            _logger.warning(
                "universal chat stream failed",
                experiment_id=str(prep.experiment_id),
                thread_id=str(prep.thread_id),
                error_type=type(exc).__name__,
            )
            with contextlib.suppress(Exception):
                await db.rollback()
            yield ("error", {"message": "Universal chat failed, please try again"})


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


async def _stream_research_tool(
    db: AsyncSession,
    experiment: Experiment,
    user: User,
    tool_use: Any,
    prep: UniversalStreamPrep,
    chain_parent_id: UUID | None,
) -> AsyncGenerator[tuple[str, Any], None]:
    """Research: tokens first, then commit + emit tool_result with full payload."""
    final_payload: dict[str, Any] | None = None
    async for kind, payload in exec_ask_research_agent_stream(
        db, experiment, tool_use.input, user
    ):
        if kind == "token":
            text = payload.get("text")
            if isinstance(text, str) and text:
                yield ("subagent_token", {"agent": "research", "text": text})
        elif kind == "complete":
            final_payload = payload

    if final_payload is None:
        final_payload = {"error": "Research agent returned no result"}

    stored = _tool_result_payload(tool_use.name, final_payload)
    tool_result_msg = ChatMessage(
        thread_id=prep.thread_id,
        role=ChatRole.TOOL_RESULT,
        content="Result received",
        experiment_id=experiment.id,
        turn_kind=ChatTurnKind.UNIVERSAL_CHAT,
        parent_message_id=chain_parent_id,
        tool_payload=stored,
    )
    db.add(tool_result_msg)
    await db.flush()
    # Track until commit succeeds so cancel can delete a half-written row.
    yield ("_in_flight_tool_result", {"id": tool_result_msg.id})
    await db.commit()

    yield (
        "tool_result",
        {
            "tool_name": tool_use.name,
            "message_id": str(tool_result_msg.id),
            "payload": stored,
        },
    )
    yield (
        "_chain_parent",
        {
            "id": tool_result_msg.id,
            "content_json": _tool_result_content_json(stored),
        },
    )


async def _stream_refine_tool(
    db: AsyncSession,
    experiment: Experiment,
    user: User,
    tool_use: Any,
    prep: UniversalStreamPrep,
    chain_parent_id: UUID | None,
) -> AsyncGenerator[tuple[str, Any], None]:
    """Refine: sync execute, fake-stream tokens, then commit + emit tool_result."""
    exec_result = await execute_tool(
        tool_use.name,
        tool_use.input,
        db,
        experiment,
        user=user,
    )
    payload = _tool_result_payload(tool_use.name, exec_result)

    if "error" not in payload and isinstance(exec_result.get("assistant_text"), str):
        async for chunk in iter_paced_text_chunks(
            exec_result["assistant_text"],
            pacing_delay=prep.pacing_delay,
        ):
            yield ("subagent_token", {"agent": "refine", "text": chunk})

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
