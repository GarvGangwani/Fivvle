"""Chat router — POST /chat/turn (planning §7.1, ADR 0019).

Thin HTTP layer over chat_service.handle_turn. Domain logic stays in services.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Request, Response, UploadFile, status
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
    ChatAttachmentsUploadResponse,
    ChatAttachmentUploadItem,
    ChatEditTurnRequest,
    ChatEditTurnResponse,
    ChatMessageItem,
    ChatTurnRequest,
    ChatTurnResponse,
    ExperimentChatMessagesResponse,
)
from app.services.chat_attachment_service import (
    ChatAttachmentAccessError,
    create_chat_attachment,
)
from app.services.chat_service import (
    ChatAuthorizationError,
    ChatMessageEditError,
    build_user_message_metadata,
    handle_edit_turn,
    handle_turn,
    list_experiment_chat_messages,
)
from app.services.chat_tree_service import enrich_messages_with_sibling_info
from app.services.experiment_service import InvalidExperimentState
from app.utils.chat_attachment import (
    MAX_ATTACHMENTS_PER_TURN,
    ChatAttachmentValidationError,
)

_logger = get_logger(__name__)


async def _message_items_with_siblings(
    db: AsyncSession,
    messages: list,
) -> list[ChatMessageItem]:
    enriched = await enrich_messages_with_sibling_info(db, messages)
    return [
        ChatMessageItem.from_orm_message(
            msg,
            sibling_index=index,
            sibling_count=count,
        )
        for msg, index, count in enriched
    ]

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
            body.name,
            body.attachment_ids,
            user_message_metadata=build_user_message_metadata(
                selected_option_indices=body.selected_option_indices,
                custom_added_text=body.custom_added_text,
                answered_question_from_message_id=body.answered_question_from_message_id,
            ),
        )
        return ChatTurnResponse.from_result(result)
    except ChatAuthorizationError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden",
        ) from None
    except ChatAttachmentValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from None
    except ChatAttachmentAccessError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="One or more attachments are invalid or expired.",
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


@router.post(
    "/turn/edit",
    response_model=ChatEditTurnResponse,
    status_code=status.HTTP_200_OK,
)
@limiter.limit(AUTH_RATE_LIMIT, key_func=user_key)
async def chat_turn_edit(
    request: Request,
    response: Response,
    body: ChatEditTurnRequest,
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
    dispatcher: Annotated[ResearchDispatcher, Depends(get_dispatcher_dep)],
) -> ChatEditTurnResponse:
    if get_settings().auto_fire_chat_enabled == "off":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    try:
        result = await handle_edit_turn(
            db,
            current_user,
            body.thread_id,
            body.message_id,
            body.new_content,
            dispatcher,
        )
        return ChatEditTurnResponse(
            thread_id=result.thread_id,
            edited_message_id=result.edited_message_id,
            message_id=result.message_id,
            experiment_id=result.experiment_id,
            assistant_message=result.assistant_message,
            turn_kind=result.turn_kind,
            clarifying_dimension=result.clarifying_dimension,
            clarifying_questions=list(result.clarifying_questions),
            pipeline_dispatched=result.pipeline_dispatched,
            dispatched_at=result.dispatched_at,
            experiment_status=result.experiment_status,
            research_error_detail=result.research_error_detail,
            messages=await _message_items_with_siblings(db, result.messages),
        )
    except ChatAuthorizationError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden",
        ) from None
    except ChatMessageEditError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
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
            "chat edit turn failed",
            exc_info=exc,
            error_type=type(exc).__name__,
            user_id=str(current_user.id),
            request_id=request_id,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Internal error", "request_id": request_id},
        ) from exc


@router.post(
    "/attachments",
    response_model=ChatAttachmentsUploadResponse,
    status_code=status.HTTP_200_OK,
)
@limiter.limit(AUTH_RATE_LIMIT, key_func=user_key)
async def upload_chat_attachments(
    request: Request,
    response: Response,
    files: Annotated[list[UploadFile], File(...)],
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ChatAttachmentsUploadResponse:
    if get_settings().auto_fire_chat_enabled == "off":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one file is required.",
        )
    if len(files) > MAX_ATTACHMENTS_PER_TURN:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"You can attach up to {MAX_ATTACHMENTS_PER_TURN} files per message.",
        )

    uploaded: list[ChatAttachmentUploadItem] = []
    try:
        for upload in files:
            file_bytes = await upload.read()
            filename = upload.filename or "attachment"
            result = await create_chat_attachment(
                db,
                user=current_user,
                filename=filename,
                file_bytes=file_bytes,
            )
            uploaded.append(
                ChatAttachmentUploadItem(
                    id=result.id,
                    filename=result.filename,
                    content_kind=result.content_kind,
                    excerpt=result.excerpt,
                    char_count=result.char_count,
                )
            )
        await db.commit()
    except ChatAttachmentValidationError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        await db.rollback()
        request_id: str = getattr(request.state, "request_id", "unknown")
        _logger.error(
            "chat attachment upload failed",
            exc_info=exc,
            error_type=type(exc).__name__,
            user_id=str(current_user.id),
            request_id=request_id,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Internal error", "request_id": request_id},
        ) from exc

    return ChatAttachmentsUploadResponse(attachments=uploaded)


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
        messages=await _message_items_with_siblings(db, messages),
    )
