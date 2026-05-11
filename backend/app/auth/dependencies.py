"""Authentication dependencies for FastAPI route handlers.

`get_current_user` is the canonical way to get the authenticated user.
Use it as: `current_user: Annotated[User, Depends(get_current_user)]`.

Per AGENTS.md "Authentication and authorization", every authenticated
endpoint MUST use this dependency. Resource-ownership checks are SEPARATE
(see future `get_owned_experiment` etc.).
"""

from typing import Annotated

import sentry_sdk
from fastapi import Depends, HTTPException, Request, status
from firebase_admin import auth as firebase_auth
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.firebase import verify_id_token
from app.db.models.user import User
from app.db.session import get_session
from app.logging_config import get_logger

_logger = get_logger(__name__)


def _extract_bearer_token(request: Request) -> str:
    """Pull the token from `Authorization: Bearer <token>`.

    Raises 401 if the header is missing or malformed. The error response
    is deliberately generic — never reveal which validation step failed
    (AGENTS.md "Error handling").
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    scheme, _, token = auth_header.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return token


async def get_current_user(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_session)],
) -> User:
    """Verify Firebase ID token and return the User row from Postgres.

    Returns 401 if:
    - Authorization header is missing or malformed
    - Token signature is invalid
    - Token is expired or revoked
    - Token's firebase_uid has no corresponding User row in Postgres
      (the User must be created via /users/sync first)
    """
    token = _extract_bearer_token(request)

    try:
        decoded = verify_id_token(token)
    except (
        firebase_auth.InvalidIdTokenError,
        firebase_auth.ExpiredIdTokenError,
        firebase_auth.RevokedIdTokenError,
    ) as exc:
        # Log at debug level only — invalid tokens are normal, not exceptional.
        _logger.debug("token verification failed", error_type=type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    firebase_uid = decoded.get("uid")
    if not firebase_uid:
        # Malformed claim — Firebase guarantees uid, but defensively check.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    stmt = select(User).where(User.firebase_uid == firebase_uid)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None:
        # Token is valid but User row doesn't exist. Frontend must call /users/sync first.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not provisioned. Sync user record before authenticating.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Enrich Sentry scope with the resolved user. Internal UUID only — never
    # email or firebase_uid (AGENTS.md "Logging hygiene").
    request.state.current_user = user
    sentry_sdk.set_user({"id": str(user.id)})

    return user


async def get_current_admin_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Require the authenticated user to have admin role.

    Returns 403 (NOT 401) when the user is authenticated but not admin —
    authentication succeeded, authorization failed. Per AGENTS.md,
    admin role is determined server-side from the User.is_admin column;
    never from a header, JWT claim, or anything the client could spoof.
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user
