"""Voices phase — Perplexity-scoped Reddit qualitative evidence extraction.

Public API: execute_voices(...) → VoicesOutput. Never raises.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

import app.integrations.perplexity as perplexity_integration
import app.llm.client as llm_client
from app.config import Settings
from app.llm.prompts.voices import (
    PROMPT_NAME,
    VOICES_EXTRACTION_SYSTEM_PROMPT,
    VoicesExtractionDraft,
    build_voices_extraction_user_prompt,
)
from app.logging_config import get_logger
from app.schemas.planner import ResearchPlan
from app.schemas.refinement import RefinedIdea
from app.schemas.targeting import ExperimentTargeting
from app.schemas.voices import VoicesEvidence, VoicesOutput
from app.services.subreddit_selection_service import get_subreddits_for_topic
from app.services.voices_geography import build_subreddit_geography_map

_logger = get_logger(__name__)

_MAX_TOKENS = 8000
_TEMPERATURE = 0.2


@dataclass
class _FetchedComment:
    url: str
    subreddit: str
    body: str
    score: int
    created_utc: float


@dataclass
class _FetchedPost:
    url: str
    subreddit: str
    title: str
    selftext: str
    score: int | None = None
    created_utc: float | None = None
    post_id: str | None = None
    comments: list[_FetchedComment] = field(default_factory=list)


def _derive_topic(refined_idea: RefinedIdea) -> str:
    parts = [refined_idea.refined_one_liner, refined_idea.value_proposition]
    topic = " — ".join(p.strip() for p in parts if p and p.strip())
    return topic[:300]



def _is_post_too_old(created_utc: float | None, max_age_days: int) -> bool:
    if created_utc is None:
        return False
    cutoff = time.time() - (max_age_days * 86400)
    return created_utc < cutoff


def _exc_http_status_code(exc: BaseException) -> int | None:
    """Extract HTTP status from integration errors or httpx response errors."""
    status_code: int | None = getattr(exc, "status_code", None)
    if status_code is None:
        response_obj = getattr(exc, "response", None)
        if response_obj is not None:
            status_code = getattr(response_obj, "status_code", None)
    return status_code


def _serialize_reddit_content(posts: list[_FetchedPost]) -> str:
    lines: list[str] = []
    for post in posts:
        body = f"{post.title}\n{post.selftext}".strip()
        attrs = [
            f'subreddit="{post.subreddit}"',
            f'url="{post.url}"',
            'kind="post"',
        ]
        if post.score is not None:
            attrs.append(f'score="{post.score}"')
        if post.created_utc is not None:
            attrs.append(f'created_utc="{post.created_utc}"')
        lines.append(
            f"<post {' '.join(attrs)}>\n{body}\n</post>"
        )
        for comment in post.comments:
            comment_attrs = [
                f'subreddit="{comment.subreddit}"',
                f'url="{comment.url}"',
                'kind="comment"',
            ]
            if comment.score is not None:
                comment_attrs.append(f'score="{comment.score}"')
            if comment.created_utc is not None:
                comment_attrs.append(f'created_utc="{comment.created_utc}"')
            lines.append(
                f"<comment {' '.join(comment_attrs)}>\n{comment.body}\n</comment>"
            )
    return "\n\n".join(lines)


def _url_to_content(posts: list[_FetchedPost]) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for post in posts:
        mapping[post.url] = f"{post.title}\n{post.selftext}".strip()
        for comment in post.comments:
            mapping[comment.url] = comment.body
    return mapping


def _validate_atoms(
    drafts: list,
    url_to_content: dict[str, str],
) -> list[VoicesEvidence]:
    validated: list[VoicesEvidence] = []
    dropped = 0
    for draft in drafts:
        content = url_to_content.get(draft.source_url)
        if content is None:
            dropped += 1
            continue
        if draft.verbatim_quote not in content:
            dropped += 1
            continue
        validated.append(VoicesEvidence.model_validate(draft.model_dump()))
    if dropped:
        _logger.warning(
            "voices quote validation dropped atoms",
            dropped_count=dropped,
            kept_count=len(validated),
        )
    return validated


async def _fetch_subreddit_posts(
    db: AsyncSession,
    *,
    query: str,
    subreddit: str,
    limit: int,
    experiment_id: UUID,
    comments_per_thread: int,  # noqa: ARG001 — retained for call-site stability
    max_age_days: int,
    semaphore: asyncio.Semaphore,
) -> list[_FetchedPost]:
    async with semaphore:
        try:
            results = await perplexity_integration.search(
                db,
                query=query,
                experiment_id=experiment_id,
                domain_filter=[f"reddit.com/r/{subreddit}"],
                max_results=limit,
            )
        except Exception as exc:
            _logger.warning(
                "voices subreddit fetch failed",
                error_type=type(exc).__name__,
                status_code=_exc_http_status_code(exc),
                subreddit=subreddit,
            )
            return []

    fetched: list[_FetchedPost] = []
    for result in results:
        post = _FetchedPost(
            url=result.url,
            subreddit=subreddit.lower(),
            title=result.title,
            selftext=result.snippet,
            score=None,
            created_utc=None,
            post_id=None,
            comments=[],
        )
        if _is_post_too_old(post.created_utc, max_age_days):
            continue
        fetched.append(post)
    return fetched


async def execute_voices(
    *,
    db: AsyncSession,
    refined_idea: RefinedIdea,
    research_plan: ResearchPlan,  # noqa: ARG001 — reserved for future query tuning
    targeting: ExperimentTargeting | None,
    experiment_id: UUID,
    settings: Settings,
) -> VoicesOutput:
    """Run Voices phase. Never raises — returns empty VoicesOutput on failure."""
    try:
        return await _execute_voices_inner(
            db=db,
            refined_idea=refined_idea,
            targeting=targeting,
            experiment_id=experiment_id,
            settings=settings,
        )
    except Exception as exc:
        _logger.warning(
            "voices phase unexpected error",
            error_type=type(exc).__name__,
            experiment_id=str(experiment_id),
        )
        return VoicesOutput(atoms=[], skipped_reason="voices_service_raised")


async def _execute_voices_inner(
    *,
    db: AsyncSession,
    refined_idea: RefinedIdea,
    targeting: ExperimentTargeting | None,
    experiment_id: UUID,
    settings: Settings,
) -> VoicesOutput:
    topic = _derive_topic(refined_idea)
    geography = targeting.target_geography if targeting else None

    subreddits = await get_subreddits_for_topic(
        db,
        topic=topic,
        geography=geography,
        experiment_id=experiment_id,
    )
    if not subreddits:
        return VoicesOutput(
            atoms=[],
            skipped_reason="subreddit_selection_returned_empty",
        )

    max_subs = settings.voices_max_subreddits
    threads_per = settings.voices_threads_per_subreddit
    comments_per = settings.voices_comments_per_thread
    max_age = settings.voices_post_max_age_days
    concurrency = settings.voices_reddit_concurrency

    selected = subreddits[:max_subs]
    semaphore = asyncio.Semaphore(concurrency)

    results = await asyncio.gather(
        *[
            _fetch_subreddit_posts(
                db,
                query=topic,
                subreddit=sub,
                limit=threads_per,
                experiment_id=experiment_id,
                comments_per_thread=comments_per,
                max_age_days=max_age,
                semaphore=semaphore,
            )
            for sub in selected
        ]
    )

    all_posts: list[_FetchedPost] = []
    subreddits_searched: list[str] = []
    for sub, posts in zip(selected, results, strict=True):
        if posts:
            subreddits_searched.append(sub)
            all_posts.extend(posts)

    threads_fetched = len(all_posts)
    comments_fetched = 0

    if not all_posts:
        return VoicesOutput(
            atoms=[],
            subreddits_searched=subreddits_searched,
            threads_fetched=0,
            comments_fetched=0,
            # retained for Rule 5 pattern match; renaming is a follow-up PR
            skipped_reason="praw_all_failed",
        )

    reddit_content = _serialize_reddit_content(all_posts)
    if not reddit_content.strip():
        return VoicesOutput(
            atoms=[],
            subreddits_searched=subreddits_searched,
            threads_fetched=threads_fetched,
            comments_fetched=comments_fetched,
            skipped_reason="no_relevant_content",
        )

    geo_map = build_subreddit_geography_map(subreddits_searched, geography)

    try:
        draft, meta = await llm_client.complete_structured(
            db,
            provider=settings.voices_extraction_provider,
            model=settings.voices_extraction_model,
            prompt_name=PROMPT_NAME,
            system=VOICES_EXTRACTION_SYSTEM_PROMPT,
            user=build_voices_extraction_user_prompt(
                refined_idea,
                targeting,
                reddit_content,
                geo_map,
            ),
            response_model=VoicesExtractionDraft,
            max_tokens=_MAX_TOKENS,
            temperature=_TEMPERATURE,
            max_retries=2,
            experiment_id=experiment_id,
            phase="voices_extraction",
        )
    except Exception as exc:
        _logger.warning(
            "voices extraction LLM failed",
            error_type=type(exc).__name__,
            experiment_id=str(experiment_id),
        )
        return VoicesOutput(
            atoms=[],
            subreddits_searched=subreddits_searched,
            threads_fetched=threads_fetched,
            comments_fetched=comments_fetched,
            skipped_reason="llm_extraction_failed",
        )

    url_to_content = _url_to_content(all_posts)
    atoms = _validate_atoms(draft.atoms, url_to_content)

    if not atoms:
        return VoicesOutput(
            atoms=[],
            subreddits_searched=subreddits_searched,
            threads_fetched=threads_fetched,
            comments_fetched=comments_fetched,
            skipped_reason="no_relevant_content",
        )

    _logger.info(
        "voices extraction complete",
        experiment_id=str(experiment_id),
        atom_count=len(atoms),
        threads_fetched=threads_fetched,
        comments_fetched=comments_fetched,
        subreddit_count=len(subreddits_searched),
        cost_usd=str(meta.cost_usd),
        latency_ms=meta.latency_ms,
    )

    return VoicesOutput(
        atoms=atoms,
        subreddits_searched=subreddits_searched,
        threads_fetched=threads_fetched,
        comments_fetched=comments_fetched,
        skipped_reason=None,
    )
