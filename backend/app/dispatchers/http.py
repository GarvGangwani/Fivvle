"""HttpDispatcher — production implementation of ResearchDispatcher (ADR 0009).

POSTs to the Cloud Function HTTPS endpoint with a Google OIDC token so the
function can verify the caller is the Fivvle API service account.

Not implemented in B2.4 — the in-process dispatcher is used for all
environments in the current milestone.  This stub ensures:
  1. The factory can return a typed object for DISPATCHER_MODE=http.
  2. Tests can verify the factory routing without touching real network.
  3. The class docstring documents the B3 implementation contract.

B3 implementation checklist (do NOT implement here until B3):
  - Use httpx.AsyncClient with a 30-second timeout.
  - Obtain an OIDC token via google-auth for the Cloud Function audience.
  - POST {"experiment_id": str(experiment_id)} to settings.research_engine_url.
  - On non-2xx response: raise DispatchError with sanitized status code.
  - On network error: raise DispatchError.
  - Follow SSRF prevention rules in AGENTS.md (the URL comes from settings,
    not from user input, so the blocklist check is a belt-and-suspenders
    measure, not strictly required — but do it anyway).
"""

from __future__ import annotations

from uuid import UUID

import structlog

from app.dispatchers.protocol import DispatchError

logger = structlog.get_logger(__name__)


class HttpDispatcher:
    """Trigger the research engine Cloud Function over HTTPS (B3 implementation).

    Accepts the Cloud Function URL at construction time.  The factory reads it
    from settings.research_engine_url and validates it is set before calling
    this constructor.
    """

    def __init__(self, url: str) -> None:
        self._url = url

    async def dispatch(self, experiment_id: UUID) -> None:
        """POST to the Cloud Function.  NOT YET IMPLEMENTED — raises immediately."""
        logger.error(
            "http dispatcher not yet implemented",
            dispatcher="http",
            experiment_id=str(experiment_id),
            phase="failed",
        )
        raise DispatchError(
            "HttpDispatcher is not implemented in B2.4. "
            "Set DISPATCHER_MODE=in_process for local dev."
        )
