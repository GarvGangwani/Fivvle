"""Tests for landing_page_publishes table and publish_id FKs (PR-3 Step 1)."""

from __future__ import annotations

from sqlalchemy import Integer, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from app.db.models.insight_report import InsightReport
from app.db.models.landing_page import LandingPage
from app.db.models.landing_page_publish import LandingPagePublish
from app.db.models.page_view import PageView
from app.db.models.waitlist_signup import WaitlistSignup


def test_landing_page_publish_table_columns() -> None:
    cols = LandingPagePublish.__table__.columns
    assert isinstance(cols["id"].type, PG_UUID)
    assert cols["landing_page_id"].nullable is False
    assert isinstance(cols["publish_number"].type, Integer)
    assert cols["published_at"].nullable is False
    assert cols["ended_at"].nullable is True


def test_landing_page_publish_unique_constraint() -> None:
    uniques = [
        c
        for c in LandingPagePublish.__table__.constraints
        if isinstance(c, UniqueConstraint)
    ]
    named = {c.name: c for c in uniques}
    assert "uq_landing_page_publishes_landing_number" in named
    uq = named["uq_landing_page_publishes_landing_number"]
    assert {col.name for col in uq.columns} == {"landing_page_id", "publish_number"}


def test_landing_page_publish_landing_page_fk_cascades() -> None:
    col = LandingPagePublish.__table__.columns["landing_page_id"]
    fks = list(col.foreign_keys)
    assert len(fks) == 1
    assert fks[0].column.table.name == "landing_pages"
    assert fks[0].ondelete == "CASCADE"


def test_landing_page_publish_landing_page_id_indexed() -> None:
    indexes = {idx.name for idx in LandingPagePublish.__table__.indexes}
    assert "ix_landing_page_publishes_landing_page_id" in indexes


def test_landing_page_has_publishes_relationship() -> None:
    assert hasattr(LandingPage, "publishes")


def test_page_view_publish_id_fk_cascades() -> None:
    col = PageView.__table__.columns["publish_id"]
    assert col.nullable is True
    fks = list(col.foreign_keys)
    assert len(fks) == 1
    assert fks[0].column.table.name == "landing_page_publishes"
    assert fks[0].ondelete == "CASCADE"
    indexes = {idx.name for idx in PageView.__table__.indexes}
    assert "ix_page_views_publish_id" in indexes


def test_waitlist_signup_publish_id_fk_cascades() -> None:
    col = WaitlistSignup.__table__.columns["publish_id"]
    assert col.nullable is True
    fks = list(col.foreign_keys)
    assert len(fks) == 1
    assert fks[0].column.table.name == "landing_page_publishes"
    assert fks[0].ondelete == "CASCADE"
    indexes = {idx.name for idx in WaitlistSignup.__table__.indexes}
    assert "ix_waitlist_signups_publish_id" in indexes


def test_insight_report_publish_id_fk_set_null() -> None:
    col = InsightReport.__table__.columns["publish_id"]
    assert col.nullable is True
    fks = list(col.foreign_keys)
    assert len(fks) == 1
    assert fks[0].column.table.name == "landing_page_publishes"
    assert fks[0].ondelete == "SET NULL"
