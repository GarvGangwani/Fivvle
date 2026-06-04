"""Pydantic response schemas for admin chat-quality observability endpoints."""

from pydantic import BaseModel, Field


class RefinementTurnCountDistributionResponse(BaseModel):
    """Refinement turn-count histogram (keys 0–3; 3 means 3+)."""

    distribution: dict[int, int] = Field(
        description="Bucketed refinement_count → experiment count (3 = three or more turns)",
    )


class UserReplyLengthStatsResponse(BaseModel):
    """Aggregate char lengths of user replies following a clarifying assistant turn."""

    median: int
    p90: int
    count: int
    max: int


class DispatchLatencyStatsResponse(BaseModel):
    """Dispatch-to-completion latency in seconds for finished research pipelines."""

    median_seconds: int
    p90_seconds: int
    count: int


class DispatchTriggerRatioResponse(BaseModel):
    """Experiment counts by dispatch_trigger."""

    user_confirm: int
    auto_fire: int


class FirstTurnDimensionDistributionResponse(BaseModel):
    """clarifying_dimension on the first refinement_clarify assistant turn per experiment."""

    distribution: dict[str, int]
