"""Sub-agent executors for the universal-chat tool loop (Phase 2).

``ask_refine_agent`` and ``ask_research_agent`` call the existing refine /
evidence chat services so rail and phase-panel share the same threads.
Mapped results are typed dicts persisted as ``tool_payload.result``.
"""

from __future__ import annotations

import copy
import re
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.experiment import Experiment
from app.db.models.user import User
from app.dispatchers.protocol import ResearchDispatcher
from app.llm.prompts.refine_subagent import (
    PROMPT_NAME_REFINE_SUBAGENT,
    REFINE_SUBAGENT_SYSTEM_PROMPT,
    build_refine_subagent_user_prompt,
)
from app.llm.prompts.research_subagent import (
    PROMPT_NAME_RESEARCH_SUBAGENT,
    RESEARCH_SUBAGENT_SYSTEM_PROMPT,
)
from app.logging_config import get_logger
from app.services import chat_service
from app.services.evidence_chat_service import send_evidence_chat_message

_logger = get_logger(__name__)

_CITE_RE = re.compile(r"\[cite:\s*([^\]]*)\]", re.IGNORECASE)
_REF_RE = re.compile(r"\[ref:\s*([^\]]*)\]", re.IGNORECASE)
_MARKER_RE = re.compile(
    r"\[(?:cite|ref):\s*[^\]]*\]",
    re.IGNORECASE,
)

_QUERY_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "query": {
            "type": "string",
            "description": (
                "The founder's question or request to forward to the sub-agent."
            ),
        },
    },
    "required": ["query"],
    "additionalProperties": False,
}


class _NoopResearchDispatcher:
    """Refine turns no longer auto-dispatch research; satisfy the Protocol."""

    async def dispatch(self, experiment_id: UUID) -> None:
        _ = experiment_id


def refine_agent_input_schema() -> dict[str, Any]:
    return copy.deepcopy(_QUERY_SCHEMA)


def research_agent_input_schema() -> dict[str, Any]:
    return copy.deepcopy(_QUERY_SCHEMA)


def _extract_query(args: dict[str, Any]) -> str | None:
    raw = args.get("query")
    if not isinstance(raw, str):
        return None
    cleaned = raw.strip()
    return cleaned or None


def _title_for_url(url: str, report: dict[str, Any] | None) -> str:
    if report:
        for qf in report.get("questions_and_findings") or []:
            if not isinstance(qf, dict):
                continue
            for finding in qf.get("findings") or []:
                if not isinstance(finding, dict):
                    continue
                for cite in finding.get("citations") or []:
                    if isinstance(cite, dict) and cite.get("url") == url:
                        title = cite.get("title")
                        if isinstance(title, str) and title.strip():
                            return title.strip()
        for comp in report.get("competitors") or []:
            if not isinstance(comp, dict):
                continue
            for cite in comp.get("citations") or []:
                if isinstance(cite, dict) and cite.get("url") == url:
                    title = cite.get("title")
                    if isinstance(title, str) and title.strip():
                        return title.strip()
    try:
        from urllib.parse import urlparse

        host = urlparse(url).netloc
        return host or url
    except Exception:
        return url


def _title_for_ref_anchor(anchor: str, report: dict[str, Any] | None) -> str:
    cleaned = anchor.strip()
    lower = cleaned.lower()
    if lower.startswith("q") and lower[1:].isdigit():
        if report:
            for qf in report.get("questions_and_findings") or []:
                if isinstance(qf, dict) and str(qf.get("question_id", "")).lower() == lower:
                    q = qf.get("question")
                    if isinstance(q, str) and q.strip():
                        return f"{lower}: {q.strip()}"
        return lower
    if lower.startswith("competitor:"):
        name = cleaned[len("competitor:") :].strip() or cleaned
        return f"Competitor: {name}"
    if lower.startswith("section:"):
        return f"Section: {cleaned[len('section:') :].strip()}"
    if lower == "limitation":
        return "Limitation"
    return cleaned


