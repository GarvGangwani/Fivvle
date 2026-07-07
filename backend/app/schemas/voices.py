"""Voices phase schema — Reddit-sourced qualitative evidence.

VoicesEvidence is the Voices analog to ExtractedEvidence. Reader remains
frozen and Tavily-only (per ADR 0012); Voices produces its own atoms
with Reddit-specific metadata.

Post-parse validation (in voices_service): verbatim_quote MUST be an
exact substring of the source post/comment content. Same anti-
hallucination guard pattern as Reader.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field


class VoicesEvidenceDraft(BaseModel):
    """LLM-facing atom shape."""

    model_config = ConfigDict(extra="forbid")

    source_url: Annotated[
        str,
        Field(
            max_length=500,
            description=(
                "The full Reddit URL of the post or comment this quote comes "
                "from. Must be a URL that appeared in the <reddit_content> "
                "block. Format: https://reddit.com/r/<sub>/comments/<id>/... "
                "Do NOT fabricate URLs."
            ),
        ),
    ]

    subreddit: Annotated[
        str,
        Field(
            max_length=50,
            description=(
                "The subreddit name without r/ prefix (e.g. 'india', "
                "'startups'). Must match the subreddit in source_url."
            ),
        ),
    ]

    kind: Literal["post", "comment"] = Field(
        description="Whether the quote is from a post body or a comment.",
    )

    verbatim_quote: Annotated[
        str,
        Field(
            min_length=10,
            max_length=500,
            description=(
                "The exact quote from the post or comment, character-for-"
                "character. Do NOT paraphrase. The system verifies this is "
                "an exact substring of the source content. If no quotable "
                "phrase captures the point, skip this atom entirely — do "
                "not fabricate."
            ),
        ),
    ]

    pain_pattern: Annotated[
        str,
        Field(
            min_length=20,
            max_length=400,
            description=(
                "1-2 sentences describing what pain, need, or preference "
                "this quote reveals. Concrete: 'user is frustrated that X "
                "existing tool costs Y', not 'user has some complaints'."
            ),
        ),
    ]

    on_target_geography: bool = Field(
        description=(
            "True if this quote is from a geography-native subreddit for "
            "the target market (r/india for India-scoped experiments). "
            "False for global/other-geography subreddits. Set based on "
            "the subreddit-to-geography mapping the LLM was told."
        ),
    )

    signal_strength: Literal["strong", "moderate", "weak"] = Field(
        description=(
            "'strong' when the quote is unambiguous, specific, and on-topic. "
            "'moderate' when it's on-topic but qualified or partial. "
            "'weak' when the connection to the founder's idea is tangential."
        ),
    )


class VoicesEvidence(VoicesEvidenceDraft):
    """Post-validation atom. Same shape as draft, semantically trusted.

    Quote substring check has passed. URL has been confirmed to be in the
    fetched Reddit content.
    """


class VoicesOutput(BaseModel):
    """The Voices phase's output, consumed by Synthesizer."""

    model_config = ConfigDict(extra="forbid")

    atoms: Annotated[
        list[VoicesEvidence],
        Field(
            min_length=0,
            max_length=15,
            description=(
                "0-15 VoicesEvidence atoms. Empty when subreddit selection "
                "failed, PRAW failed, LLM extraction failed, or no relevant "
                "content was found."
            ),
        ),
    ]
    subreddits_searched: Annotated[
        list[str],
        Field(
            default_factory=list,
            max_length=8,
            description="Subreddits that were actually fetched from.",
        ),
    ]
    threads_fetched: int = Field(default=0)
    comments_fetched: int = Field(default=0)
    skipped_reason: str | None = Field(
        default=None,
        max_length=200,
        description=(
            "If atoms is empty, one-sentence machine-readable reason "
            "(e.g. 'subreddit_selection_returned_empty', 'praw_all_failed', "
            "'llm_extraction_failed', 'no_relevant_content'). Null when "
            "atoms is non-empty."
        ),
    )
