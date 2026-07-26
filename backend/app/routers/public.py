"""Public endpoints — landing page delivery, waitlist signups, page-view analytics.

Per AGENTS.md «Public landing page security»:
- No authentication on any route in this module.
- Slug format validated before any database lookup.
- 404 for non-existent, unpublished, or archived pages (no information leakage).
- X-Robots-Tag: noindex, nofollow on GET /e/{slug} (default SEO opt-out).
- Structlog: slug and aggregate counts only — never email, user_agent, or referrer.

Per .cursorrules «Per-endpoint rate limits»:
- All routes: 30 req/min/IP via PUBLIC_RATE_LIMIT + ip_key.
"""

from __future__ import annotations

import re
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from slowapi.util import get_remote_address
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import LandingCtaType
from app.db.models.experiment import Experiment
from app.db.models.landing_page import LandingPage
from app.db.enums import ExperimentStatus
from app.db.models.page_view import PageView
from app.db.session import get_session
from app.logging_config import get_logger
from app.reliability.rate_limit import PUBLIC_RATE_LIMIT, ip_key, limiter
from app.services.landing_page_publish_service import get_open_cohort
from app.services.logo_upload_service import (
    local_logo_content_type,
    local_section_image_content_type,
    resolve_local_logo_path,
    resolve_local_section_image_path,
)
from app.services.attachment_upload_service import (
    local_attachment_content_type,
    resolve_local_attachment_path,
)
from app.services.waitlist_service import record_waitlist_signup

_logger = get_logger(__name__)

_SLUG_RE = re.compile(r"^[a-z0-9-]{6,40}$")
_LOGO_FILENAME_RE = re.compile(r"^[0-9a-f-]{36}\.(png|jpe?g|webp)$", re.IGNORECASE)
# UUID-prefixed attachment object names: {uuid}-{original-filename}
_ATTACHMENT_FILENAME_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}-.+$",
    re.IGNORECASE,
)
_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)

_CTA_TYPE_TO_MODE: dict[LandingCtaType, str] = {
    LandingCtaType.WAITLIST: "waitlist",
    LandingCtaType.INTEREST: "scroll",
    LandingCtaType.CONTACT: "external",
}

router = APIRouter(tags=["Public"])


def _validate_slug(slug: str) -> str:
    """Return normalized slug or raise 404 before any DB access."""
    normalized = slug.strip().lower()
    if not _SLUG_RE.match(normalized):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return normalized


class PublicLandingPageResponse(BaseModel):
    """Payload for GET /e/{slug} — consumed by the public landing page renderer."""

    model_config = ConfigDict(extra="forbid")

    slug: str
    copy_json: dict[str, Any] | None
    page_json: dict[str, Any] | None
    experiment_slug: str | None
    cta_mode: str
    cta_url: str | None
    project_name: str
    published_at: str


class WaitlistSignupRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    source_tag: str | None = Field(default=None, max_length=100)


class WaitlistSignupResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str


class PageViewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    slug: str
    source_tag: str | None = Field(default=None, max_length=100)
    referrer: str | None = Field(default=None, max_length=2048)
    user_agent: str | None = Field(default=None, max_length=500)
    time_on_page_sec: int | None = Field(default=None, ge=0)


class PageViewResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str


async def _fetch_live_landing_page(
    db: AsyncSession,
    slug: str,
) -> tuple[LandingPage, Experiment] | None:
    """Return (LandingPage, Experiment) when slug is published and not archived.

    Public reachability is artifact-gated: live_at set and status != ARCHIVED.
    Status demotion (e.g. Evidence rerun → RESEARCH_READY) must not 404 a live page.
    """
    stmt = (
        select(LandingPage, Experiment)
        .join(Experiment, LandingPage.experiment_id == Experiment.id)
        .where(
            LandingPage.slug == slug,
            LandingPage.live_at.is_not(None),
            Experiment.status != ExperimentStatus.ARCHIVED,
        )
    )
    result = await db.execute(stmt)
    row = result.first()
    if row is None:
        return None
    landing_page, experiment = row
    return landing_page, experiment


def _landing_page_to_public_payload(
    landing_page: LandingPage,
    experiment: Experiment,
) -> PublicLandingPageResponse:
    live_at = landing_page.live_at
    assert live_at is not None  # guarded by query precondition

    page_json = landing_page.page_json if isinstance(landing_page.page_json, dict) else {}
    publish_meta = page_json.get("publish") if isinstance(page_json.get("publish"), dict) else {}

    cta_mode = publish_meta.get("cta_mode") or _CTA_TYPE_TO_MODE.get(
        landing_page.cta_type,
        "waitlist",
    )
    cta_url = publish_meta.get("cta_url")
    project_name = (
        (experiment.name.strip() if experiment.name else None)
        or publish_meta.get("project_name")
        or landing_page.headline
    )

    return PublicLandingPageResponse(
        slug=landing_page.slug,
        copy_json=landing_page.copy_json,
        page_json=landing_page.page_json,
        experiment_slug=experiment.slug,
        cta_mode=str(cta_mode),
        cta_url=str(cta_url) if cta_url else None,
        project_name=str(project_name),
        published_at=live_at.isoformat(),
    )


