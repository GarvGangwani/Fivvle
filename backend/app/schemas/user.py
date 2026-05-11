"""User-related Pydantic schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr


class UserSyncRequest(BaseModel):
    """Request body for POST /users/sync.

    The Firebase ID token in the Authorization header is the source of truth
    for firebase_uid and email — this body just carries an optional display
    name from the signup form.
    """

    model_config = ConfigDict(extra="forbid")

    name: str | None = None


class UserResponse(BaseModel):
    """Public user representation returned to the frontend.

    Does NOT include firebase_uid (internal identifier) or credits_remaining
    (admin concept, not exposed to founders in MVP).
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    name: str | None
    created_at: datetime