def build_source_refs_from_evidence_text(
    text: str,
    report: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    """Walk evidence-chat markers in first-seen order; resolve titles from report.

    Markers stay in ``assistant_text_with_citations``. This list is metadata for
    the rail chip renderer — not a second citation format.
    """
    refs: list[dict[str, Any]] = []
    seen: set[str] = set()

    def _append(
        marker_id: str,
        *,
        source_title: str,
        source_url: str | None,
    ) -> None:
        key = marker_id.lower()
        if key in seen:
            return
        seen.add(key)
        refs.append(
            {
                "marker_id": marker_id,
                "source_title": source_title,
                "source_url": source_url,
                "ref_number": len(refs) + 1,
            }
        )

    for match in _MARKER_RE.finditer(text):
        marker = match.group(0)
        cite_m = _CITE_RE.fullmatch(marker)
        if cite_m:
            urls = [u.strip() for u in cite_m.group(1).split(",") if u.strip()]
            if len(urls) == 1:
                url = urls[0]
                _append(
                    marker,
                    source_title=_title_for_url(url, report),
                    source_url=url,
                )
            else:
                for url in urls:
                    _append(
                        f"[cite: {url}]",
                        source_title=_title_for_url(url, report),
                        source_url=url,
                    )
            continue

        ref_m = _REF_RE.fullmatch(marker)
        if ref_m:
            anchors = [a.strip() for a in ref_m.group(1).split(",") if a.strip()]
            if len(anchors) == 1:
                anchor = anchors[0]
                _append(
                    marker,
                    source_title=_title_for_ref_anchor(anchor, report),
                    source_url=None,
                )
            else:
                for anchor in anchors:
                    _append(
                        f"[ref: {anchor}]",
                        source_title=_title_for_ref_anchor(anchor, report),
                        source_url=None,
                    )

    return refs


def _refined_idea_patch(
    before: dict[str, Any] | None,
    after: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """Return the post-turn idea when a write happened; else None.

    ``RefinementTurnDecision`` has no patch type — ``run_turn`` replaces
    ``refined_idea_current`` with a full ``RefinedIdea`` dump when present.
    """
    if after is None:
        return None
    if before == after:
        return None
    return after


async def exec_ask_refine_agent(
    db: AsyncSession,
    experiment: Experiment,
    args: dict[str, Any],
    user: User,
) -> dict[str, Any]:
    """Forward ``query`` into the refine thread via ``chat_service.handle_turn``."""
    query = _extract_query(args)
    if query is None:
        return {"error": "query is required"}

    before_idea = (
        copy.deepcopy(experiment.refined_idea_current)
        if isinstance(experiment.refined_idea_current, dict)
        else None
    )

    dispatcher: ResearchDispatcher = _NoopResearchDispatcher()
    turn = await chat_service.handle_turn(
        db,
        user=user,
        message=query,
        deep_research=True,
        thread_id=experiment.thread_id,
        experiment_id=experiment.id,
        idempotency_key=f"universal-refine-{uuid4()}",
        dispatcher=dispatcher,
        prompt_name=PROMPT_NAME_REFINE_SUBAGENT,
        system_prompt=REFINE_SUBAGENT_SYSTEM_PROMPT,
        user_prompt_builder=build_refine_subagent_user_prompt,
    )

    # Reload experiment — handle_turn commits; identity may be expired.
    refreshed = await db.get(Experiment, experiment.id)
    after_idea: dict[str, Any] | None = None
    if refreshed is not None and isinstance(refreshed.refined_idea_current, dict):
        after_idea = refreshed.refined_idea_current
        # Keep caller's experiment instance in sync for subsequent tools.
        experiment.refined_idea_current = after_idea
        experiment.thread_id = refreshed.thread_id
        experiment.status = refreshed.status
        experiment.refinement_count = refreshed.refinement_count

    has_mcq = len(turn.clarifying_questions) > 0
    log_entry = turn.clarifying_dimension

    return {
        "assistant_text": turn.assistant_message,
        "refined_idea_patch": _refined_idea_patch(before_idea, after_idea),
        "has_pending_mcq": has_mcq,
        "log_entry": log_entry,
    }


async def exec_ask_research_agent(
    db: AsyncSession,
    experiment: Experiment,
    args: dict[str, Any],
    user: User,
) -> dict[str, Any]:
    """Forward ``query`` into evidence chat (non-streaming) on ``evidence_thread_id``."""
    query = _extract_query(args)
    if query is None:
        return {"error": "query is required"}

    result = await send_evidence_chat_message(
        db,
        current_user=user,
        experiment_id=experiment.id,
        message=query,
        prompt_name=PROMPT_NAME_RESEARCH_SUBAGENT,
        system_prompt=RESEARCH_SUBAGENT_SYSTEM_PROMPT,
    )

    assistant_text = result.assistant_message.content or ""

    report_raw: dict[str, Any] | None = None
    exp_result = await db.execute(
        select(Experiment)
        .options(selectinload(Experiment.validation_report))
        .where(Experiment.id == experiment.id)
    )
    exp = exp_result.scalar_one_or_none()
    if exp is not None and exp.validation_report is not None:
        raw = exp.validation_report.raw_report
        if isinstance(raw, dict):
            report_raw = raw
        if exp.evidence_thread_id is not None:
            experiment.evidence_thread_id = exp.evidence_thread_id

    return {
        "assistant_text_with_citations": assistant_text,
        "source_refs": build_source_refs_from_evidence_text(assistant_text, report_raw),
    }
