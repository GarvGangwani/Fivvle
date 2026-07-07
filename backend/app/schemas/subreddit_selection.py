from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field


class SubredditSelectionDraft(BaseModel):
    """LLM-facing structured output for subreddit picking."""

    model_config = ConfigDict(extra="forbid")

    subreddits: Annotated[
        list[
            Annotated[str, Field(min_length=2, max_length=50)]
        ],
        Field(
            min_length=0,
            max_length=8,
            description=(
                "Subreddit names WITHOUT the r/ prefix (e.g. 'startups', "
                "not '/r/startups'). Prefer subreddits where the target "
                "audience actually discusses this problem. When geography "
                "is set, prefer geography-specific subreddits (e.g. 'india' "
                "or 'bangalore' for India-scoped topics). Return empty list "
                "if the topic is too vague or no confident subreddit match "
                "exists."
            ),
        ),
    ]
    rationale: Annotated[
        str,
        Field(
            min_length=0,
            max_length=400,
            description=(
                "One or two sentence explanation of the picks. Not shown to "
                "founders — audit/debug only. Empty string is acceptable "
                "when subreddits is empty."
            ),
        ),
    ]
