"""Pydantic schemas for admin coupon management."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _normalize_coupon_code(value: str) -> str:
    normalized = value.strip().upper()
    if not normalized:
        raise ValueError("Coupon code cannot be empty.")
    if len(normalized) > 64:
        raise ValueError("Coupon code must be at most 64 characters.")
    return normalized


class AdminCouponCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=1, max_length=64)
    credits: int = Field(gt=0, le=100_000)
    enabled: bool = True
    max_redemptions: int | None = Field(default=None, ge=1)
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    limit_reached_message: str | None = Field(default=None, max_length=500)
    not_yet_active_message: str | None = Field(default=None, max_length=500)
    expired_message: str | None = Field(default=None, max_length=500)
    disabled_message: str | None = Field(default=None, max_length=500)

    @field_validator("code")
    @classmethod
    def validate_code(cls, value: str) -> str:
        return _normalize_coupon_code(value)


class AdminCouponUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    credits: int | None = Field(default=None, gt=0, le=100_000)
    enabled: bool | None = None
    max_redemptions: int | None = Field(default=None, ge=1)
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    clear_starts_at: bool = False
    clear_ends_at: bool = False
    limit_reached_message: str | None = Field(default=None, max_length=500)
    not_yet_active_message: str | None = Field(default=None, max_length=500)
    expired_message: str | None = Field(default=None, max_length=500)
    disabled_message: str | None = Field(default=None, max_length=500)
    clear_limit_reached_message: bool = False
    clear_not_yet_active_message: bool = False
    clear_expired_message: bool = False
    clear_disabled_message: bool = False


class AdminCouponSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    code: str
    credits: int
    enabled: bool
    archived_at: datetime | None
    max_redemptions: int | None
    redemption_count: int = Field(ge=0)
    remaining_redemptions: int | None = None
    total_credits_gifted: int = Field(ge=0)
    total_usd_gifted: str
    starts_at: datetime | None
    ends_at: datetime | None
    limit_reached_message: str | None
    not_yet_active_message: str | None
    expired_message: str | None
    disabled_message: str | None
    created_at: datetime
    updated_at: datetime


class AdminCouponListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    coupons: list[AdminCouponSummary]
    total_usd_gifted_all_coupons: str
