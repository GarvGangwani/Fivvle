"""User-related route handlers."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from firebase_admin import auth as firebase_auth
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import _extract_bearer_token
from app.auth.firebase import verify_id_token
from app.db.models.user import User
from app.db.session import get_session
from app.logging_config import get_logger
from app.reliability.rate_limit import AUTH_RATE_LIMIT, limiter, user_key
from app.schemas.user import UserResponse, UserSyncRequest

_logger = get_logger(__name__)

router = APIRouter(prefix="/users", tags=["users"])


@router.post("/sync", response_model=UserResponse, status_code=status.HTTP_200_OK)
@limiter.limit(AUTH_RATE_LIMIT, key_func=user_key)
async def sync_user(
    request: Request,
    body: UserSyncRequest,
    db: Annotated[AsyncSession, Depends(get_session)],
    response: Response,
) -> User:
    """Idempotent user sync — call from frontend after Firebase signup.

    Verifies the Firebase ID token, then either:
    - Returns the existing User row if firebase_uid already exists, OR
    - Creates a new User row from the token's uid + email, with the optional
      display name from the request body.

    This endpoint deliberately does NOT use get_current_user — that
    dependency requires the User row to already exist, which is what we're
    creating here. Instead, we verify the token and look up the user inline.

    Per AGENTS.md, the token is the source of truth for firebase_uid and
    email — the request body cannot override either of those fields.
    """
    token = _extract_bearer_token(request)

    try:
        decoded = verify_id_token(token)
    except (
        firebase_auth.InvalidIdTokenError,
        firebase_auth.ExpiredIdTokenError,
        firebase_auth.RevokedIdTokenError,
    ) as exc:
        _logger.debug("token verification failed", error_type=type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    firebase_uid = decoded.get("uid")
    email = decoded.get("email")

    if not firebase_uid or not email:
        # Firebase guarantees uid and email — defensively check.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    stmt = select(User).where(User.firebase_uid == firebase_uid)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None:
        user = User(
            firebase_uid=firebase_uid,
            email=email,
            name=body.name,
        )
        db.add(user)
        await db.flush()
        await db.refresh(user)
        _logger.info("user provisioned", user_id=str(user.id))

    return user
