"""Tests for MCQ answer metadata helpers and ChatMessageItem mapping."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from app.db.enums import ChatRole
from app.db.models.chat_message import ChatMessage
from app.schemas.chat import ChatMessageItem
from app.services.chat_service import build_user_message_metadata


def test_build_user_message_metadata_includes_indices_and_custom() -> None:
    qid = uuid4()
    meta = build_user_message_metadata(
        selected_option_indices=[0, 2],
        custom_added_text="hospitality only",
        answered_question_from_message_id=qid,
    )
    assert meta is not None
    assert meta["selected_option_indices"] == [0, 2]
    assert meta["custom_added_text"] == "hospitality only"
    assert meta["answered_question_from_message_id"] == str(qid)


def test_build_user_message_metadata_empty_returns_none() -> None:
    assert build_user_message_metadata() is None


def test_chat_message_item_maps_metadata_json() -> None:
    msg = ChatMessage(
        id=uuid4(),
        thread_id=uuid4(),
        role=ChatRole.USER,
        content="B2B · hospitality only",
        metadata_json={
            "selected_option_indices": [0],
            "custom_added_text": "hospitality only",
        },
        created_at=datetime.now(UTC),
    )
    item = ChatMessageItem.from_orm_message(msg)
    assert item.metadata is not None
    assert item.metadata["selected_option_indices"] == [0]
    assert item.metadata["custom_added_text"] == "hospitality only"
