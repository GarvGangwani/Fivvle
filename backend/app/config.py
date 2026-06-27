"""
Application configuration via Pydantic Settings.

All values are loaded from environment variables (or .env in local dev).
In production, environment variables are injected from Google Cloud Secret Manager.
Never log or print any setting value — see AGENTS.md "Logging hygiene".
"""

from functools import lru_cache
from decimal import Decimal
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="forbid",
    )

    # --- Database ---
    database_url: str

    # --- Firebase Admin ---
    firebase_project_id: str
    # Use FIREBASE_SERVICE_ACCOUNT_PATH (not GOOGLE_APPLICATION_CREDENTIALS) so a
    # machine-wide GCP credential env var does not override backend/.env.
    firebase_service_account_path: str = Field(
        validation_alias="FIREBASE_SERVICE_ACCOUNT_PATH",
    )
    firebase_storage_bucket: str = Field(
        default="",
        description=(
            "Firebase Storage bucket for founder uploads (e.g. landing-page logos). "
            "When empty, defaults to {FIREBASE_PROJECT_ID}.appspot.com."
        ),
    )
    logo_upload_backend: Literal["auto", "local", "firebase"] = Field(
        default="auto",
        description=(
            "Where to store uploaded landing-page logos. "
            "auto=local disk in development/test, Firebase otherwise."
        ),
    )

    # --- LLM and search APIs ---
    anthropic_api_key: str
    groq_api_key: str
    moonshot_api_key: str = ""
    tavily_api_key: str
    tavily_usd_per_credit: Decimal = Field(
        default=Decimal("0.008"),
        description=(
            "USD cost per Tavily API credit for audit rollups. Default matches "
            "Tavily pay-as-you-go ($0.008/credit). Set to your plan rate "
            "(e.g. 0.0075 on Project) for accurate admin dashboards."
        ),
    )

    # --- Reddit (read-only research) ---
    reddit_client_id: str
    reddit_client_secret: str
    reddit_user_agent: str

    # --- Observability ---
    sentry_dsn: str | None = None  # Optional — missing in dev is fine

    # --- Runtime config ---
    environment: Literal["development", "staging", "production", "test"] = "development"
    # Comma-separated list of allowed CORS origins; use cors_origins_list for the parsed form.
    cors_allowed_origins: str = "http://localhost:3000"
    cors_landing_origin_regex: str = Field(
        default=(
            r"http://[a-z0-9-]{6,40}\.localhost(?::\d+)?|"
            r"https://[a-z0-9-]{6,40}\.fivvle\.io"
        ),
        description=(
            "Regex allowlist for published landing page origins (subdomain page-view "
            "and waitlist beacons). Complements cors_allowed_origins; not a wildcard."
        ),
    )
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    reader_concurrency_limit: int = Field(
        default=7,
        description=(
            "Maximum concurrent Reader per-question LLM calls. Default 7 matches "
            "typical Planner output (~5-7 research questions per pipeline). Set to "
            "1 for fully sequential execution during debugging. Per ADR 0011."
        ),
    )

    reflector_max_refinement_waves: int = Field(
        default=1,
        description=(
            "Max refinement waves Reflector executes per pipeline run. "
            "v1 ships with 1: evaluate rules once, optionally re-search and re-read "
            "flagged questions once, proceed to Synthesizer. No second evaluation pass. "
            "Setting to 0 disables Reflector re-search entirely (pass-through). "
            "Per ADR 0013 and planning doc §5."
        ),
    )

    # Per-phase LLM selection. Default Sonnet — Haiku swap blocked by max_length cap overruns (see docs/calibration/runs/2026-05-27-haiku-attempt.md). Haiku migration requires per-phase cap recalibration.
    # provider must be a value the llm.client wrapper supports ("anthropic" | "groq").
    refinement_provider: str = Field(default="anthropic")
    refinement_model: str = Field(default="claude-sonnet-4-6")
    planner_provider: str = Field(default="anthropic")
    planner_model: str = Field(default="claude-sonnet-4-6")
    reader_provider: str = Field(default="anthropic")
    reader_model: str = Field(default="claude-sonnet-4-6")
    reflector_query_provider: str = Field(default="anthropic")
    reflector_query_model: str = Field(default="claude-sonnet-4-6")
    synthesizer_provider: str = Field(default="anthropic")
    synthesizer_model: str = Field(default="claude-sonnet-4-6")
    insight_provider: str = Field(default="kimi")
    insight_model: str = Field(default="kimi-k2.6")
    chat_attachment_vision_provider: str = Field(
        default="kimi",
        description="LLM provider for extracting text and context from chat image uploads.",
    )
    chat_attachment_vision_model: str = Field(
        default="kimi-k2.6",
        description="Model for chat attachment image extraction (vision).",
    )

    # --- Research dispatcher (ADR 0009) ---
    # in_process: invokes the research engine directly via asyncio.create_task (dev/test).
    # http: POSTs to the Cloud Function HTTPS endpoint with an OIDC token (staging/prod).
    # Selection is explicit — never auto-detected from environment.
    dispatcher_mode: Literal["in_process", "http"] = "in_process"
    oidc_audience: str | None = Field(
        default=None,
        description=(
            "OIDC audience for HttpDispatcher OIDC token. When None, defaults to "
            "research_engine_url. Override only if the Cloud Function audience "
            "differs from its URL."
        ),
    )
    # Required when dispatcher_mode="http". Must be the full HTTPS URL of the Cloud Function.
    # Leave unset in local dev (in_process mode ignores it).
    research_engine_url: str | None = None

    auto_fire_chat_enabled: Literal["off", "shadow", "cohort_10", "cohort_50", "on"] = Field(
        default="off",
        description=(
            "Progressive rollout for /chat/turn auto-fire. off=endpoint 404s; "
            "shadow=no dispatch (logs would-have-fired); cohort_10/50=deterministic % "
            "of experiments dispatch; on=all dispatch."
        ),
    )

    refinement_max_clarifying_turns: int = Field(
        default=6,
        description=(
            "Hard ceiling on chat-mode clarifying turns before the refinement "
            "assistant must finalize. Per refinement prompt anti-loop cap."
        ),
    )

    refinement_min_clarifying_turns_before_finalize: int = Field(
        default=3,
        description=(
            "Minimum clarifying turns before the refinement assistant may choose "
            "to finalize. Enforced via prompt instructions, not post-hoc overrides."
        ),
    )

    monetization_enabled: bool = Field(
        default=False,
        description=(
            "When true, debit credits on paid services. Default false for local dev."
        ),
    )

    # --- Razorpay (credit pack top-ups; test mode in dev) ---
    razorpay_key_id: str = Field(
        default="",
        description="Razorpay key_id (public). Empty disables order creation.",
    )
    razorpay_key_secret: str = Field(
        default="",
        description="Razorpay key_secret. Never expose to frontend.",
    )
    usd_inr_rate: float = Field(
        default=83.0,
        description="USD→INR rate for Razorpay order amounts (product UI stays USD/credits).",
    )

    # Comma-separated emails granted admin API access (verified Firebase email only).
    admin_emails: str = Field(
        default="",
        description=(
            "Comma-separated list of emails allowed to call /admin/* endpoints. "
            "Matched case-insensitively against the Firebase-verified email on "
            "POST /users/sync. Example: fivvleio@gmail.com"
        ),
    )

    frontend_revalidate_url: str | None = Field(
        default=None,
        description="Next.js ISR revalidate endpoint (optional in local dev).",
    )
    revalidate_secret: str | None = Field(
        default=None,
        description="Shared secret for POST /api/revalidate (optional in local dev).",
    )

    landing_public_root_domain: str = Field(
        default="fivvle.io",
        description="Root domain for published landing pages ({slug}.fivvle.io).",
    )
    landing_public_dev_port: int = Field(
        default=3000,
        description="Dev port for {slug}.localhost landing page URLs.",
    )

    # ------------------------------------------------------------------
    # Derived helpers (not env vars)
    # ------------------------------------------------------------------

    @property
    def admin_emails_list(self) -> list[str]:
        return [
            part.strip().lower()
            for part in self.admin_emails.split(",")
            if part.strip()
        ]

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse the comma-separated CORS origins into a list, stripping whitespace."""
        return [origin.strip() for origin in self.cors_allowed_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """Return the cached Settings singleton.

    The cache is intentional — Settings construction reads from disk/.env on
    first call; subsequent calls return the same object with zero I/O.
    """
    return Settings()
