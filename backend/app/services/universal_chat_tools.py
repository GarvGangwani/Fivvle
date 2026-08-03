"""Tools for the universal-chat Anthropic/Kimi tool loop.

Phase 1 read tools: get_metrics_summary, get_report_summary, get_landing_status.
Phase 2 sub-agents: ask_refine_agent, ask_research_agent.

Executors soft-fail: exceptions become ``{"error": "..."}`` via ``execute_tool``.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.experiment import Experiment
from app.db.models.landing_page import LandingPage
from app.db.models.page_view import PageView
from app.db.models.user import User
from app.db.models.waitlist_signup import WaitlistSignup
from app.logging_config import get_logger
from app.services.experiment_service import metrics_from_validation_report
from app.services.landing_page_publish_service import get_open_cohort
from app.services.subagent_executors import (
    exec_ask_refine_agent,
    exec_ask_research_agent,
    refine_agent_input_schema,
    research_agent_input_schema,
)

_logger = get_logger(__name__)

_TOP_SOURCES_LIMIT = 5
_TOP_FINDINGS_LIMIT = 3
_CLAIM_MAX_CHARS = 280

# Empty JSON Schema object — Phase 1 read tools take no LLM-supplied arguments.
_EMPTY_INPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {},
    "additionalProperties": False,
}

# (db, experiment, args, user) — user is required for sub-agents; ignored by read tools.
ToolExecutor = Callable[
    [AsyncSession, Experiment, dict[str, Any], User | None],
    Awaitable[dict[str, Any]],
]


@dataclass(frozen=True)
class UniversalChatTool:
    name: str
    description: str
    input_schema: dict[str, Any]
    executor: ToolExecutor


def _truncate(text: str, max_len: int) -> str:
    cleaned = text.strip()
    if len(cleaned) <= max_len:
        return cleaned
    return cleaned[: max_len - 3].rstrip() + "..."


async def _exec_get_metrics_summary(
    db: AsyncSession,
    experiment: Experiment,
    args: dict[str, Any],
    user: User | None,
) -> dict[str, Any]:
    """Lean COUNT + GROUP BY metrics. Never calls build_analytics_aggregate."""
    _ = args, user
    lp_result = await db.execute(
        select(LandingPage).where(LandingPage.experiment_id == experiment.id)
    )
    landing_page = lp_result.scalar_one_or_none()
    if landing_page is None or landing_page.live_at is None:
        return {
            "available": False,
            "reason": "Landing page is not published yet.",
            "total_page_views": 0,
            "total_signups": 0,
            "top_traffic_sources": [],
        }

    cohort = await get_open_cohort(db, landing_page.id)
    if cohort is None:
        return {
            "available": False,
            "reason": "Landing page is live but has no open publish cohort.",
            "total_page_views": 0,
            "total_signups": 0,
            "top_traffic_sources": [],
            "live_at": landing_page.live_at.isoformat(),
        }

    views_count = int(
        await db.scalar(
            select(func.count())
            .select_from(PageView)
            .where(
                PageView.experiment_id == experiment.id,
                PageView.publish_id == cohort.id,
            )
        )
        or 0
    )
    signups_count = int(
        await db.scalar(
            select(func.count())
            .select_from(WaitlistSignup)
            .where(
                WaitlistSignup.experiment_id == experiment.id,
                WaitlistSignup.publish_id == cohort.id,
            )
        )
        or 0
    )

    source_expr = func.coalesce(PageView.source_tag, "unknown")
    source_rows = (
        await db.execute(
            select(
                source_expr.label("source"),
                func.count().label("views"),
            )
            .where(
                PageView.experiment_id == experiment.id,
                PageView.publish_id == cohort.id,
            )
            .group_by(source_expr)
            .order_by(func.count().desc())
            .limit(_TOP_SOURCES_LIMIT)
        )
    ).all()

    top_sources = [
        {"source": str(row.source), "views": int(row.views)} for row in source_rows
    ]

    if views_count == 0 and signups_count == 0:
        return {
            "available": False,
            "reason": "Landing page is live but has no views or signups yet.",
            "total_page_views": 0,
            "total_signups": 0,
            "top_traffic_sources": [],
            "live_at": landing_page.live_at.isoformat(),
        }

    return {
        "available": True,
        "total_page_views": views_count,
        "total_signups": signups_count,
        "top_traffic_sources": top_sources,
        "live_at": landing_page.live_at.isoformat(),
    }


def _aggregate_report_fields(raw: dict[str, Any]) -> dict[str, Any]:
    """Mirror routers.experiments._aggregate_validation_report + score extract.

    Kept local so services never import the experiments router.
    """
    qfs = raw.get("questions_and_findings") or []
    finding_count = sum(len(qf.get("findings") or []) for qf in qfs)
    citation_count = 0
    for qf in qfs:
        for finding in qf.get("findings") or []:
            citation_count += len(finding.get("citations") or [])
    for comp in raw.get("competitors") or []:
        citation_count += len(comp.get("citations") or [])

    _finding_count, demand_score, verdict = metrics_from_validation_report(raw)
    overall_recommendation = raw.get("overall_recommendation")
    if overall_recommendation is not None and not isinstance(overall_recommendation, str):
        overall_recommendation = str(overall_recommendation)
    if overall_recommendation is None:
        overall_recommendation = verdict

    return {
        "overall_recommendation": overall_recommendation,
        "overall_score": demand_score,
        "total_finding_count": finding_count,
        "total_citation_count": citation_count,
    }


def _top_findings_by_score(raw: dict[str, Any], *, limit: int) -> list[dict[str, Any]]:
    """Pick top findings using parent question score, then confidence."""
    confidence_rank = {"high": 3, "medium": 2, "low": 1}
    scored: list[tuple[int, int, dict[str, Any]]] = []

    for qf in raw.get("questions_and_findings") or []:
        if not isinstance(qf, dict):
            continue
        q_score = qf.get("score")
        question_score = int(q_score) if isinstance(q_score, (int, float)) else 0
        question_id = qf.get("question_id")
        for finding in qf.get("findings") or []:
            if not isinstance(finding, dict):
                continue
            claim = finding.get("claim")
            if not isinstance(claim, str) or not claim.strip():
                continue
            conf = finding.get("confidence")
            conf_rank = confidence_rank.get(conf, 0) if isinstance(conf, str) else 0
            scored.append(
                (
                    question_score,
                    conf_rank,
                    {
                        "question_id": question_id,
                        "claim": _truncate(claim, _CLAIM_MAX_CHARS),
                        "confidence": conf if isinstance(conf, str) else None,
                        "question_score": question_score if q_score is not None else None,
                    },
                )
            )

    scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
    return [item[2] for item in scored[:limit]]


async def _exec_get_report_summary(
    db: AsyncSession,
    experiment: Experiment,
    args: dict[str, Any],
    user: User | None,
) -> dict[str, Any]:
    _ = args, user
    result = await db.execute(
        select(Experiment)
        .options(selectinload(Experiment.validation_report))
        .where(Experiment.id == experiment.id)
    )
    exp = result.scalar_one()
    report = exp.validation_report
    if report is None or not isinstance(report.raw_report, dict):
        return {
            "available": False,
            "reason": "No validation report yet.",
        }

    raw = report.raw_report
    summary = _aggregate_report_fields(raw)
    return {
        "available": True,
        **summary,
        "top_findings": _top_findings_by_score(raw, limit=_TOP_FINDINGS_LIMIT),
    }


async def _exec_get_landing_status(
    db: AsyncSession,
    experiment: Experiment,
    args: dict[str, Any],
    user: User | None,
) -> dict[str, Any]:
    _ = args, user
    lp_result = await db.execute(
        select(LandingPage).where(LandingPage.experiment_id == experiment.id)
    )
    landing_page = lp_result.scalar_one_or_none()
    if landing_page is None:
        return {
            "available": False,
            "reason": "No landing page yet.",
        }

    is_live = landing_page.live_at is not None
    return {
        "available": True,
        "is_live": is_live,
        "slug": landing_page.slug,
        "headline": landing_page.headline,
        "subheadline": landing_page.subheadline,
        "live_at": landing_page.live_at.isoformat() if landing_page.live_at else None,
    }


async def _exec_ask_refine_agent(
    db: AsyncSession,
    experiment: Experiment,
    args: dict[str, Any],
    user: User | None,
) -> dict[str, Any]:
    if user is None:
        return {"error": "user required for ask_refine_agent"}
    return await exec_ask_refine_agent(db, experiment, args, user)


async def _exec_ask_research_agent(
    db: AsyncSession,
    experiment: Experiment,
    args: dict[str, Any],
    user: User | None,
) -> dict[str, Any]:
    if user is None:
        return {"error": "user required for ask_research_agent"}
    return await exec_ask_research_agent(db, experiment, args, user)


_OPEN_PHASE_VALUES = ("spark", "refine", "evidence", "launch", "signal")

_OPEN_PHASE_PANEL_INPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "phase": {
            "type": "string",
            "enum": list(_OPEN_PHASE_VALUES),
            "description": (
                "Phase panel to open: spark, refine, evidence, launch, or signal."
            ),
        },
        "source_ref_id": {
            "type": ["string", "null"],
            "description": (
                "Optional citation marker id (e.g. [cite:s1]) for evidence scroll. "
                "Pass null when not pointing at a specific source."
            ),
        },
    },
    "required": ["phase"],
    "additionalProperties": False,
}


async def _exec_open_phase_panel(
    db: AsyncSession,
    experiment: Experiment,
    args: dict[str, Any],
    user: User | None,
) -> dict[str, Any]:
    """Return a navigate payload for the frontend. No DB side effects."""
    _ = db, experiment, user
    phase = args.get("phase") if isinstance(args, dict) else None
    if not isinstance(phase, str) or phase not in _OPEN_PHASE_VALUES:
        return {"error": "phase must be one of spark|refine|evidence|launch|signal"}
    source_ref_id = args.get("source_ref_id")
    if source_ref_id is not None and not isinstance(source_ref_id, str):
        source_ref_id = None
    if isinstance(source_ref_id, str) and not source_ref_id.strip():
        source_ref_id = None
    return {
        "navigate_to": phase,
        "source_ref_id": source_ref_id,
    }


_TOOLS: tuple[UniversalChatTool, ...] = (
    UniversalChatTool(
        name="get_metrics_summary",
        description=(
            "Return lean landing-page metrics: total page views, waitlist signups, "
            "and top traffic sources. Use only when the founder asks about numbers, "
            "traffic, conversion, or waitlist performance."
        ),
        input_schema=_EMPTY_INPUT_SCHEMA,
        executor=_exec_get_metrics_summary,
    ),
    UniversalChatTool(
        name="get_report_summary",
        description=(
            "Return a compact validation-report summary: overall recommendation, "
            "overall score, finding/citation counts, and top findings. Use only when "
            "the founder asks about research findings, scores, or the recommendation."
        ),
        input_schema=_EMPTY_INPUT_SCHEMA,
        executor=_exec_get_report_summary,
    ),
    UniversalChatTool(
        name="get_landing_status",
        description=(
            "Return whether the landing page exists/is live, plus slug, headline, "
            "and subheadline. Use only when the founder asks if the page is live "
            "or about landing status/URL copy."
        ),
        input_schema=_EMPTY_INPUT_SCHEMA,
        executor=_exec_get_landing_status,
    ),
    UniversalChatTool(
        name="ask_refine_agent",
        description=(
            "Ask the Refine sub-agent to continue refining the idea (naming, target "
            "user, positioning, differentiation, clarifying questions). Writes to "
            "the refine chat thread and may update refined_idea_current. Pass the "
            "founder's refinement question as query."
        ),
        input_schema=refine_agent_input_schema(),
        executor=_exec_ask_refine_agent,
    ),
    UniversalChatTool(
        name="ask_research_agent",
        description=(
            "Ask the Research/Evidence sub-agent about the validation report, market "
            "signals, competitors, findings, or citations. Read-only; writes to the "
            "evidence chat thread. Pass the founder's research question as query."
        ),
        input_schema=research_agent_input_schema(),
        executor=_exec_ask_research_agent,
    ),
    UniversalChatTool(
        name="open_phase_panel",
        description=(
            "Open a phase panel (spark, refine, evidence, launch, signal) so the "
            "founder can see the artifact. Use after research/refine sub-agents when "
            "the founder should look at the report or refine surface. Do not call if "
            "that phase is already current_open_phase. Do not open for metrics-only "
            "answers."
        ),
        input_schema=_OPEN_PHASE_PANEL_INPUT_SCHEMA,
        executor=_exec_open_phase_panel,
    ),
)

_TOOLS_BY_NAME: dict[str, UniversalChatTool] = {tool.name: tool for tool in _TOOLS}


def get_tool_schemas(provider: str = "anthropic") -> list[dict[str, Any]]:
    """Provider-dialect ``tools=`` schemas for the universal-chat loop."""
    if provider == "anthropic":
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.input_schema,
            }
            for tool in _TOOLS
        ]
    if provider == "kimi":
        return [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.input_schema,
                },
            }
            for tool in _TOOLS
        ]
    raise ValueError(f"unsupported tool schema provider: {provider}")


async def execute_tool(
    name: str,
    args: dict[str, Any],
    db: AsyncSession,
    experiment: Experiment,
    *,
    user: User | None = None,
) -> dict[str, Any]:
    """Run a named tool. Soft-fail: never raise into the agent loop.

    ``args`` carries LLM tool_use input (e.g. ``query`` for sub-agents).
    Phase 1 read tools ignore args and scope to ``experiment``.
    """
    tool = _TOOLS_BY_NAME.get(name)
    if tool is None:
        return {"error": f"Unknown tool: {name}"}
    try:
        return await tool.executor(db, experiment, args or {}, user)
    except Exception as exc:
        _logger.warning(
            "universal chat tool failed",
            tool_name=name,
            experiment_id=str(experiment.id),
            error_type=type(exc).__name__,
        )
        return {"error": f"{type(exc).__name__}: tool execution failed"}
