"""Unit tests for app.services.error_translation (planning §5.1)."""

from __future__ import annotations

from app.db.enums import ExperimentStatus
from app.services.error_translation import (
    UserFacingError,
    translate_engineer_error,
)

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


def test_tavily_rate_limit_from_searcher_failure_detail() -> None:
    detail = (
        "searcher:SearcherFailure: All 14 Tavily searches failed across 7 questions. "
        "First error: RateLimitError: 429 too many requests"
    )
    result = translate_engineer_error("SearcherFailure", detail)
    assert result == UserFacingError(_MSG_TAVILY_RATE_LIMIT, "retry_pipeline")


def test_tavily_all_failed_from_searcher_failure_class() -> None:
    detail = (
        "searcher:SearcherFailure: All 10 Tavily searches failed across 5 questions. "
        "First error: RuntimeError: connection reset"
    )
    result = translate_engineer_error("SearcherFailure", detail)
    assert result == UserFacingError(_MSG_TAVILY_ALL_FAILED, "retry_pipeline")


def test_planner_llm_error_from_sanitized_detail() -> None:
    detail = "planner:InstructorRetryException: failed to parse ResearchPlan after retries"
    result = translate_engineer_error("InstructorRetryException", detail)
    assert result == UserFacingError(_MSG_PLANNER_LLM, "retry_pipeline")


def test_synthesizer_hallucinated_citation_by_class_name() -> None:
    detail = (
        "synthesizer:SynthesizerHallucinatedCitation: URL https://evil.example "
        "not in validated evidence URLs"
    )
    result = translate_engineer_error("SynthesizerHallucinatedCitation", detail)
    assert result == UserFacingError(
        _MSG_SYNTHESIZER_HALLUCINATED_CITATION, "retry_pipeline"
    )


def test_quote_hallucination_rate_exceeded_when_research_ready() -> None:
    detail = "reader: quote_hallucination_rate exceeded threshold (0.12 > 0.10)"
    result = translate_engineer_error(
        None,
        detail,
        experiment_status=ExperimentStatus.RESEARCH_READY,
    )
    assert result == UserFacingError(_MSG_QUOTE_HALLUCINATION_READY, "none")


def test_cost_ceiling_from_detail_substring() -> None:
    detail = "pipeline:RuntimeError: experiment cost ceiling $4.50 exceeded"
    result = translate_engineer_error(None, detail)
    assert result == UserFacingError(_MSG_COST_CEILING, "retry_pipeline")


def test_refinement_llm_timeout() -> None:
    detail = "refinement:APITimeoutError: request timed out after 120s"
    result = translate_engineer_error("APITimeoutError", detail)
    assert result == UserFacingError(_MSG_REFINEMENT_TIMEOUT, "retry_refinement_turn")


def test_refinement_validation_error() -> None:
    detail = "refinement:ValidationError: assistant_message must end with ?"
    result = translate_engineer_error("ValidationError", detail)
    assert result == UserFacingError(_MSG_REFINEMENT_VALIDATION, "retry_refinement_turn")


def test_dispatch_error_maps_to_catch_all() -> None:
    result = translate_engineer_error(
        "DispatchError",
        "Failed to schedule research pipeline",
    )
    assert result == UserFacingError(_MSG_CATCH_ALL, "retry_pipeline")


def test_catch_all_unknown_class_and_empty_detail() -> None:
    result = translate_engineer_error("TotallyUnknownError", None)
    assert result == UserFacingError(_MSG_CATCH_ALL, "retry_pipeline")


def test_substring_matching_is_case_insensitive() -> None:
    detail = "SEARCHER:SearcherFailure: ALL 2 TAVILY SEARCHES FAILED across 1 questions"
    result = translate_engineer_error(None, detail)
    assert result == UserFacingError(_MSG_TAVILY_ALL_FAILED, "retry_pipeline")


def test_error_class_name_takes_precedence_over_conflicting_detail_substring() -> None:
    detail = (
        "synthesizer:SynthesizerHallucinatedCitation: upstream 429 rate limit on tavily"
    )
    result = translate_engineer_error("SynthesizerHallucinatedCitation", detail)
    assert result == UserFacingError(
        _MSG_SYNTHESIZER_HALLUCINATED_CITATION, "retry_pipeline"
    )


def test_quote_hallucination_not_matched_when_not_research_ready() -> None:
    detail = "reader: quote_hallucination_rate exceeded threshold"
    result = translate_engineer_error(
        None,
        detail,
        experiment_status=ExperimentStatus.RESEARCH_FAILED,
    )
    assert result == UserFacingError(_MSG_CATCH_ALL, "retry_pipeline")
