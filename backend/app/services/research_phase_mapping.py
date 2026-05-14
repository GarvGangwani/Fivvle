"""Research phase mapping — human-readable labels for ExperimentStatus values.

This module is the single source of truth for the phase strings shown to
founders on the research-in-progress screen (USER_FLOW Stage 2.4).

The label strings must match USER_FLOW.md exactly — the frontend renders them
verbatim.  Changes here require a corresponding frontend update.

B3 extension note:
    When Reader and Reflector phases land in B3, un-comment the RESEARCH_READING
    and RESEARCH_REFLECTING entries and remove the "Unreachable in B2" comments.
    The state machine will then flow:
        RESEARCH_SEARCHING → RESEARCH_READING → RESEARCH_REFLECTING → RESEARCH_SYNTHESIZING
    instead of the direct RESEARCH_SEARCHING → RESEARCH_SYNTHESIZING transition
    used in B2.4.
"""

from __future__ import annotations

from app.db.enums import ExperimentStatus

# ---------------------------------------------------------------------------
# Phase display labels
#
# Keys: every ExperimentStatus that can appear while research is in progress
#       (RESEARCHING through RESEARCH_READY / RESEARCH_FAILED).
# Values: the human-readable string shown in the research-in-progress UI.
#
# None means "no active phase label" — used for terminal states where the
# frontend shows a different component (report view or error screen).
# ---------------------------------------------------------------------------

PHASE_DISPLAY: dict[ExperimentStatus, str | None] = {
    ExperimentStatus.RESEARCHING: "Starting research...",
    ExperimentStatus.RESEARCH_PLANNING: "Planning your research questions...",
    ExperimentStatus.RESEARCH_SEARCHING: "Searching across sources...",
    # Unreachable in B2; B3 inserts these phases between SEARCHING and SYNTHESIZING.
    ExperimentStatus.RESEARCH_READING: "Reading and extracting evidence...",
    ExperimentStatus.RESEARCH_REFLECTING: "Reflecting on findings...",
    ExperimentStatus.RESEARCH_SYNTHESIZING: "Synthesizing the validation report...",
    # Terminal states — no phase label; frontend shows report or error screen.
    ExperimentStatus.RESEARCH_READY: None,
    ExperimentStatus.RESEARCH_FAILED: None,
}

# ---------------------------------------------------------------------------
# phases_completed — derived from current status
#
# Each entry lists the statuses that were successfully completed *before*
# reaching the current status.  Used by /research-status so the frontend
# can render a progress stepper without a separate audit log table.
#
# The ordering matches the B2.4 state machine:
#   RESEARCHING → RESEARCH_PLANNING → RESEARCH_SEARCHING
#               → RESEARCH_SYNTHESIZING → RESEARCH_READY
#
# RESEARCH_READING and RESEARCH_REFLECTING are listed for completeness (B3).
# ---------------------------------------------------------------------------

_RESEARCH_PHASE_ORDER: list[ExperimentStatus] = [
    ExperimentStatus.RESEARCHING,
    ExperimentStatus.RESEARCH_PLANNING,
    ExperimentStatus.RESEARCH_SEARCHING,
    # B3 will insert RESEARCH_READING and RESEARCH_REFLECTING here.
    ExperimentStatus.RESEARCH_SYNTHESIZING,
    ExperimentStatus.RESEARCH_READY,
]


def get_phases_completed(status: ExperimentStatus) -> list[ExperimentStatus]:
    """Return the list of phases completed before reaching the given status.

    For statuses not in the research flow (e.g. DRAFT) returns an empty list.
    For RESEARCH_FAILED, returns phases completed before the failure — i.e.
    all phases in the order up to (but not including) the current status.

    The result is used by /research-status to drive a progress stepper.
    """
    if status == ExperimentStatus.RESEARCH_FAILED:
        # Cannot determine exactly where failure occurred from the status alone.
        # Return empty — callers can check error_detail for context.
        return []

    try:
        idx = _RESEARCH_PHASE_ORDER.index(status)
    except ValueError:
        return []  # Not a research-flow status.

    return _RESEARCH_PHASE_ORDER[:idx]


def get_phase_label(status: ExperimentStatus) -> str | None:
    """Return the human-readable phase label for a given experiment status.

    Returns None for statuses outside the research flow (e.g. DRAFT, REFINED)
    and for terminal research states (RESEARCH_READY, RESEARCH_FAILED).

    The /research-status endpoint calls this directly.  The returned value
    is safe to pass through to the frontend — it contains no LLM-generated
    content and no user data.
    """
    return PHASE_DISPLAY.get(status)
