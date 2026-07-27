"""Tests for LandingPageV2Spec cascade stamp columns (PR-4 Step 1)."""

from __future__ import annotations

from sqlalchemy import Integer
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from app.db.models.landing_page import LandingPage
from app.db.models.landing_page_v2 import LandingPageV2Spec


def test_landing_page_v2_has_stamp_attributes() -> None:
    assert hasattr(LandingPageV2Spec, "spark_version_id")
    assert hasattr(LandingPageV2Spec, "refined_idea_version")
    assert hasattr(LandingPageV2Spec, "edited_doc_version")


def test_landing_page_v2_stamp_columns_nullable() -> None:
    cols = LandingPageV2Spec.__table__.columns
    assert cols["spark_version_id"].nullable is True
    assert cols["refined_idea_version"].nullable is True
    assert cols["edited_doc_version"].nullable is True
    assert isinstance(cols["spark_version_id"].type, PG_UUID)
    assert isinstance(cols["refined_idea_version"].type, Integer)
    assert isinstance(cols["edited_doc_version"].type, Integer)


def test_landing_page_v2_spark_fk_matches_v1_pattern() -> None:
    """spark_version_id FK target and ondelete must match LandingPage (v1)."""
    v1_col = LandingPage.__table__.columns["spark_version_id"]
    v2_col = LandingPageV2Spec.__table__.columns["spark_version_id"]
    v1_fks = list(v1_col.foreign_keys)
    v2_fks = list(v2_col.foreign_keys)
    assert len(v1_fks) == 1 and len(v2_fks) == 1
    assert v1_fks[0].column.table.name == "experiment_spark_versions"
    assert v2_fks[0].column.table.name == "experiment_spark_versions"
    assert v1_fks[0].ondelete == v2_fks[0].ondelete
