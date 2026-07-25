import type { LaunchChannel, ShareSurface } from "@/lib/api-launch-kit";

/** Founder-facing labels for LaunchChannel enum values. */
export const CHANNEL_LABELS: Record<LaunchChannel, string> = {
  reddit: "Reddit",
  twitter: "Twitter / X",
  linkedin: "LinkedIn",
  hackernews: "Hacker News",
  product_hunt: "Product Hunt",
  dm_chain: "DM Chain",
  newsletter: "Newsletter",
  community_slack: "Community Slack",
  other: "Other",
};

/** Founder-facing labels for ShareSurface enum values. */
export const SURFACE_LABELS: Record<ShareSurface, string> = {
  tweet: "Tweet",
  reddit_post: "Reddit Post",
  dm_opener: "DM Opener",
  linkedin_post: "LinkedIn Post",
  hackernews_show: "HN Show",
};

/**
 * Soft display caps (warn at 90%, red on overflow — save still allowed).
 * Schema hard cap is always SCHEMA_TEXT_HARD_CAP (1200); overflow of that blocks save.
 * HACKERNEWS_SHOW soft-caps at 80 (title-length editorial norm for a single text field).
 */
export const SHARE_COPY_SOFT_CAP: Record<ShareSurface, number> = {
  tweet: 280,
  reddit_post: 1200,
  dm_opener: 1200,
  linkedin_post: 1200,
  hackernews_show: 80,
};

export const SCHEMA_TEXT_HARD_CAP = 1200;
export const RATIONALE_MAX = 280;
export const COHORT_HINT_MAX = 500;

export const LAUNCH_CHANNELS: LaunchChannel[] = [
  "reddit",
  "twitter",
  "linkedin",
  "hackernews",
  "product_hunt",
  "dm_chain",
  "newsletter",
  "community_slack",
  "other",
];
