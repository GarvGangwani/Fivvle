"""Build compressed experiment context for post-research chat discussion."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.experiment import Experiment
from app.db.models.page_view import PageView
from app.db.models.waitlist_signup import WaitlistSignup
from app.schemas.refinement import RefinedIdea
from app.services.analytics_aggregator import (
    LandingPageNotLiveError,
    build_analytics_aggregate,
)

_MAX_CONTEXT_CHARS = 6000


def _truncate(text: str, max_len: int) -> str:
    if len(text) <= max_len:
        return text
    return text[: max_len - 3].rstrip() + "..."


def _compress_validation_report(raw: dict) -> str:
    lines: list[str] = []

    executive = raw.get("executive_summary")
    if isinstance(executive, str) and executive.strip():
        lines.append(f"Executive summary: {_truncate(executive.strip(), 600)}")

    market = raw.get("market_signals")
    if isinstance(market, str) and market.strip():
        lines.append(f"Market signals: {_truncate(market.strip(), 400)}")

    rec = raw.get("overall_recommendation")
    if rec is not None:
        lines.append(f"Overall recommendation: {rec}")

    findings: list[str] = []
    for qf in raw.get("questions_and_findings") or []:
        for finding in qf.get("findings") or []:
            claim = finding.get("claim")
            if isinstance(claim, str) and claim.strip():
                findings.append(_truncate(claim.strip(), 200))
            if len(findings) >= 3:
                break
        if len(findings) >= 3:
            break
    if findings:
        lines.append("Top findings:")
        for idx, claim in enumerate(findings, start=1):
            lines.append(f"  {idx}. {claim}")

    risks_assessment = raw.get("risks_assessment")
    if isinstance(risks_assessment, str) and risks_assessment.strip():
        lines.append(f"Risks assessment: {_truncate(risks_assessment.strip(), 500)}")

    return "\n".join(lines) if lines else "Validation report exists but has no readable summary."


async def _landing_metrics_block(
    db: AsyncSession,
    experiment_id: UUID,
) -> str | None:
    try:
        agg = await build_analytics_aggregate(db, experiment_id)
    except LandingPageNotLiveError:
        pv_count = await db.scalar(
            select(func.count())
            .select_from(PageView)
            .where(PageView.experiment_id == experiment_id)
        )
        signup_count = await db.scalar(
            select(func.count())
            .select_from(WaitlistSignup)
            .where(WaitlistSignup.experiment_id == experiment_id)
        )
        if not pv_count and not signup_count:
            return None
        return (
            f"Landing page metrics (draft/unpublished): "
            f"{pv_count or 0} page views, {signup_count or 0} signups"
        )

    rate_pct = round(agg.conversion_rate * 100, 2)
    return (
        f"Landing page metrics: {agg.total_page_views} total views, "
        f"{agg.total_signups} signups, {rate_pct}% conversion rate"
    )


async def build_experiment_discussion_context(
    db: AsyncSession,
    experiment: Experiment,
) -> str:
    """Compressed context block for chat_discussion_v1 system/user prompts."""
    result = await db.execute(
        select(Experiment)
        .options(
            selectinload(Experiment.validation_report),
            selectinload(Experiment.landing_page),
        )
        .where(Experiment.id == experiment.id)
    )
    exp = result.scalar_one()
    sections: list[str] = [f"Experiment status: {exp.status.value}"]

    if exp.refined_idea:
        idea = RefinedIdea.model_validate(exp.refined_idea)
        sections.append(
            "Refined idea:\n"
            f"- Headline: {idea.headline}\n"
            f"- One-liner: {idea.refined_one_liner}\n"
            f"- Target audience: {idea.target_audience}\n"
            f"- Value proposition: {idea.value_proposition}"
        )
        if idea.risks:
            top_risks = idea.risks[:3]
            sections.append("Top risks from refinement:\n" + "\n".join(f"- {r}" for r in top_risks))
    else:
        sections.append(f"Raw idea: {_truncate(exp.raw_idea.strip(), 500)}")

    if exp.validation_report is not None:
        sections.append(
            "Validation report (compressed):\n"
            + _compress_validation_report(exp.validation_report.raw_report)
        )
    else:
        sections.append("Validation report: not available yet.")

    if exp.landing_page is not None:
        lp = exp.landing_page
        live_label = "live" if lp.live_at is not None else "draft"
        sections.append(
            f"Landing page: {live_label} (template: {lp.template_id}, slug: {lp.slug})"
        )
        metrics = await _landing_metrics_block(db, exp.id)
        if metrics:
            sections.append(metrics)
    else:
        sections.append("Landing page: not generated yet.")

    context = "\n\n".join(sections)
    return _truncate(context, _MAX_CONTEXT_CHARS)
