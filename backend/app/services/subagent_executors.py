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
    format_sources_block,
)
from app.logging_config import get_logger
from app.services import chat_service
from app.services.evidence_chat_service import send_evidence_chat_message

_logger = get_logger(__name__)

# Rail research cites primary sources as [cite:sN] (not full URLs / [ref:]).
_CITE_SOURCE_ID_RE = re.compile(r"\[cite:\s*(s\d+)\]", re.IGNORECASE)

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


def _domain_from_url(url: str) -> str:
    try:
        from urllib.parse import urlparse

        host = urlparse(url).netloc.lower()
        if host.startswith("www."):
            host = host[4:]
        return host or url
    except Exception:
        return url


def _iter_report_citations(report: dict[str, Any]) -> list[dict[str, str]]:
    """Collect Citation-shaped dicts from findings + competitors (dedupe by URL)."""
    collected: list[dict[str, str]] = []
    seen_urls: set[str] = set()

    def _add(cite: Any) -> None:
        if not isinstance(cite, dict):
            return
        url = cite.get("url")
        if not isinstance(url, str) or not url.strip():
            return
        url = url.strip()
        if url in seen_urls:
            return
        seen_urls.add(url)
        title = cite.get("title")
        domain = cite.get("source_domain")
        collected.append(
            {
                "source_title": title.strip()
                if isinstance(title, str) and title.strip()
                else url,
                "source_url": url,
                "source_domain": domain.strip()
                if isinstance(domain, str) and domain.strip()
                else _domain_from_url(url),
            }
        )

    for qf in report.get("questions_and_findings") or []:
        if not isinstance(qf, dict):
            continue
        for finding in qf.get("findings") or []:
            if not isinstance(finding, dict):
                continue
            for cite in finding.get("citations") or []:
                _add(cite)

    for comp in report.get("competitors") or []:
        if not isinstance(comp, dict):
            continue
        for cite in comp.get("citations") or []:
            _add(cite)

    return collected


def build_source_index(
    report: dict[str, Any] | None,
) -> dict[str, dict[str, str | None]]:
    """Map ``s1``..``sN`` -> primary source metadata from the validation report."""
    if not report:
        return {}
    index: dict[str, dict[str, str | None]] = {}
    for i, cite in enumerate(_iter_report_citations(report), start=1):
        source_id = f"s{i}"
        index[source_id] = {
            "source_title": cite["source_title"],
            "source_url": cite["source_url"],
            "source_domain": cite["source_domain"],
        }
    return index


def build_source_refs_from_cite_ids(
    text: str,
    source_index: dict[str, dict[str, str | None]],
) -> list[dict[str, Any]]:
    """Resolve in-content ``[cite:sN]`` markers via ``source_index``.

    Unresolved ids and ``[ref:...]`` markers are dropped (frontend shows them
    as plain text).
    """
    refs: list[dict[str, Any]] = []
    seen: set[str] = set()
    for match in _CITE_SOURCE_ID_RE.finditer(text):
        source_id = match.group(1).lower()
        if source_id in seen:
            continue
        meta = source_index.get(source_id)
        if meta is None:
            continue
        seen.add(source_id)
        marker_id = f"[cite:{source_id}]"
        refs.append(
            {
                "marker_id": marker_id,
                "source_title": meta.get("source_title") or source_id,
                "source_url": meta.get("source_url"),
                "source_domain": meta.get("source_domain"),
            }
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

    source_index = build_source_index(report_raw)
    sources_block = format_sources_block(source_index)

    result = await send_evidence_chat_message(
        db,
        current_user=user,
        experiment_id=experiment.id,
        message=query,
        prompt_name=PROMPT_NAME_RESEARCH_SUBAGENT,
        system_prompt=RESEARCH_SUBAGENT_SYSTEM_PROMPT,
        sources_block=sources_block,
    )

    assistant_text = result.assistant_message.content or ""

    if exp is not None and exp.evidence_thread_id is not None:
        experiment.evidence_thread_id = exp.evidence_thread_id
    else:
        refreshed = await db.get(Experiment, experiment.id)
        if refreshed is not None and refreshed.evidence_thread_id is not None:
            experiment.evidence_thread_id = refreshed.evidence_thread_id

    return {
        "assistant_text_with_citations": assistant_text,
        "source_refs": build_source_refs_from_cite_ids(assistant_text, source_index),
    }
