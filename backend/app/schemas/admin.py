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
