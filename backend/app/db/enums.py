"""
Python StrEnum types for status fields.

These mirror the State Machine in ARCHITECTURE.md exactly.
Models (build step 2B) reference these via SQLAlchemy's Enum() type
with ``native_enum=False`` so values are stored as VARCHAR, allowing
new states to be added without Postgres-level ALTER TYPE migrations.
"""

from enum import StrEnum


class ExperimentStatus(StrEnum):
    """Matches ARCHITECTURE.md state machine exactly — 17 states total.

    Sub-states for the research engine phases are inline rather than
    nested, making them first-class status values on the Experiment row.

    Adding a new state requires:
    1. Adding the enum member here.
    2. Updating ARCHITECTURE.md state machine diagram.
    3. Optionally a data migration to backfill values (usually not needed).

    Storage strategy: VARCHAR with SQLAlchemy Enum(native_enum=False).
    This lets us add states without Postgres-level ALTER TYPE migrations.
    """

    # --- Refinement states (3) ---
    DRAFT = "DRAFT"
    REFINING = "REFINING"
    REFINED = "REFINED"

    # --- Research umbrella + sub-states (1 umbrella + 5 sub + 2 terminal = 8) ---
    RESEARCHING = "RESEARCHING"
    RESEARCH_PLANNING = "RESEARCH_PLANNING"
    RESEARCH_SEARCHING = "RESEARCH_SEARCHING"
    RESEARCH_READING = "RESEARCH_READING"
    RESEARCH_REFLECTING = "RESEARCH_REFLECTING"
    RESEARCH_SYNTHESIZING = "RESEARCH_SYNTHESIZING"
    RESEARCH_READY = "RESEARCH_READY"
    RESEARCH_FAILED = "RESEARCH_FAILED"

    # --- Landing page states (3) ---
    LANDING_GENERATING = "LANDING_GENERATING"
    LANDING_DRAFT = "LANDING_DRAFT"
    LANDING_LIVE = "LANDING_LIVE"

    # --- Terminal states (3) ---
    ANALYZING = "ANALYZING"
    COMPLETED = "COMPLETED"
    ARCHIVED = "ARCHIVED"


class LandingDensity(StrEnum):
    """Density toggle on landing page templates (per ARCHITECTURE.md LandingPageProps)."""

    COMPACT = "compact"
    ROOMY = "roomy"


class LandingCtaType(StrEnum):
    """CTA type on landing pages (per USER_FLOW.md Stage 4)."""

    WAITLIST = "waitlist"
    INTEREST = "interest"
    CONTACT = "contact"


class InsightRecommendation(StrEnum):
    """AI recommendation in the insight report (per USER_FLOW.md Stage 6)."""

    PROCEED = "proceed"
    ITERATE = "iterate"
    PIVOT = "pivot"
    KILL = "kill"
