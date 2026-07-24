"""SQLAlchemy model for the Experiment table."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

import sqlalchemy as sa
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.enums import DispatchTrigger, ExperimentStage, ExperimentStatus, FounderDecision

if TYPE_CHECKING:
    from app.db.models.external_api_call import ExternalAPICall
    from app.db.models.insight_report import InsightReport
    from app.db.models.landing_page import LandingPage
    from app.db.models.landing_page_v2 import LandingPageV2Spec
    from app.db.models.launch_kit import LaunchKit
    from app.db.models.llm_call import LLMCall
    from app.db.models.page_view import PageView
    from app.db.models.user import User
    from app.db.models.validation_report import ValidationReport
    from app.db.models.waitlist_signup import WaitlistSignup


class Experiment(Base):
    __tablename__ = "experiments"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    slug: Mapped[str | None] = mapped_column(
        String(50),
        unique=True,
        nullable=True,
        index=True,
    )
    name: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    raw_idea: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    refined_idea: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    refined_idea_current: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    refined_idea_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    tags: Mapped[list[str]] = mapped_column(
        ARRAY(String),
        nullable=False,
        server_default=sa.text("'{}'"),
    )
    refinement_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=sa.text("0"),
    )
    target_geography: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
    )
    # Founder-declared audience bracket (coarse, e.g. "urban middle-class families
    # in tier-1 cities"). Distinct from RefinedIdea.target_audience which is an
    # LLM-generated vivid portrait produced during refinement. Both flow into
    # Planner/Synthesizer as complementary signals — the bracket anchors geography
    # and demographics; the portrait anchors context and behavior.
    audience_bracket: Mapped[str | None] = mapped_column(
        String(300),
        nullable=True,
    )
    stage: Mapped[ExperimentStage | None] = mapped_column(
        SQLEnum(
            ExperimentStage,
            name="experiment_stage",
            native_enum=False,
            length=20,
        ),
        nullable=True,
    )
    why_now: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )
    status: Mapped[ExperimentStatus] = mapped_column(
        SQLEnum(
            ExperimentStatus,
            name="experiment_status",
            native_enum=False,
            length=50,
        ),
        nullable=False,
        default=ExperimentStatus.SPARK,
        index=True,
    )
    spark_last_edited_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    refinement_started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    # Sanitized error string written by the state machine on RESEARCH_FAILED.
    # NULL on success. Never contains raw stack traces or API keys — see
    # research_engine_service.py _sanitize_error_detail().
    research_error_detail: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    # Links experiment to chat thread; null for non-chat paths (admin, eval).
    thread_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("chat_threads.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    # Evidence-chat thread (founder Q&A over the completed validation report).
    # Separate from thread_id so evidence chat never mixes with refinement/
    # discussion history. Created on the first evidence-chat message. Mirrors
    # thread_id exactly (FK → chat_threads, SET NULL on delete, indexed).
    evidence_thread_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("chat_threads.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    # Audit: user_confirm (/confirm) vs auto_fire (chat refinement complete).
    dispatch_trigger: Mapped[DispatchTrigger | None] = mapped_column(
        SQLEnum(
            DispatchTrigger,
            name="dispatch_trigger",
            native_enum=False,
            length=20,
        ),
        nullable=True,
    )
    # Founder-recorded Signal decision (proceed/iterate/pivot/kill). Distinct from
    # API field `verdict` (validation-report overall_recommendation) and from the
    # AI InsightRecommendation on InsightReport. Nullable until the founder records.
    founder_decision: Mapped[FounderDecision | None] = mapped_column(
        SQLEnum(
            FounderDecision,
            name="founder_decision",
            native_enum=False,
            length=20,
        ),
        nullable=True,
    )
    founder_decision_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    # Optional free-text rationale. Cap matches Experiment.why_now (String(500)).
    founder_decision_note: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )
    # Optimistic concurrency for amendable decisions. NULL = never recorded;
    # first write accepts base_version=0 and sets this to 1.
    founder_decision_version: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    # --- Relationships ---
    user: Mapped[User] = relationship(back_populates="experiments")
    validation_report: Mapped[ValidationReport | None] = relationship(
        back_populates="experiment",
        cascade="all, delete-orphan",
        uselist=False,
    )
    landing_page: Mapped[LandingPage | None] = relationship(
        back_populates="experiment",
        cascade="all, delete-orphan",
        uselist=False,
    )
    landing_page_v2: Mapped[LandingPageV2Spec | None] = relationship(
        back_populates="experiment",
        cascade="all, delete-orphan",
        uselist=False,
    )
    insight_report: Mapped[InsightReport | None] = relationship(
        back_populates="experiment",
        cascade="all, delete-orphan",
        uselist=False,
    )
    launch_kit: Mapped[LaunchKit | None] = relationship(
        back_populates="experiment",
        cascade="all, delete-orphan",
        uselist=False,
    )
    page_views: Mapped[list[PageView]] = relationship(
        back_populates="experiment",
        cascade="all, delete-orphan",
    )
    waitlist_signups: Mapped[list[WaitlistSignup]] = relationship(
        back_populates="experiment",
        cascade="all, delete-orphan",
    )
    # No cascade — LLMCall/ExternalAPICall are audit records; survive experiment deletion.
    llm_calls: Mapped[list[LLMCall]] = relationship(back_populates="experiment")
    external_api_calls: Mapped[list[ExternalAPICall]] = relationship(
        back_populates="experiment"
    )
