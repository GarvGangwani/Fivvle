"""HttpDispatcher — production ResearchDispatcher for DISPATCHER_MODE=http (ADR 0009).

Per ADR 0020, POSTs ``{"experiment_id": "<uuid>"}`` to the configured Cloud Function
URL with a GCP OIDC bearer token (audience defaults to the URL; override via
``OIDC_AUDIENCE``). HTTP 200/202 means the trigger was accepted; the pipeline runs
asynchronously in the Cloud Function after the response.
"""

from __future__ import annotations

import asyncio
from uuid import UUID

import httpx
import structlog
from google.auth.exceptions import DefaultCredentialsError
from google.auth.transport.requests import Request as GoogleAuthRequest
from google.oauth2.id_token import fetch_id_token

from app.dispatchers.protocol import DispatchError

logger = structlog.get_logger(__name__)


class HttpDispatcher:
    """Trigger the research engine Cloud Function over HTTPS (ADR 0020).

    Accepts the Cloud Function URL at construction time.  The factory reads it
    from settings.research_engine_url and validates it is set before calling
    this constructor.
    """

    def __init__(
        self,
        url: str,
        audience: str | None = None,
        timeout_seconds: float = 10.0,
    ) -> None:
        self._url = url
        self._audience = audience or url
        self._timeout = timeout_seconds

    async def dispatch(self, experiment_id: UUID) -> None:
        """POST to the Cloud Function with an OIDC bearer token."""
        log = logger.bind(
            dispatcher="http",
            experiment_id=str(experiment_id),
        )
        log.info("http dispatch started", phase="dispatch_started")

        try:
            token = await asyncio.to_thread(
                fetch_id_token,
                GoogleAuthRequest(),
                self._audience,
            )
        except DefaultCredentialsError:
            log.error(
                "failed to mint oidc token",
                phase="failed",
                error_type="DefaultCredentialsError",
            )
            raise DispatchError(
                "Failed to mint OIDC token for Cloud Function dispatch"
            ) from None
        except Exception as exc:
            log.error(
                "failed to mint oidc token",
                phase="failed",
                error_type=type(exc).__name__,
            )
            raise DispatchError(
                "Failed to mint OIDC token for Cloud Function dispatch"
            ) from exc

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(
                    self._url,
                    json={"experiment_id": str(experiment_id)},
                    headers={"Authorization": f"Bearer {token}"},
                )
        except httpx.TimeoutException:
            raise DispatchError(
                f"Cloud Function dispatch timed out after {self._timeout}s"
            ) from None
        except httpx.HTTPError as exc:
            raise DispatchError(
                f"Cloud Function dispatch transport error: {type(exc).__name__}"
            ) from exc

        if response.status_code not in {200, 202}:
            raise DispatchError(
                f"Cloud Function returned HTTP {response.status_code} (expected 202)"
            )

        log.info(
            "http dispatch succeeded",
            phase="dispatch_succeeded",
            status_code=response.status_code,
        )