@router.get("/e/{slug}", response_model=PublicLandingPageResponse)
@limiter.limit(PUBLIC_RATE_LIMIT, key_func=ip_key)
async def get_public_landing_page(
    request: Request,
    response: Response,
    slug: str,
    db: Annotated[AsyncSession, Depends(get_session)],
) -> PublicLandingPageResponse:
    validated_slug = _validate_slug(slug)
    row = await _fetch_live_landing_page(db, validated_slug)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    landing_page, experiment = row
    response.headers["X-Robots-Tag"] = "noindex, nofollow"

    _logger.info(
        "public landing page served",
        slug=validated_slug,
        experiment_id=str(experiment.id),
    )
    return _landing_page_to_public_payload(landing_page, experiment)


@router.post(
    "/e/{slug}/waitlist",
    response_model=WaitlistSignupResponse,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit(PUBLIC_RATE_LIMIT, key_func=ip_key)
async def submit_waitlist_signup(
    request: Request,
    response: Response,
    slug: str,
    body: WaitlistSignupRequest,
    db: Annotated[AsyncSession, Depends(get_session)],
) -> WaitlistSignupResponse:
    validated_slug = _validate_slug(slug)
    row = await _fetch_live_landing_page(db, validated_slug)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    landing_page, experiment = row
    await record_waitlist_signup(
        db,
        experiment_id=experiment.id,
        email=str(body.email).strip().lower(),
        source_tag=body.source_tag,
        client_ip=get_remote_address(request),
        landing_page_id=landing_page.id,
    )

    _logger.info(
        "waitlist signup recorded",
        slug=validated_slug,
        experiment_id=str(experiment.id),
    )
    return WaitlistSignupResponse(message="Signed up successfully")


@router.post(
    "/analytics/page-view",
    response_model=PageViewResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
@limiter.limit(PUBLIC_RATE_LIMIT, key_func=ip_key)
async def record_page_view(
    request: Request,
    response: Response,
    body: PageViewRequest,
    db: Annotated[AsyncSession, Depends(get_session)],
) -> PageViewResponse:
    # Invalid slug format — silently accept without DB lookup (no info leak).
    normalized_slug = body.slug.strip().lower()
    if not _SLUG_RE.match(normalized_slug):
        return PageViewResponse(status="recorded")

    row = await _fetch_live_landing_page(db, normalized_slug)
    if row is None:
        return PageViewResponse(status="recorded")

    landing_page, experiment = row
    cohort = await get_open_cohort(db, landing_page.id)
    publish_id = cohort.id if cohort is not None else None
    if publish_id is None:
        _logger.warning(
            "page_view_missing_cohort",
            landing_id=str(landing_page.id),
            experiment_id=str(experiment.id),
        )

    page_view = PageView(
        experiment_id=experiment.id,
        publish_id=publish_id,
        source_tag=body.source_tag,
        time_on_page_sec=body.time_on_page_sec,
        user_agent=body.user_agent,
        ip_address=get_remote_address(request),
        referrer=body.referrer,
    )
    db.add(page_view)
    await db.commit()

    _logger.info(
        "page view recorded",
        slug=normalized_slug,
        experiment_id=str(experiment.id),
    )
    return PageViewResponse(status="recorded")


@router.get("/uploads/landing-logos/{user_id}/{experiment_id}/{filename}")
@limiter.limit(PUBLIC_RATE_LIMIT, key_func=ip_key)
async def get_landing_page_logo_upload(
    request: Request,
    response: Response,
    user_id: str,
    experiment_id: str,
    filename: str,
) -> FileResponse:
    """Serve locally stored landing-page logos (development / fallback storage)."""
    if not _UUID_RE.match(user_id) or not _UUID_RE.match(experiment_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    if not _LOGO_FILENAME_RE.match(filename):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    path = resolve_local_logo_path(user_id, experiment_id, filename)
    if not path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    return FileResponse(
        path,
        media_type=local_logo_content_type(path),
        headers={"Cache-Control": "public, max-age=31536000, immutable"},
    )


@router.get("/uploads/landing-section-images/{user_id}/{experiment_id}/{filename}")
@limiter.limit(PUBLIC_RATE_LIMIT, key_func=ip_key)
async def get_landing_page_section_image_upload(
    request: Request,
    response: Response,
    user_id: str,
    experiment_id: str,
    filename: str,
) -> FileResponse:
    """Serve locally stored landing-page section images (development / fallback storage)."""
    if not _UUID_RE.match(user_id) or not _UUID_RE.match(experiment_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    if not _LOGO_FILENAME_RE.match(filename):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    path = resolve_local_section_image_path(user_id, experiment_id, filename)
    if not path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    return FileResponse(
        path,
        media_type=local_section_image_content_type(path),
        headers={"Cache-Control": "public, max-age=31536000, immutable"},
    )


@router.get("/uploads/experiment-attachments/{experiment_id}/{filename}")
@limiter.limit(PUBLIC_RATE_LIMIT, key_func=ip_key)
async def get_experiment_attachment_upload(
    request: Request,
    response: Response,
    experiment_id: str,
    filename: str,
) -> FileResponse:
    """Serve locally stored Spark attachments (development / fallback storage)."""
    if not _UUID_RE.match(experiment_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    if not _ATTACHMENT_FILENAME_RE.match(filename):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    path = resolve_local_attachment_path(experiment_id, filename)
    if not path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    return FileResponse(
        path,
        media_type=local_attachment_content_type(path),
        headers={"Cache-Control": "public, max-age=31536000, immutable"},
    )
