"""Insight service — wraps the LLM insight-synthesis call.

Single public function: generate_insight_report().

Called by the insight Cloud Function (Step 7). Reads Experiment + ValidationReport,
builds AnalyticsAggregate via analytics_aggregator, calls Kimi with the
insight_v1_cached prompt, validates that every cited finding ID exists, and
persists an InsightReport row. Does NOT change experiment status — that lives
in the Cloud Function per the synthesizer_service precedent.

Citation validation: every cited_finding_ids entry in research_takeaways must
match the positional ID set computed by app.llm.prompts.insight._compute_finding_ids
(scheme: "{question_id}.f{idx}"). On hallucination, retries ONCE with feedback
prepended to the user prompt naming the invalid IDs and the valid set. If the
second attempt also hallucinates, raises InsightCitationHallucinatedError —
the Cloud Function maps this to status=INSIGHT_FAILED.

Per .cursorrules: imports complete_structured from app.llm.client. Does NOT
import anthropic / kimi clients directly.

Per AGENTS.md logging hygiene: NEVER log InsightReportOutputDraft content,
ValidationReport content, AnalyticsAggregate content, or PII. Log only
aggregate counts and flags (experiment_id, finding_count, retry_count,
recommendation_type, cost, latency).
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import app.llm.client as llm_client
from app.config import get_settings
from app.db.models.insight_report import InsightReport
from app.db.models.validation_report import ValidationReport as ValidationReportRow
from app.llm.prompts.insight import (
    INSIGHT_SYSTEM_PROMPT,
    PROMPT_NAME,
    _compute_finding_ids,
    build_insight_user_prompt,
)
from app.logging_config import get_logger
from app.schemas.insight import InsightReportOutputDraft
from app.schemas.validation_report import ValidationReport
from app.services.analytics_aggregator import build_analytics_aggregate

_logger = get_logger(__name__)

INSIGHT_CACHE_BREAKPOINTS: list[llm_client.CacheBreakpoint] = [
    llm_client.CacheBreakpoint(position="user_zone_a_end", ttl="1h"),
    llm_client.CacheBreakpoint(position="user_zone_b_end", ttl="5m"),
]

# 8192 tokens is comfortable for a single-call structured insight report.
# Empirically tighter than synthesizer's 16384 because insight has fewer
# nested objects and no parallel question fan-out.
_INSIGHT_MAX_TOKENS = 8192

# 0.6 — Kimi k2.6 requires temperature=0.6 when thinking is disabled (ADR 0018).
# The LLM client also forces this internally; setting it here keeps the intent explicit.
_INSIGHT_TEMPERATURE = 0.6


class MissingValidationReportError(Exception):  # noqa: N818
    """Raised when generate_insight_report cannot find a ValidationReport row
    for the experiment. Indicates upstream pipeline failure — should not occur
    in normal flow (Stage 6 presumes RESEARCH_READY → LANDING_LIVE → ANALYZING).
    """


class InsightCitationHallucinatedError(Exception):  # noqa: N818
    """Raised when the LLM cites finding IDs that don't exist in the
    ValidationReport, AFTER one retry with explicit feedback.

    Hard quality failure — the Cloud Function maps this to status=INSIGHT_FAILED.
    """

    def __init__(
        self,
        invalid_ids: set[str],
        valid_ids: set[str],
        *,
        experiment_id: UUID,
    ) -> None:
        self.invalid_ids = invalid_ids
        self.valid_ids = valid_ids
        self.experiment_id = experiment_id
        super().__init__(
            f"Insight LLM cited finding IDs not in ValidationReport: "
            f"{sorted(invalid_ids)}. Valid set had {len(valid_ids)} entries. "
            f"Experiment {experiment_id}."
        )


def _collect_cited_finding_ids(draft: InsightReportOutputDraft) -> set[str]:
    """Flatten all cited_finding_ids across every research_takeaway."""
    return {fid for tk in draft.research_takeaways for fid in tk.cited_finding_ids}


def _find_invalid_finding_ids(
    draft: InsightReportOutputDraft, valid_ids: set[str]
) -> set[str]:
    cited = _collect_cited_finding_ids(draft)
    return cited - valid_ids


def _build_retry_user_prompt(
    base_user_prompt: str,
    invalid_ids: set[str],
    valid_ids: set[str],
) -> str:
    """Append corrective feedback to the original user prompt and return the new prompt.

    The feedback is added AFTER Zone C so the LLM sees the original three zones
    intact (preserving cache hits for Zones A and B) plus a final corrective block.
    """
    feedback = (
        "\n\n<previous_attempt_feedback>\n"
        f"Your previous response cited finding IDs that do NOT exist in the "
        f"ValidationReport: {sorted(invalid_ids)}.\n"
        f"The ONLY valid finding IDs are listed in <finding_id_directory> above.\n"
        f"For reference, the valid set is: {sorted(valid_ids)}.\n"
        "Re-emit the entire InsightReportOutputDraft. Every cited_finding_ids "
        "value MUST appear in the directory. Do not invent IDs. Do not cite URLs.\n"
        "</previous_attempt_feedback>\n"
    )
    return base_user_prompt + feedback


async def _fetch_validation_report(
    db: AsyncSession, experiment_id: UUID
) -> ValidationReport:
    """Fetch the ValidationReport DB row and parse the raw_report JSONB
    into the Pydantic ValidationReport. Raises MissingValidationReportError
    if no row exists.
    """
    stmt = select(ValidationReportRow).where(
        ValidationReportRow.experiment_id == experiment_id
    )
    result = await db.execute(stmt)
    row = result.scalar_one_or_none()
    if row is None or row.raw_report is None:
        raise MissingValidationReportError(
            f"No ValidationReport found for experiment {experiment_id}"
        )
    return ValidationReport.model_validate(row.raw_report)


def _compute_valid_finding_id_set(vr: ValidationReport) -> set[str]:
    """Same scheme as app.llm.prompts.insight._compute_finding_ids — wrapped
    as a set for O(1) membership checks. Importing _compute_finding_ids keeps
    the scheme co-located in the prompts module."""
    return {fid for fid, _ in _compute_finding_ids(vr)}


def _persist_insight_row(
    db: AsyncSession,
    *,
    experiment_id: UUID,
    draft: InsightReportOutputDraft,
) -> InsightReport:
    """Build an InsightReport ORM instance from the draft and add it to the session.

    raw_output stores the full draft dump; the scalar JSONB columns store the
    queryable subsets per planning doc §4.2.
    """
    row = InsightReport(
        experiment_id=experiment_id,
        traffic_summary=draft.traffic_summary.model_dump(mode="json"),
        conversion_by_source=draft.conversion_by_source.model_dump(mode="json"),
        research_takeaways={
            "items": [tk.model_dump(mode="json") for tk in draft.research_takeaways]
        },
        recommendation=draft.recommendation,
        recommendation_type=draft.recommendation_type,
        raw_output=draft.model_dump(mode="json"),
    )
    db.add(row)
    return row


async def generate_insight_report(
    db: AsyncSession,
    experiment_id: UUID,
) -> InsightReport:
    """Build and persist an InsightReport for the given experiment.

    Pipeline:
      1. Fetch the parsed ValidationReport (raise if missing).
      2. Build the AnalyticsAggregate via analytics_aggregator.
      3. Build the Insight user prompt + valid_finding_ids set.
      4. Call Kimi (complete_structured) with insight_v1_cached prompt.
      5. Validate that every cited finding ID is in valid_finding_ids.
         On hallucination, retry ONCE with feedback. If the retry also
         hallucinates, raise InsightCitationHallucinatedError.
      6. Persist InsightReport row (raw_output + queryable JSONB columns +
         recommendation + recommendation_type). Caller commits the transaction.

    Returns the persisted (flushed but not committed) InsightReport ORM row.

    Does NOT change Experiment.status. Status transitions live in the caller
    (the insight Cloud Function in Step 7).

    Raises:
      MissingValidationReportError — no ValidationReport row for the experiment.
      LandingPageNotLiveError — propagated from analytics_aggregator.
      InsightCitationHallucinatedError — citation validation failed after retry.
      Exception — any LLM provider error propagates from complete_structured.
    """
    settings = get_settings()

    vr = await _fetch_validation_report(db, experiment_id)
    analytics = await build_analytics_aggregate(db, experiment_id)
    valid_ids = _compute_valid_finding_id_set(vr)

    base_user_prompt = build_insight_user_prompt(vr, analytics)
    user_prompt = base_user_prompt

    draft: InsightReportOutputDraft | None = None
    final_invalid_ids: set[str] = set()
    retry_count = 0

    for attempt in range(2):  # 1 initial + 1 retry on citation hallucination
        candidate_draft, _llm_result = await llm_client.complete_structured(
            db,
            provider=settings.insight_provider,
            model=settings.insight_model,
            prompt_name=PROMPT_NAME,
            system=INSIGHT_SYSTEM_PROMPT,
            user=user_prompt,
            response_model=InsightReportOutputDraft,
            max_tokens=_INSIGHT_MAX_TOKENS,
            temperature=_INSIGHT_TEMPERATURE,
            experiment_id=experiment_id,
            phase="insight",
            cache_breakpoints=INSIGHT_CACHE_BREAKPOINTS,
        )

        invalid_ids = _find_invalid_finding_ids(candidate_draft, valid_ids)
        if not invalid_ids:
            draft = candidate_draft
            break

        # Citation hallucination — retry with feedback if budget remains.
        if attempt == 0:
            retry_count = 1
            user_prompt = _build_retry_user_prompt(
                base_user_prompt, invalid_ids, valid_ids
            )
            _logger.warning(
                "insight citation hallucination — retrying with feedback",
                experiment_id=str(experiment_id),
                invalid_id_count=len(invalid_ids),
                valid_id_count=len(valid_ids),
            )
            continue

        # Second attempt also hallucinated. Hard fail.
        final_invalid_ids = invalid_ids
        break

    if draft is None:
        raise InsightCitationHallucinatedError(
            invalid_ids=final_invalid_ids,
            valid_ids=valid_ids,
            experiment_id=experiment_id,
        )

    row = _persist_insight_row(db, experiment_id=experiment_id, draft=draft)
    await db.flush()  # surface IntegrityError early; caller commits.

    _logger.info(
        "insight report generated",
        experiment_id=str(experiment_id),
        recommendation_type=draft.recommendation_type.value,
        finding_id_count=len(valid_ids),
        cited_finding_id_count=len(_collect_cited_finding_ids(draft)),
        takeaway_count=len(draft.research_takeaways),
        retry_count=retry_count,
    )

    return row
