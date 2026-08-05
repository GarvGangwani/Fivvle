"""Write-once capture of the experiment's immutable original idea."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.chat_attachment import ChatAttachment
from app.db.models.experiment import Experiment
from app.logging_config import get_logger
from app.schemas.idea_capture import IdeaTheme
from app.services.idea_theme_service import classify_idea_theme

_logger = get_logger(__name__)

_RAW_IDEA_MAX_LEN = 2000


class IdeaAlreadyCapturedError(Exception):
    """Raised when capture is attempted after original_idea is already set."""

    def __init__(self, message: str = "Original idea already captured") -> None:
        super().__init__(message)
        self.message = message


class IdeaCaptureValidationError(Exception):
    """Invalid capture input (empty text, bad attachments, etc.)."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


@dataclass(frozen=True, slots=True)
class FrozenAttachmentRef:
    id: UUID
    original_filename: str
    content_kind: str


@dataclass(frozen=True, slots=True)
class CaptureOriginalIdeaResult:
    experiment_id: UUID
    original_idea: str
    original_idea_captured_at: datetime
    idea_theme: IdeaTheme
    frozen_attachments: list[FrozenAttachmentRef]


async def capture_original_idea(
    db: AsyncSession,
    *,
    experiment: Experiment,
    user_id: UUID,
    idea_text: str,
    attachment_ids: list[UUID],
) -> CaptureOriginalIdeaResult:
    """Freeze the original idea + attachments + theme. Write-once.

    Does not modify raw_idea, refined_idea, or spark_version.
    """
    if experiment.original_idea is not None:
        raise IdeaAlreadyCapturedError()

    stripped = idea_text.strip()
    if not stripped:
        raise IdeaCaptureValidationError("idea_text must not be empty")
    if len(idea_text) > _RAW_IDEA_MAX_LEN:
        raise IdeaCaptureValidationError(
            f"idea_text must be at most {_RAW_IDEA_MAX_LEN} characters"
        )

    unique_ids = list(dict.fromkeys(attachment_ids))
    frozen_rows = await _resolve_and_freeze_attachments(
        db,
        user_id=user_id,
        experiment_id=experiment.id,
        attachment_ids=unique_ids,
    )

    captured_at = datetime.now(UTC)
    theme = await classify_idea_theme(
        db,
        stripped,
        experiment_id=experiment.id,
    )

    experiment.original_idea = stripped
    experiment.original_idea_captured_at = captured_at
    experiment.idea_theme = theme

    await db.commit()
    await db.refresh(experiment)

    _logger.info(
        "original_idea_captured",
        experiment_id=str(experiment.id),
        theme=theme,
        attachment_count=len(frozen_rows),
    )

    return CaptureOriginalIdeaResult(
        experiment_id=experiment.id,
        original_idea=stripped,
        original_idea_captured_at=experiment.original_idea_captured_at or captured_at,
        idea_theme=theme,
        frozen_attachments=frozen_rows,
    )


async def _resolve_and_freeze_attachments(
    db: AsyncSession,
    *,
    user_id: UUID,
    experiment_id: UUID,
    attachment_ids: list[UUID],
) -> list[FrozenAttachmentRef]:
    if not attachment_ids:
        return []

    result = await db.execute(
        select(ChatAttachment).where(ChatAttachment.id.in_(attachment_ids))
    )
    rows = list(result.scalars().all())
    by_id = {row.id: row for row in rows}

    if len(by_id) != len(attachment_ids):
        raise IdeaCaptureValidationError(
            "One or more attachments are invalid or not found"
        )

    frozen: list[FrozenAttachmentRef] = []
    for attachment_id in attachment_ids:
        row = by_id[attachment_id]
        if row.user_id != user_id:
            raise IdeaCaptureValidationError(
                "One or more attachments are invalid or not found"
            )
        if (
            row.origin_experiment_id is not None
            and row.origin_experiment_id != experiment_id
        ):
            raise IdeaCaptureValidationError(
                "One or more attachments are already frozen to another experiment"
            )
        row.origin_experiment_id = experiment_id
        frozen.append(
            FrozenAttachmentRef(
                id=row.id,
                original_filename=row.original_filename,
                content_kind=row.content_kind,
            )
        )
    await db.flush()
    return frozen
