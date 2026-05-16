"""B3 Reader phase order and display mapping (planning doc §10.2)."""

from __future__ import annotations

from app.db.enums import ExperimentStatus
from app.services import research_phase_mapping as rpm


def test_phase_order_contains_research_reading_between_searching_and_synthesizing() -> None:
    order = rpm._RESEARCH_PHASE_ORDER
    i_search = order.index(ExperimentStatus.RESEARCH_SEARCHING)
    i_read = order.index(ExperimentStatus.RESEARCH_READING)
    i_synth = order.index(ExperimentStatus.RESEARCH_SYNTHESIZING)
    assert i_search < i_read < i_synth


def test_phase_order_contains_research_reflecting_between_reading_and_synthesizing() -> None:
    """ADR 0013 / B3 §7: REFLECTING is a live pipeline phase between Reader and Synthesizer."""
    order = rpm._RESEARCH_PHASE_ORDER
    assert ExperimentStatus.RESEARCH_REFLECTING in order
    i_read = order.index(ExperimentStatus.RESEARCH_READING)
    i_refl = order.index(ExperimentStatus.RESEARCH_REFLECTING)
    i_synth = order.index(ExperimentStatus.RESEARCH_SYNTHESIZING)
    assert i_read < i_refl < i_synth


def test_phase_display_contains_research_reading() -> None:
    label = rpm.PHASE_DISPLAY.get(ExperimentStatus.RESEARCH_READING)
    assert label is not None
    assert len(label) > 0


def test_phase_display_contains_research_reflecting_even_though_unreachable() -> None:
    label = rpm.PHASE_DISPLAY.get(ExperimentStatus.RESEARCH_REFLECTING)
    assert label is not None
    assert len(label) > 0
