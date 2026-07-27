"""Waitlist signup business logic."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.waitlist_signup import WaitlistSignup
from app.integrations.ip_geolocation import lookup_ip_geolocation
from app.logging_config import get_logger
from app.services.landing_page_publish_service import get_open_cohort
from app.utils.ip_address import is_public_ip

_logger = get_logger(__name__)


async def record_waitlist_signup(
    db: AsyncSession,
    *,
    experiment_id: UUID,
    email: str,
    source_tag: str | None,
    client_ip: str | None,
    landing_page_id: UUID | None = None,
) -> WaitlistSignup:
    """Persist a waitlist signup and enrich with IP geolocation when possible."""
    publish_id: UUID | None = None
    if landing_page_id is not None:
        cohort = await get_open_cohort(db, landing_page_id)
        if cohort is not None:
            publish_id = cohort.id
        else:
            _logger.warning(
                "waitlist_signup_missing_cohort",
                landing_id=str(landing_page_id),
                experiment_id=str(experiment_id),
            )

    geo = None
    if client_ip and is_public_ip(client_ip):
        geo = await lookup_ip_geolocation(
            db,
            ip=client_ip,
            experiment_id=experiment_id,
        )

    signup = WaitlistSignup(
        experiment_id=experiment_id,
        publish_id=publish_id,
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
