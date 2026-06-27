"""Pydantic response schemas for admin cost rollup endpoints."""

from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ExperimentCostResponse(BaseModel):
    """Cost rollup for a single experiment."""

    model_config = ConfigDict(from_attributes=True)

    experiment_id: UUID
    llm_cost_usd: Decimal
    external_api_cost_usd: Decimal
    total_cost_usd: Decimal
    llm_call_count: int
    external_api_call_count: int
    products: list["ProductCostRow"] = []


class UserCostResponse(BaseModel):
    """Cost rollup across all of a user's experiments."""

    model_config = ConfigDict(from_attributes=True)

    user_id: UUID
    llm_cost_usd: Decimal
    external_api_cost_usd: Decimal
    total_cost_usd: Decimal
    llm_call_count: int
    external_api_call_count: int


class DailyCostRow(BaseModel):
    """Cost totals for a single calendar day."""

    day: date
    llm_cost_usd: Decimal
    external_api_cost_usd: Decimal
    tavily_cost_usd: Decimal
    total_cost_usd: Decimal
    llm_call_count: int
    external_api_call_count: int


class DailyCostResponse(BaseModel):
    """Daily cost rollup for the last N days."""

    days_back: int
    rows: list[DailyCostRow]


class PhaseCostRow(BaseModel):
    """LLM cost totals for a single workflow phase."""

    phase: str | None  # NULL phase rows are grouped as None
    llm_cost_usd: Decimal
    call_count: int


class PerPhaseCostResponse(BaseModel):
    """Per-phase LLM cost breakdown for the last N days."""

    days_back: int
    rows: list[PhaseCostRow]


class ProductCostRow(BaseModel):
    """LLM + external API cost totals for one founder-journey product."""

    cost_category: str
    label: str
    llm_cost_usd: Decimal
    external_api_cost_usd: Decimal
    total_cost_usd: Decimal
    llm_call_count: int
    external_api_call_count: int


class PerProductCostResponse(BaseModel):
    """Per-product cost breakdown for the last N days."""

    days_back: int
    rows: list[ProductCostRow]


class ExperimentCostStatsRow(BaseModel):
    """Distribution of per-experiment spend in a period."""

    experiment_count: int
    avg_cost_usd: Decimal
    min_cost_usd: Decimal
    max_cost_usd: Decimal
    median_cost_usd: Decimal


class CostSummaryResponse(BaseModel):
    """High-level platform spend summary."""

    days_back: int
    total_cost_usd: Decimal
    llm_cost_usd: Decimal
    external_api_cost_usd: Decimal
    tavily_logged_cost_usd: Decimal
    tavily_estimated_gap_usd: Decimal
    tavily_total_cost_usd: Decimal
    tavily_logged_credits: int
    tavily_estimated_gap_credits: int
    tavily_unlogged_experiment_count: int
    llm_call_count: int
    external_api_call_count: int
    active_user_count: int
    experiment_stats: ExperimentCostStatsRow
    target_cost_per_experiment_usd: Decimal = Decimal("1.50")
    tavily_usd_per_credit: Decimal = Decimal("0.008")


class UserCostInsightRow(BaseModel):
    """Per-user spend rollup for admin dashboards."""

    user_id: UUID
    email: str
    name: str | None
    experiment_count: int
    llm_cost_usd: Decimal
    external_api_cost_usd: Decimal
    total_cost_usd: Decimal
    llm_call_count: int
    external_api_call_count: int


class PerUserCostResponse(BaseModel):
    days_back: int
    rows: list[UserCostInsightRow]


class ProviderCostRow(BaseModel):
    """Spend for one provider (LLM or external API)."""

    provider: str
    source: str
    cost_usd: Decimal
    call_count: int


class PerProviderCostResponse(BaseModel):
    days_back: int
    rows: list[ProviderCostRow]


class TopExperimentCostRow(BaseModel):
    experiment_id: UUID
    label: str
    total_cost_usd: Decimal
    llm_cost_usd: Decimal
    external_api_cost_usd: Decimal


class CostInsightsResponse(BaseModel):
    """Bundled admin dashboard payload."""

    days_back: int
    summary: CostSummaryResponse
    per_user: list[UserCostInsightRow]
    per_provider: list[ProviderCostRow]
    per_phase: list[PhaseCostRow]
    top_experiments: list[TopExperimentCostRow]


class ExperimentPhaseCostRow(BaseModel):
    """Cost for one workflow phase within a project."""

    phase: str
    label: str
    source: str
    cost_usd: Decimal
    call_count: int


class UserExperimentCostRow(BaseModel):
    """Per-project cost rollup with phase breakdown."""

    experiment_id: UUID
    label: str
    name: str | None
    status: str
    total_cost_usd: Decimal
    llm_cost_usd: Decimal
    external_api_cost_usd: Decimal
    phases: list[ExperimentPhaseCostRow]


class UserExperimentsCostResponse(BaseModel):
    """All projects for a user with per-phase spend."""

    user_id: UUID
    email: str
    name: str | None
    days_back: int
    experiments: list[UserExperimentCostRow]
