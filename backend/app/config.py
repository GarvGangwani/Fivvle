"""
Application configuration via Pydantic Settings.

All values are loaded from environment variables (or .env in local dev).
In production, environment variables are injected from Google Cloud Secret Manager.
Never log or print any setting value — see AGENTS.md "Logging hygiene".
"""

from functools import lru_cache
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
    google_application_credentials: str

    # --- LLM and search APIs ---
    anthropic_api_key: str
    groq_api_key: str
    tavily_api_key: str

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

    # --- Research dispatcher (ADR 0009) ---
    # in_process: invokes the research engine directly via asyncio.create_task (dev/test).
    # http: POSTs to the Cloud Function HTTPS endpoint with an OIDC token (staging/prod).
    # Selection is explicit — never auto-detected from environment.
    dispatcher_mode: Literal["in_process", "http"] = "in_process"
    # Required when dispatcher_mode="http". Must be the full HTTPS URL of the Cloud Function.
    # Leave unset in local dev (in_process mode ignores it).
    research_engine_url: str | None = None

    # ------------------------------------------------------------------
    # Derived helpers (not env vars)
    # ------------------------------------------------------------------

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
