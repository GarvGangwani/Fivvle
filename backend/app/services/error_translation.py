"""Map engineer-facing errors to user-facing chat messages (planning §5.1).

Pure translation layer — no DB, logging, or side effects. Step 5 wires this into
chat responses; callers pass ``research_error_detail`` and optional exception class.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.db.enums import ExperimentStatus

# §5.1 user-facing messages (verbatim).
_MSG_TAVILY_RATE_LIMIT = (
    "Search is busy right now. Try again in a couple of minutes?"
)
_MSG_TAVILY_ALL_FAILED = (
    "I couldn't get search results to back this up — usually transient. Retry?"
)
_MSG_PLANNER_LLM = (
    "I had trouble setting up the research questions. Let me try that again?"
)
_MSG_SYNTHESIZER_HALLUCINATED_CITATION = (
    "The research came back with sources I don't trust. "
    "Rather try again than show shaky."
)
_MSG_QUOTE_HALLUCINATION_READY = (
    "Some evidence came through fuzzy — research went through but flagged a few "
    "quotes. View report?"
)
_MSG_COST_CEILING = (
    "This run hit our budget cap — something went sideways. We're looking. Try again?"
)
_MSG_REFINEMENT_TIMEOUT = "Got tied up thinking — retry?"
_MSG_REFINEMENT_VALIDATION = (
    "Something didn't parse on my side. Try once more?"
)
_MSG_CATCH_ALL = (
    "Research didn't complete this time. Retry, or try a slightly different framing?"
)

_RETRY_PIPELINE = "retry_pipeline"
_RETRY_REFINEMENT_TURN = "retry_refinement_turn"
_RETRY_NONE = "none"

# Exception class names used in research_error_detail (phase:Type: message).
_PLANNER_LLM_CLASS_NAMES = frozenset(
    {
        "InstructorRetryException",
        "APITimeoutError",
        "RateLimitError",
        "TimeoutError",
        "APIError",
        "APIConnectionError",
        "ValidationError",
    }
)
_REFINEMENT_TIMEOUT_CLASS_NAMES = frozenset(
    {
        "RefinementTimeout",
        "APITimeoutError",
        "TimeoutError",
    }
)
_REFINEMENT_VALIDATION_CLASS_NAMES = frozenset(
    {
        "ValidationError",
        "InstructorRetryException",
    }
)
_TAVILY_RATE_LIMIT_CLASS_NAMES = frozenset({"Tavily429", "TavilyRateLimit"})


@dataclass(frozen=True)
class UserFacingError:
    message: str
    retry_action: Literal["retry_pipeline", "retry_refinement_turn", "none"]


def _phase_from_detail(error_detail: str | None) -> str | None:
    if not error_detail:
        return None
    segment = error_detail.split(":", 1)[0]
    return segment.lower() if segment else None


def _detail_lower(error_detail: str | None) -> str:
    return (error_detail or "").lower()


def _is_tavily_all_fail_detail(detail_lower: str) -> bool:
    return "all" in detail_lower and "tavily searches failed" in detail_lower


def _is_tavily_rate_limit_detail(detail_lower: str) -> bool:
    if "429" in detail_lower or "rate limit" in detail_lower:
        return True
    return "tavilyratelimit" in detail_lower.replace("_", "").replace(" ", "")


def _is_hallucinated_citation_detail(detail_lower: str) -> bool:
    return "hallucinat" in detail_lower and "citation" in detail_lower


def _is_cost_ceiling_detail(detail_lower: str) -> bool:
    return (
        "budget" in detail_lower
        or "cost ceiling" in detail_lower
        or "$4.5" in detail_lower
        or "4.50" in detail_lower
    )


def _is_quote_hallucination_ready(
    detail_lower: str,
    experiment_status: ExperimentStatus | None,
) -> bool:
    if experiment_status != ExperimentStatus.RESEARCH_READY:
        return False
    return "quote_hallucination" in detail_lower


def _is_refinement_context(
    *,
    error_class_name: str | None,
    error_detail: str | None,
) -> bool:
    if error_class_name == "RefinementTimeout":
        return True
    phase = _phase_from_detail(error_detail)
    if phase == "refinement":
        return True
    detail_lower = _detail_lower(error_detail)
    return "refinement:" in detail_lower or "refinement turn" in detail_lower


def _is_planner_context(error_detail: str | None) -> bool:
    return _phase_from_detail(error_detail) == "planner"


def _is_refinement_timeout(
    *,
    error_class_name: str | None,
    error_detail: str | None,
) -> bool:
    if not _is_refinement_context(
        error_class_name=error_class_name, error_detail=error_detail
    ):
        return False
    if error_class_name in _REFINEMENT_TIMEOUT_CLASS_NAMES:
        return True
    detail_lower = _detail_lower(error_detail)
    return "timeout" in detail_lower


def _is_refinement_validation(
    *,
    error_class_name: str | None,
    error_detail: str | None,
) -> bool:
    if not _is_refinement_context(
        error_class_name=error_class_name, error_detail=error_detail
    ):
        return False
    return error_class_name in _REFINEMENT_VALIDATION_CLASS_NAMES


def _match_by_class_name(
    error_class_name: str | None,
    error_detail: str | None,
) -> UserFacingError | None:
    if not error_class_name:
        return None

    if error_class_name == "SynthesizerHallucinatedCitation":
        return UserFacingError(
            _MSG_SYNTHESIZER_HALLUCINATED_CITATION, _RETRY_PIPELINE
        )

    if error_class_name == "SearcherFailure":
        detail_lower = _detail_lower(error_detail)
        if _is_tavily_rate_limit_detail(detail_lower):
            return UserFacingError(_MSG_TAVILY_RATE_LIMIT, _RETRY_PIPELINE)
        return UserFacingError(_MSG_TAVILY_ALL_FAILED, _RETRY_PIPELINE)

    if error_class_name in _TAVILY_RATE_LIMIT_CLASS_NAMES:
        return UserFacingError(_MSG_TAVILY_RATE_LIMIT, _RETRY_PIPELINE)

    if error_class_name == "TavilyAllFailed":
        return UserFacingError(_MSG_TAVILY_ALL_FAILED, _RETRY_PIPELINE)

    if error_class_name == "DispatchError":
        return UserFacingError(_MSG_CATCH_ALL, _RETRY_PIPELINE)

    if error_class_name in _PLANNER_LLM_CLASS_NAMES and _is_planner_context(
        error_detail
    ):
        return UserFacingError(_MSG_PLANNER_LLM, _RETRY_PIPELINE)

    if _is_refinement_timeout(
        error_class_name=error_class_name, error_detail=error_detail
    ):
        return UserFacingError(_MSG_REFINEMENT_TIMEOUT, _RETRY_REFINEMENT_TURN)

    if _is_refinement_validation(
        error_class_name=error_class_name, error_detail=error_detail
    ):
        return UserFacingError(_MSG_REFINEMENT_VALIDATION, _RETRY_REFINEMENT_TURN)

    return None


def _match_by_detail(
    error_detail: str | None,
    experiment_status: ExperimentStatus | None,
) -> UserFacingError | None:
    detail_lower = _detail_lower(error_detail)
    if not detail_lower:
        return None

    if _is_quote_hallucination_ready(detail_lower, experiment_status):
        return UserFacingError(_MSG_QUOTE_HALLUCINATION_READY, _RETRY_NONE)

    if _is_cost_ceiling_detail(detail_lower):
        return UserFacingError(_MSG_COST_CEILING, _RETRY_PIPELINE)

    if _is_hallucinated_citation_detail(detail_lower):
        return UserFacingError(
            _MSG_SYNTHESIZER_HALLUCINATED_CITATION, _RETRY_PIPELINE
        )

    if _is_tavily_all_fail_detail(detail_lower):
        return UserFacingError(_MSG_TAVILY_ALL_FAILED, _RETRY_PIPELINE)

    if _is_tavily_rate_limit_detail(detail_lower):
        return UserFacingError(_MSG_TAVILY_RATE_LIMIT, _RETRY_PIPELINE)

    if detail_lower.startswith("planner:"):
        return UserFacingError(_MSG_PLANNER_LLM, _RETRY_PIPELINE)

    if detail_lower.startswith("refinement:"):
        if "timeout" in detail_lower:
            return UserFacingError(_MSG_REFINEMENT_TIMEOUT, _RETRY_REFINEMENT_TURN)
        return UserFacingError(_MSG_REFINEMENT_VALIDATION, _RETRY_REFINEMENT_TURN)

    return None


def translate_engineer_error(
    error_class_name: str | None,
    error_detail: str | None,
    experiment_status: ExperimentStatus | None = None,
) -> UserFacingError:
    """Map an engineer-facing error to a user-facing chat message.

    error_class_name: exception class __name__ if known (e.g. "DispatchError")
    error_detail: the sanitized engineer message (typically experiment.research_error_detail)
    experiment_status: optional — RESEARCH_FAILED vs RESEARCH_READY may modify wording
    """
    by_class = _match_by_class_name(error_class_name, error_detail)
    if by_class is not None:
        return by_class

    by_detail = _match_by_detail(error_detail, experiment_status)
    if by_detail is not None:
        return by_detail

    return UserFacingError(_MSG_CATCH_ALL, _RETRY_PIPELINE)
