"""Analytics aggregator — derives AnalyticsAggregate from landing-page telemetry.

Pure DB-read service: no LLM calls, no writes, no status transitions.
Produces the structured input contract for the B4 insight generator LLM
(``docs/planning/b4-insight-generator.md`` §4.1).

Per AGENTS.md "Logging hygiene":
    Log experiment_id and aggregate counts only — never emails, IPs, or source_tag
    values.
"""

from __future__ import annotations

from datetime import datetime, timezone
from statistics import median
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.landing_page import LandingPage
from app.db.models.page_view import PageView
from app.db.models.waitlist_signup import WaitlistSignup
from app.integrations.ip_geolocation import location_label
from app.logging_config import get_logger
from app.schemas.insight import AnalyticsAggregate, SignupLocationBucket

_logger = get_logger(__name__)

# v1 heuristic — refine after observing real founder tagging patterns.
# Source tags treated as "warm" for warm_network_bias_index calculation.
# Matching is case-insensitive substring match against source_tag.
WARM_SOURCE_TAG_PATTERNS: tuple[str, ...] = (
    "twitter",
    "linkedin",
    "discord",
    "slack",
    "personal",
    "founder",
    "warm",
    "friends",
    "network",
)


class LandingPageNotLiveError(Exception):
    """Raised when the experiment has no LandingPage with a non-null live_at."""


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def _normalize_source_tag(source_tag: str | None) -> str:
    return source_tag if source_tag is not None else "unknown"


def _is_warm_source(source_tag: str) -> bool:
    if source_tag == "unknown":
        return False
    lower = source_tag.lower()
    return any(pattern in lower for pattern in WARM_SOURCE_TAG_PATTERNS)


def _percentile_p90(sorted_times: list[int]) -> int:
    idx = int(0.9 * (len(sorted_times) - 1))
    return sorted_times[idx]


def _build_signups_by_location(
    waitlist_signups: list[WaitlistSignup],
) -> list[SignupLocationBucket]:
    counts: dict[tuple[str | None, str | None, str | None], int] = {}
    for signup in waitlist_signups:
        key = (signup.geo_city, signup.geo_region, signup.geo_country)
        counts[key] = counts.get(key, 0) + 1

    buckets = [
        SignupLocationBucket(
            city=city,
            region=region,
            country=country,
            count=count,
        )
        for (city, region, country), count in counts.items()
    ]
    buckets.sort(
        key=lambda bucket: (
            -bucket.count,
            location_label(city=bucket.city, region=bucket.region, country=bucket.country),
        )
    )
    return buckets


