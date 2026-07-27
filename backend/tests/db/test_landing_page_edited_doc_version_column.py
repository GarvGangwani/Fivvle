"""Tests for LandingPage.edited_doc_version column (PR-2 Step 2)."""

from __future__ import annotations

from sqlalchemy import Integer

from app.db.models.landing_page import LandingPage


def test_landing_page_has_edited_doc_version_attribute() -> None:
    assert hasattr(LandingPage, "edited_doc_version")


def test_edited_doc_version_column_is_nullable_integer() -> None:
    col = LandingPage.__table__.columns["edited_doc_version"]
    assert isinstance(col.type, Integer)
    assert col.nullable is True
