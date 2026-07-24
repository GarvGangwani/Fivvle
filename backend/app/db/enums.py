"""
Python StrEnum types for status fields.

These mirror the State Machine in ARCHITECTURE.md exactly.
Models (build step 2B) reference these via SQLAlchemy's Enum() type
with ``native_enum=False`` so values are stored as VARCHAR, allowing
new states to be added without Postgres-level ALTER TYPE migrations.
"""

from enum import StrEnum


class ExperimentStage(StrEnum):
    """Founder-declared product lifecycle stage for targeting (nullable on Experiment)."""

    IDEA = "idea"
    BUILDING = "building"
    LAUNCHED = "launched"


class ExperimentStatus(StrEnum):
    """Matches ARCHITECTURE.md state machine exactly — 21 states total.

    Sub-states for the research engine phases are inline rather than
    nested, making them first-class status values on the Experiment row.

    Adding a new state requires:
    1. Adding the enum member here.
    2. Updating ARCHITECTURE.md state machine diagram.
    3. Optionally a data migration to backfill values (usually not needed).

    Storage strategy: VARCHAR with SQLAlchemy Enum(native_enum=False).
    This lets us add states without Postgres-level ALTER TYPE migrations.
    """

    # --- Spark + refinement states (4) ---
    SPARK = "SPARK"
    DRAFT = "DRAFT"  # legacy mid-flow rows; new creates use SPARK
    REFINING = "REFINING"
    REFINED = "REFINED"

    # --- Research umbrella + sub-states (1 umbrella + 5 sub + 2 terminal = 8) ---
    RESEARCHING = "RESEARCHING"
    RESEARCH_PLANNING = "RESEARCH_PLANNING"
    RESEARCH_SEARCHING = "RESEARCH_SEARCHING"
    RESEARCH_READING = "RESEARCH_READING"
    RESEARCH_REFLECTING = "RESEARCH_REFLECTING"
    RESEARCH_VOICES = "RESEARCH_VOICES"
    RESEARCH_SYNTHESIZING = "RESEARCH_SYNTHESIZING"
    RESEARCH_READY = "RESEARCH_READY"
    RESEARCH_FAILED = "RESEARCH_FAILED"

    # --- Landing page states (3) ---
    LANDING_GENERATING = "LANDING_GENERATING"
    LANDING_DRAFT = "LANDING_DRAFT"
    LANDING_LIVE = "LANDING_LIVE"

    # --- Insight sub-states (3, under ANALYZING umbrella per RESEARCHING precedent) ---
    INSIGHT_GENERATING = "INSIGHT_GENERATING"
    INSIGHT_READY = "INSIGHT_READY"
    INSIGHT_FAILED = "INSIGHT_FAILED"

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


class ChatRole(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"
    # Agent tool exchange (universal chat and future agent surfaces).
    # Stored as VARCHAR via native_enum=False — no Postgres ALTER TYPE needed.
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"


class ChatTurnKind(StrEnum):
    NORMAL_CHAT = "normal_chat"
    DISCUSS = "discuss"
    REFINEMENT_CLARIFY = "refinement_clarify"
    REFINEMENT_FINALIZE = "refinement_finalize"
    DISPATCH_ANNOUNCE = "dispatch_announce"
    PIPELINE_PROGRESS = "pipeline_progress"
    PIPELINE_COMPLETE = "pipeline_complete"
    PIPELINE_FAILED = "pipeline_failed"
    # Founder chatting with a completed validation report (Evidence surface).
    # Isolated thread — never mixed with refinement/discussion history.
    EVIDENCE_CHAT = "evidence_chat"
    # Canvas-wide coach / future agent surface. Isolated via
    # experiments.universal_thread_id — never mixed with Refine or Evidence.
    UNIVERSAL_CHAT = "universal_chat"


class DispatchTrigger(StrEnum):
    USER_CONFIRM = "user_confirm"
    AUTO_FIRE = "auto_fire"
    EVIDENCE_RERUN = "evidence_rerun"


class WalletTransactionType(StrEnum):
    """Ledger entry types for wallet_transactions (ADR 0024 / migration f8a2c1d4e6b7)."""

    TOPUP = "TOPUP"
    BONUS = "BONUS"
    COUPON = "COUPON"
    SERVICE_USAGE = "SERVICE_USAGE"
    REFUND = "REFUND"
    ADMIN_ADJUSTMENT = "ADMIN_ADJUSTMENT"


class PaymentOrderStatus(StrEnum):
    """Razorpay credit-pack purchase lifecycle."""

    CREATED = "CREATED"
    PAID = "PAID"
    FAILED = "FAILED"
