"""Waitlist signup business logic."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.waitlist_signup import WaitlistSignup
from app.integrations.ip_geolocation import lookup_ip_geolocation
from app.utils.ip_address import is_public_ip


async def record_waitlist_signup(
    db: AsyncSession,
    *,
    experiment_id: UUID,
    email: str,
    source_tag: str | None,
    client_ip: str | None,
) -> WaitlistSignup:
    """Persist a waitlist signup and enrich with IP geolocation when possible."""
    geo = None
    if client_ip and is_public_ip(client_ip):
        geo = await lookup_ip_geolocation(
            db,
            ip=client_ip,
            experiment_id=experiment_id,
        )

    signup = WaitlistSignup(
        experiment_id=experiment_id,
        email=email,
        source_tag=source_tag,
        ip_address=client_ip if is_public_ip(client_ip) else None,
        geo_city=geo.city if geo else None,
        geo_region=geo.region if geo else None,
        geo_country=geo.country if geo else None,
    )
    db.add(signup)
    await db.commit()
    await db.refresh(signup)
    return signup
