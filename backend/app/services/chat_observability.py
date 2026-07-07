"""Chat-mode quality observability queries (planning doc §6.4).

Pure async query functions over existing tables. No side effects.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import ChatRole, ChatTurnKind, DispatchTrigger, ExperimentStatus
from app.db.models.chat_message import ChatMessage
from app.db.models.experiment import Experiment
from app.db.models.llm_call import LLMCall
from app.db.models.validation_report import ValidationReport

_REFINEMENT_CHAT_PHASES = ("refinement_chat", "chat_normal")
_TURN_BUCKETS = (0, 1, 2, 3)


def _percentile(sorted_values: list[int], pct: float) -> int:
    """Linear-interpolation percentile; returns 0 for an empty list."""
    if not sorted_values:
        return 0
    if len(sorted_values) == 1:
        return sorted_values[0]
    rank = (pct / 100.0) * (len(sorted_values) - 1)
    lower = int(rank)
    upper = min(lower + 1, len(sorted_values) - 1)
    weight = rank - lower
    return int(round(sorted_values[lower] * (1 - weight) + sorted_values[upper] * weight))


def _bucket_refinement_count(count: int) -> int:
    return min(count, 3)


async def refinement_turn_count_distribution(
    db: AsyncSession,
    since: datetime | None = None,
) -> dict[int, int]:
    """Histogram of final refinement_count for chat-mode experiments (thread_id set)."""
    stmt = (
        select(Experiment.refinement_count, func.count())
        .where(Experiment.thread_id.is_not(None))
        .group_by(Experiment.refinement_count)
    )
    if since is not None:
        stmt = stmt.where(Experiment.updated_at >= since)

    rows = (await db.execute(stmt)).all()
    distribution = {bucket: 0 for bucket in _TURN_BUCKETS}
    for refinement_count, row_count in rows:
        bucket = _bucket_refinement_count(int(refinement_count))
        distribution[bucket] = distribution.get(bucket, 0) + int(row_count)
    return distribution


async def user_reply_length_stats(
    db: AsyncSession,
    since: datetime | None = None,
) -> dict[str, int]:
    """Median / p90 / count / max char length of user replies to clarifying questions."""
    prev_role = func.lag(ChatMessage.role).over(
        partition_by=ChatMessage.thread_id,
        order_by=(ChatMessage.created_at.asc(), ChatMessage.id.asc()),
    )
    prev_turn_kind = func.lag(ChatMessage.turn_kind).over(
        partition_by=ChatMessage.thread_id,
        order_by=(ChatMessage.created_at.asc(), ChatMessage.id.asc()),
    )
    content_len = func.length(ChatMessage.content)

    inner = select(
        content_len.label("reply_len"),
        ChatMessage.role,
        prev_role.label("prev_role"),
        prev_turn_kind.label("prev_turn_kind"),
        ChatMessage.created_at,
    ).subquery()

    # LAG() over SQLEnum columns returns member names (e.g. ASSISTANT), not values.
    stmt = select(inner.c.reply_len).where(
        inner.c.role == ChatRole.USER.value,
        inner.c.prev_role == ChatRole.ASSISTANT.name,
        inner.c.prev_turn_kind == ChatTurnKind.REFINEMENT_CLARIFY.name,
    )
    if since is not None:
        stmt = stmt.where(inner.c.created_at >= since)
    lengths = [int(row[0]) for row in (await db.execute(stmt)).all() if row[0] is not None]
    if not lengths:
        return {"median": 0, "p90": 0, "count": 0, "max": 0}

    sorted_lengths = sorted(lengths)
    return {
        "median": _percentile(sorted_lengths, 50.0),
        "p90": _percentile(sorted_lengths, 90.0),
        "count": len(lengths),
        "max": max(lengths),
    }


async def dispatch_to_completion_latency_stats(
    db: AsyncSession,
    since: datetime | None = None,
) -> dict[str, int]:
    """Median / p90 dispatch-to-completion latency in seconds for finished pipelines.

    Dispatch anchor: earliest LLMCall.called_at for the experiment where phase is not
    refinement_chat or chat_normal (first pipeline-phase call after dispatch).

    Completion: validation_reports.generated_at for RESEARCH_READY;
    experiments.updated_at for RESEARCH_FAILED.
    """
    pipeline_start = (
        select(
            LLMCall.experiment_id.label("experiment_id"),
            func.min(LLMCall.called_at).label("dispatch_at"),
        )
        .where(
            LLMCall.experiment_id.is_not(None),
            LLMCall.phase.notin_(_REFINEMENT_CHAT_PHASES),
        )
        .group_by(LLMCall.experiment_id)
    ).subquery()

    completion_at = case(
        (
            Experiment.status == ExperimentStatus.RESEARCH_READY,
            ValidationReport.generated_at,
        ),
        (
            Experiment.status == ExperimentStatus.RESEARCH_FAILED,
            Experiment.updated_at,
        ),
    )

    stmt = (
        select(
            completion_at.label("completion_at"),
            pipeline_start.c.dispatch_at,
        )
        .select_from(Experiment)
        .join(
            pipeline_start,
            pipeline_start.c.experiment_id == Experiment.id,
        )
        .outerjoin(ValidationReport, ValidationReport.experiment_id == Experiment.id)
        .where(
            Experiment.dispatch_trigger.is_not(None),
            Experiment.status.in_(
                (ExperimentStatus.RESEARCH_READY, ExperimentStatus.RESEARCH_FAILED)
            ),
            pipeline_start.c.dispatch_at.is_not(None),
            completion_at.is_not(None),
        )
    )
    if since is not None:
        stmt = stmt.where(completion_at >= since)

    latencies: list[int] = []
    for completion_at_val, dispatch_at in (await db.execute(stmt)).all():
        if completion_at_val is None or dispatch_at is None:
            continue
        completion_ts = completion_at_val
        dispatch_ts = dispatch_at
        if completion_ts.tzinfo is None:
            completion_ts = completion_ts.replace(tzinfo=timezone.utc)
        if dispatch_ts.tzinfo is None:
            dispatch_ts = dispatch_ts.replace(tzinfo=timezone.utc)
        latencies.append(int((completion_ts - dispatch_ts).total_seconds()))

    if not latencies:
        return {"median_seconds": 0, "p90_seconds": 0, "count": 0}

    sorted_latencies = sorted(latencies)
    return {
        "median_seconds": _percentile(sorted_latencies, 50.0),
        "p90_seconds": _percentile(sorted_latencies, 90.0),
        "count": len(latencies),
    }


async def dispatch_trigger_ratio(
    db: AsyncSession,
    since: datetime | None = None,
) -> dict[str, int]:
    """Counts of experiments by dispatch_trigger (nulls excluded)."""
    stmt = (
        select(Experiment.dispatch_trigger, func.count())
        .where(Experiment.dispatch_trigger.is_not(None))
        .group_by(Experiment.dispatch_trigger)
    )
    if since is not None:
        stmt = stmt.where(Experiment.updated_at >= since)

    rows = (await db.execute(stmt)).all()
    result = {
        DispatchTrigger.USER_CONFIRM.value: 0,
        DispatchTrigger.AUTO_FIRE.value: 0,
    }
    for trigger, count in rows:
        if trigger is not None:
            result[trigger.value] = int(count)
    return result


async def first_turn_dimension_distribution(
    db: AsyncSession,
    since: datetime | None = None,
) -> dict[str, int]:
    """Distribution of clarifying_dimension on the first refinement_clarify turn per experiment."""
    row_num = func.row_number().over(
        partition_by=ChatMessage.experiment_id,
        order_by=(ChatMessage.created_at.asc(), ChatMessage.id.asc()),
    )
    ranked = (
        select(
            ChatMessage.experiment_id,
            ChatMessage.clarifying_dimension,
            ChatMessage.created_at,
            row_num.label("rn"),
        )
        .where(
            ChatMessage.role == ChatRole.ASSISTANT,
            ChatMessage.turn_kind == ChatTurnKind.REFINEMENT_CLARIFY,
            ChatMessage.experiment_id.is_not(None),
            ChatMessage.clarifying_dimension.is_not(None),
        )
    ).subquery()

    stmt = (
        select(ranked.c.clarifying_dimension, func.count())
        .where(ranked.c.rn == 1)
        .group_by(ranked.c.clarifying_dimension)
    )
    if since is not None:
        stmt = stmt.where(ranked.c.created_at >= since)

    rows = (await db.execute(stmt)).all()
    return {str(dimension): int(count) for dimension, count in rows if dimension is not None}
