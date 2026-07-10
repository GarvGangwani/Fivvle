"""Experiment Spark attachment CRUD and upload-url endpoints."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.db.models.experiment import Experiment
from app.db.models.experiment_attachment import ExperimentAttachment
from app.db.models.user import User
from app.db.session import get_session
from app.schemas.experiment_attachments import (
    AttachmentCreateIn,
    AttachmentOut,
    AttachmentPatchIn,
    UploadUrlRequest,
    UploadUrlResponse,
)
from app.services.attachment_upload_service import (
    AttachmentUploadError,
    create_attachment_upload_url,
    store_local_attachment_bytes,
)

router = APIRouter(tags=["experiment-attachments"])


async def _get_owned_experiment(
    db: AsyncSession,
    experiment_id: UUID,
    user_id: UUID,
) -> Experiment:
    result = await db.execute(select(Experiment).where(Experiment.id == experiment_id))
    experiment = result.scalar_one_or_none()
    if experiment is None or experiment.user_id != user_id:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return experiment


@router.get(
    "/experiments/{experiment_id}/attachments",
    response_model=list[AttachmentOut],
)
async def list_attachments(
    experiment_id: UUID,
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[AttachmentOut]:
    await _get_owned_experiment(db, experiment_id, current_user.id)
    result = await db.execute(
        select(ExperimentAttachment)
        .where(
            ExperimentAttachment.experiment_id == experiment_id,
            ExperimentAttachment.user_id == current_user.id,
        )
        .order_by(
            ExperimentAttachment.created_at.desc(),
            ExperimentAttachment.id.desc(),
        )
    )
    rows = result.scalars().all()
    return [AttachmentOut.model_validate(row) for row in rows]


@router.post(
    "/experiments/{experiment_id}/attachments",
    response_model=AttachmentOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_attachment(
    experiment_id: UUID,
    payload: AttachmentCreateIn,
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> AttachmentOut:
    await _get_owned_experiment(db, experiment_id, current_user.id)
    row = ExperimentAttachment(
        experiment_id=experiment_id,
        user_id=current_user.id,
        attachment_type=payload.attachment_type,
        title=payload.title,
        content_text=payload.content_text,
        file_url=payload.file_url,
        file_mime=payload.file_mime,
        file_size_bytes=payload.file_size_bytes,
    )
    db.add(row)
    await db.flush()
    await db.refresh(row)
    return AttachmentOut.model_validate(row)


@router.patch(
    "/experiments/{experiment_id}/attachments/{att_id}",
    response_model=AttachmentOut,
)
async def patch_attachment(
    experiment_id: UUID,
    att_id: UUID,
    payload: AttachmentPatchIn,
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> AttachmentOut:
    await _get_owned_experiment(db, experiment_id, current_user.id)
    result = await db.execute(
        select(ExperimentAttachment).where(
            ExperimentAttachment.id == att_id,
            ExperimentAttachment.experiment_id == experiment_id,
            ExperimentAttachment.user_id == current_user.id,
        )
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Attachment not found")

    updates = payload.model_dump(exclude_unset=True)
    if "title" in updates and updates["title"] is not None:
        updates["title"] = updates["title"].strip()
    for key, value in updates.items():
        setattr(row, key, value)
    await db.flush()
    await db.refresh(row)
    return AttachmentOut.model_validate(row)


@router.delete(
    "/experiments/{experiment_id}/attachments/{att_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_attachment(
    experiment_id: UUID,
    att_id: UUID,
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Response:
    await _get_owned_experiment(db, experiment_id, current_user.id)
    result = await db.execute(
        select(ExperimentAttachment).where(
            ExperimentAttachment.id == att_id,
            ExperimentAttachment.experiment_id == experiment_id,
            ExperimentAttachment.user_id == current_user.id,
        )
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Attachment not found")
    await db.delete(row)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/experiments/{experiment_id}/attachments/upload-url",
    response_model=UploadUrlResponse,
)
async def create_upload_url(
    experiment_id: UUID,
    payload: UploadUrlRequest,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> UploadUrlResponse:
    await _get_owned_experiment(db, experiment_id, current_user.id)
    try:
        return create_attachment_upload_url(
            experiment_id=experiment_id,
            filename=payload.filename,
            mime_type=payload.mime_type,
            size_bytes=payload.size_bytes,
            api_base_url=str(request.base_url),
        )
    except AttachmentUploadError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.put(
    "/experiments/{experiment_id}/attachments/local-upload/{object_name}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def local_upload_attachment(
    experiment_id: UUID,
    object_name: str,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Response:
    """Dev/test PUT target for signed local upload URLs."""
    await _get_owned_experiment(db, experiment_id, current_user.id)
    body = await request.body()
    content_type = request.headers.get("content-type", "application/octet-stream")
    try:
        store_local_attachment_bytes(
            experiment_id=experiment_id,
            object_name=object_name,
            file_bytes=body,
            content_type=content_type,
        )
    except AttachmentUploadError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)
