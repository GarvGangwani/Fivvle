"""Shared ValidationReport bundle for landing-page generators (v1 and v2)."""

from __future__ import annotations

from dataclasses import dataclass

from app.schemas.validation_report import ValidationReport


@dataclass(frozen=True, slots=True)
class ValidationReportForLanding:
    """Parsed raw_report plus optional founder-edited narrative for strategist."""

    report: ValidationReport
    edited_narrative: str | None
    edited_doc_version: int | None
