"""Database package — SQLAlchemy 2.0 async, Postgres.

Public API:
    Base               — declarative base class for models
    get_session        — FastAPI dependency yielding an AsyncSession
    init_engine        — startup hook (called in app.main lifespan, step 2C)
    dispose_engine     — shutdown hook
    check_db_health    — used by /health/ready (wired in step 2C)

    Status enums:      ExperimentStatus, LandingDensity, LandingCtaType,
                       InsightRecommendation

    Models:            Experiment, ExternalAPICall, InsightReport, LandingPage,
                       LLMCall, PageView, User, ValidationReport, WaitlistSignup
"""

from app.db.base import Base
from app.db.enums import (
    ExperimentStatus,
    InsightRecommendation,
    LandingCtaType,
    LandingDensity,
)
from app.db.models import (
    Experiment,
    ExternalAPICall,
    InsightReport,
    LandingPage,
    LLMCall,
    PageView,
    User,
    ValidationReport,
    WaitlistSignup,
)
from app.db.session import (
    check_db_health,
    dispose_engine,
    get_session,
    init_engine,
)

__all__ = [
    # Base
    "Base",
    # Enums
    "ExperimentStatus",
    "InsightRecommendation",
    "LandingCtaType",
    "LandingDensity",
    # Models
    "Experiment",
    "ExternalAPICall",
    "InsightReport",
    "LandingPage",
    "LLMCall",
    "PageView",
    "User",
    "ValidationReport",
    "WaitlistSignup",
    # Session management
    "check_db_health",
    "dispose_engine",
    "get_session",
    "init_engine",
]
