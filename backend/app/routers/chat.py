"""Chat router — POST /chat/turn (planning §7.1, ADR 0019).

Thin HTTP layer over chat_service.handle_turn. Domain logic stays in services.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.db.models.user import User
from app.db.session import get_session
from app.dispatchers.dependencies import get_dispatcher_dep
from app.dispatchers.protocol import ResearchDispatcher
from app.logging_config import get_logger
from app.reliability.rate_limit import AUTH_RATE_LIMIT, limiter, user_key
from app.schemas.chat import ChatTurnRequest, ChatTurnResponse
from app.services.chat_service import ChatAuthorizationError, handle_turn
from app.services.experiment_service import InvalidExperimentState

_logger = get_logger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post(
    "/turn",
    response_model=ChatTurnResponse,
    status_code=status.HTTP_200_OK,
)
@limiter.limit(AUTH_RATE_LIMIT, key_func=user_key)
async def chat_turn(
    request: Request,
    response: Response,
    body: ChatTurnRequest,
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
    dispatcher: Annotated[ResearchDispatcher, Depends(get_dispatcher_dep)],
) -> ChatTurnResponse:
    try:
        result = await handle_turn(
            db,
            current_user,
            body.message,
            body.deep_research,
            body.thread_id,
            body.experiment_id,
            body.idempotency_key,
            dispatcher,
        )
        return ChatTurnResponse.from_result(result)
    except ChatAuthorizationError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden",
        ) from None
    except InvalidExperimentState as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from None
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from None
    except Exception as exc:
        request_id: str = getattr(request.state, "request_id", "unknown")
        _logger.error(
            "chat turn failed",
            exc_info=exc,
            error_type=type(exc).__name__,
            user_id=str(current_user.id),
            request_id=request_id,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Internal error", "request_id": request_id},
        ) from exc
