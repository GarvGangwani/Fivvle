"""Tests for InsightReport.raw_output JSONB column (B4 Step 0)."""

from __future__ import annotations

from sqlalchemy.dialects.postgresql import JSONB

from app.db.models.insight_report import InsightReport


def test_insight_report_has_raw_output_attribute() -> None:
    assert hasattr(InsightReport, "raw_output")


def test_raw_output_column_type_is_jsonb() -> None:
    col_type = InsightReport.__table__.columns["raw_output"].type
    assert isinstance(col_type, JSONB)


def test_raw_output_column_is_nullable() -> None:
    assert InsightReport.__table__.columns["raw_output"].nullable is True
