"""Chat router — POST /chat/turn (planning §7.1, ADR 0019).

Thin HTTP layer over chat_service.handle_turn. Domain logic stays in services.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.config import get_settings
from app.db.models.user import User
from app.db.session import get_session
from app.dispatchers.dependencies import get_dispatcher_dep
from app.dispatchers.protocol import ResearchDispatcher
from app.logging_config import get_logger
from app.reliability.rate_limit import AUTH_RATE_LIMIT, limiter, user_key
from app.schemas.chat import (
    ChatMessageItem,
    ChatTurnRequest,
    ChatTurnResponse,
    ExperimentChatMessagesResponse,
)
from app.services.chat_service import ChatAuthorizationError, handle_turn, list_experiment_chat_messages
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
    if get_settings().auto_fire_chat_enabled == "off":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

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


@router.get(
    "/experiments/{experiment_id}/messages",
    response_model=ExperimentChatMessagesResponse,
    status_code=status.HTTP_200_OK,
)
@limiter.limit(AUTH_RATE_LIMIT, key_func=user_key)
async def get_experiment_chat_messages(
    request: Request,
    response: Response,
    experiment_id: UUID,
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ExperimentChatMessagesResponse:
    if get_settings().auto_fire_chat_enabled == "off":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    try:
        thread_id, messages = await list_experiment_chat_messages(
            db, current_user, experiment_id
        )
    except ChatAuthorizationError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden",
        ) from None

    return ExperimentChatMessagesResponse(
        thread_id=thread_id,
        experiment_id=experiment_id,
        messages=[ChatMessageItem.model_validate(m) for m in messages],
    )
