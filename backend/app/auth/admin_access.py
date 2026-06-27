"""Admin access policy — email allowlist enforced server-side.

Per AGENTS.md, admin authorization must not rely on client claims.
The allowlist lives in config (ADMIN_EMAILS); sync and admin dependencies
both derive access from the verified Firebase email on the User row.
"""

from __future__ import annotations

from app.config import Settings, get_settings
from app.db.models.user import User


def admin_email_allowlist(settings: Settings | None = None) -> frozenset[str]:
    """Normalized admin emails from ADMIN_EMAILS (comma-separated)."""
    cfg = settings or get_settings()
    emails = {
        part.strip().lower()
        for part in cfg.admin_emails.split(",")
        if part.strip()
    }
    return frozenset(emails)


def is_admin_email(email: str, settings: Settings | None = None) -> bool:
    allowlist = admin_email_allowlist(settings)
    if not allowlist:
        return False
    return email.strip().lower() in allowlist


def apply_admin_role_from_email(user: User, email: str, settings: Settings | None = None) -> bool:
    """Set user.is_admin from the email allowlist. Returns True if the flag changed."""
    should_be_admin = is_admin_email(email, settings)
    if user.is_admin == should_be_admin:
        return False
    user.is_admin = should_be_admin
    return True