async def build_analytics_aggregate(
    db: AsyncSession,
    experiment_id: UUID,
) -> AnalyticsAggregate:
    """Build AnalyticsAggregate from page_views + waitlist_signups + landing_page.

    Raises LandingPageNotLiveError if the experiment has no live landing page
    (the aggregator is meant to be called only after Stage 4 publish).
    """
    lp_result = await db.execute(
        select(LandingPage).where(LandingPage.experiment_id == experiment_id)
    )
    landing_page = lp_result.scalar_one_or_none()
    if landing_page is None or landing_page.live_at is None:
        raise LandingPageNotLiveError(
            f"Experiment {experiment_id} has no published landing page (live_at is null)"
        )

    now = datetime.now(timezone.utc)
    days_live = max(0, (now - landing_page.live_at).days)
    live_date = landing_page.live_at.astimezone(timezone.utc).date()

    pv_result = await db.execute(
        select(PageView)
        .where(PageView.experiment_id == experiment_id)
        .order_by(PageView.ts.asc())
    )
    page_views = list(pv_result.scalars().all())

    ws_result = await db.execute(
        select(WaitlistSignup)
        .where(WaitlistSignup.experiment_id == experiment_id)
        .order_by(WaitlistSignup.ts.asc())
    )
    waitlist_signups = list(ws_result.scalars().all())

    total_page_views = len(page_views)
    total_signups = len(waitlist_signups)

    data_quality_notes: list[str] = []

    non_null_ips = {pv.ip_address for pv in page_views if pv.ip_address is not None}
    if total_page_views > 0 and len(non_null_ips) == 0:
        unique_visitors = total_page_views
        data_quality_notes.append(
            "All page views missing IP address — unique-visitor count falls back to total views."
        )
    else:
        unique_visitors = len(non_null_ips)

    if total_page_views > 0:
        conversion_rate = _clamp01(total_signups / total_page_views)
    else:
        conversion_rate = 0.0

    views_by_source: dict[str, int] = {}
    for pv in page_views:
        tag = _normalize_source_tag(pv.source_tag)
        views_by_source[tag] = views_by_source.get(tag, 0) + 1

    signups_by_source: dict[str, int] = {}
    for ws in waitlist_signups:
        tag = _normalize_source_tag(ws.source_tag)
        signups_by_source[tag] = signups_by_source.get(tag, 0) + 1

    conversion_rate_by_source: dict[str, float] = {}
    for tag, view_count in views_by_source.items():
        if view_count > 0:
            rate = signups_by_source.get(tag, 0) / view_count
        else:
            rate = 0.0
        conversion_rate_by_source[tag] = _clamp01(rate)

    if total_page_views > 0:
        warm_view_count = sum(
            count
            for tag, count in views_by_source.items()
            if _is_warm_source(tag)
        )
        warm_network_bias_index = _clamp01(warm_view_count / total_page_views)
    else:
        warm_network_bias_index = 0.0

    non_null_times = [
        pv.time_on_page_sec
        for pv in page_views
        if pv.time_on_page_sec is not None
    ]
    if len(non_null_times) == 0:
        time_on_page_p50_seconds = 0
        time_on_page_p90_seconds = 0
        if total_page_views > 0:
            data_quality_notes.append(
                "No time_on_page data captured — percentiles default to 0."
            )
    else:
        sorted_times = sorted(non_null_times)
        time_on_page_p50_seconds = int(median(sorted_times))
        time_on_page_p90_seconds = _percentile_p90(sorted_times)

    views_by_day: list[int] = []
    signups_by_day: list[int] = []
    for day_idx in range(days_live):
        views_by_day.append(
            sum(
                1
                for pv in page_views
                if (pv.ts.astimezone(timezone.utc).date() - live_date).days == day_idx
            )
        )
        signups_by_day.append(
            sum(
                1
                for ws in waitlist_signups
                if (ws.ts.astimezone(timezone.utc).date() - live_date).days == day_idx
            )
        )

    drop_off_signals: dict[str, str] = {}
    if total_page_views > 50 and total_signups == 0:
        drop_off_signals["zero_conversion"] = (
            "≥50 views with zero signups — check CTA visibility or value proposition clarity"
        )
    if time_on_page_p90_seconds > 0 and time_on_page_p50_seconds == 0:
        drop_off_signals["bimodal_engagement"] = (
            "Engagement distribution is bimodal — half of visitors leave instantly, "
            "the other half spend significant time"
        )

    if total_page_views > 0:
        for tag, count in views_by_source.items():
            if count > 0.9 * total_page_views:
                data_quality_notes.append(
                    f"Traffic concentrated on a single source ({tag}) — "
                    "results may not generalize."
                )
                break

    if days_live > 0 and total_page_views == 0:
        data_quality_notes.append(
            f"Landing page has been live {days_live} day(s) with zero traffic — "
            "distribute the URL before generating insights."
        )

    if total_page_views > 0 and days_live > 0:
        daily_avg = total_page_views / max(days_live, 1)
        spike_threshold = 5 * daily_avg
        for idx, day_views in enumerate(views_by_day):
            if day_views > spike_threshold:
                data_quality_notes.append(
                    f"Day {idx} traffic spike ({day_views} views) is >5x the daily "
                    "average — possible bot or campaign event."
                )

    aggregate = AnalyticsAggregate(
        days_live=days_live,
        total_page_views=total_page_views,
        unique_visitors=unique_visitors,
        total_signups=total_signups,
        conversion_rate=conversion_rate,
        views_by_source=views_by_source,
        signups_by_source=signups_by_source,
        conversion_rate_by_source=conversion_rate_by_source,
        signups_by_location=_build_signups_by_location(waitlist_signups),
        warm_network_bias_index=warm_network_bias_index,
        time_on_page_p50_seconds=time_on_page_p50_seconds,
        time_on_page_p90_seconds=time_on_page_p90_seconds,
        signups_by_day=signups_by_day,
        views_by_day=views_by_day,
        drop_off_signals=drop_off_signals,
        data_quality_notes=data_quality_notes,
    )

    _logger.info(
        "analytics aggregate built",
        experiment_id=str(experiment_id),
        days_live=days_live,
        total_page_views=total_page_views,
        total_signups=total_signups,
        unique_source_count=len(views_by_source),
        warm_network_bias_index=warm_network_bias_index,
    )

    return aggregate
