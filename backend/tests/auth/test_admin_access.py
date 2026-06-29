"""Tests for admin email allowlist."""

from types import SimpleNamespace

from app.auth.admin_access import (
    apply_admin_role_from_email,
    is_admin_email,
)
from app.db.models.user import User


def test_is_admin_email_matches_allowlist_case_insensitive() -> None:
    settings = SimpleNamespace(admin_emails="FivvleIO@gmail.com, ops@example.com")
    assert is_admin_email("fivvleio@gmail.com", settings)  # type: ignore[arg-type]
    assert is_admin_email("OPS@example.com", settings)  # type: ignore[arg-type]
    assert not is_admin_email("other@example.com", settings)  # type: ignore[arg-type]


def test_apply_admin_role_from_email_updates_user() -> None:
    settings = SimpleNamespace(admin_emails="fivvleio@gmail.com")
    user = User(
        firebase_uid="uid",
        email="fivvleio@gmail.com",
        is_admin=False,
    )
    assert apply_admin_role_from_email(user, user.email, settings) is True  # type: ignore[arg-type]
    assert user.is_admin is True
    assert apply_admin_role_from_email(user, user.email, settings) is False  # type: ignore[arg-type]
