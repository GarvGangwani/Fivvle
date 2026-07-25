/**
 * Platform compose intent URLs for Launch Kit share-copy post actions.
 *
 * Separate from `SHARE_CHANNELS` / trackable landing links — those copy a
 * landing-page URL; these open (or degrade to) a platform compose flow with
 * share-copy text.
 */

import type { ShareSurface } from "@/lib/api-launch-kit";
import { buildTrackedLandingPageUrl } from "@/lib/published-page";

/** utm_source tags for appending a tracked link into share posts. */
export const SURFACE_UTM_MAP: Record<ShareSurface, string> = {
  tweet: "twitter",
  reddit_post: "reddit",
  linkedin_post: "linkedin",
  hackernews_show: "hackernews",
  dm_opener: "dm",
};

const REDDIT_TITLE_MAX = 300;

export type SharePostMode = "prefill" | "copy_open" | "copy_only";

export type SharePostAction = {
  mode: SharePostMode;
  /** Uppercase brutalist button label. */
  buttonLabel: string;
  /** Compose / feed URL to open in a new tab, or null when copy-only with no target. */
  openUrl: string | null;
  /** Clipboard payload for copy_open / copy_only (and HN degradation). */
  clipboardText: string;
  /** Toast after copy (copy modes only). */
  toastMessage: string | null;
};

export type BuildSharePostActionArgs = {
  surface: ShareSurface;
  text: string;
  experimentName: string;
  slug: string | null;
  isLive: boolean;
};

/** Truncate at a word boundary with no ellipsis. Hard-cuts if no space in the window. */
export function truncateAtWordBoundary(text: string, max: number): string {
  if (max <= 0) return "";
  if (text.length <= max) return text;
  const sliced = text.slice(0, max);
  const lastSpace = sliced.lastIndexOf(" ");
  if (lastSpace > Math.floor(max / 2)) {
    return sliced.slice(0, lastSpace).trimEnd();
  }
  return sliced.trimEnd();
}

/**
 * Split a single share-copy blob into Reddit title + body.
 *
 * - Multi-line: first non-empty line = title; rest = body.
 * - Single paragraph: title = truncate ≤300 at word boundary; body = full text.
 * - Empty title after split → fall back to `experimentName`.
 */
export function splitRedditTitleBody(
  text: string,
  experimentName: string,
): { title: string; body: string } {
  const normalized = text.replace(/\r\n/g, "\n").trim();
  const lines = normalized.split("\n");
  const firstNonEmptyIdx = lines.findIndex((l) => l.trim().length > 0);

  let title: string;
  let body: string;

  if (firstNonEmptyIdx >= 0 && lines.length > firstNonEmptyIdx + 1) {
    title = lines[firstNonEmptyIdx]!.trim();
    body = lines
      .slice(firstNonEmptyIdx + 1)
      .join("\n")
      .trim();
  } else {
    const single = normalized;
    title = truncateAtWordBoundary(single, REDDIT_TITLE_MAX);
    body = single;
  }

  if (!title.trim()) {
    title = experimentName.trim() || "Untitled";
  } else if (title.length > REDDIT_TITLE_MAX) {
    title = truncateAtWordBoundary(title, REDDIT_TITLE_MAX);
  }

  return { title, body };
}

function appendUrl(body: string, url: string | null): string {
  if (!url) return body;
  const trimmed = body.trimEnd();
  if (!trimmed) return url;
  if (trimmed.includes(url)) return trimmed;
  return `${trimmed}\n\n${url}`;
}

function trackedUrlFor(
  surface: ShareSurface,
  slug: string | null,
  isLive: boolean,
): string | null {
  if (!isLive || !slug) return null;
  return buildTrackedLandingPageUrl(slug, SURFACE_UTM_MAP[surface]);
}

function twitterIntentUrl(text: string): string {
  const url = new URL("https://twitter.com/intent/tweet");
  url.searchParams.set("text", text);
  return url.toString();
}

function redditSubmitUrl(title: string, body: string): string {
  const url = new URL("https://www.reddit.com/submit");
  url.searchParams.set("title", title);
  url.searchParams.set("text", body);
  return url.toString();
}

function hnSubmitUrl(pageUrl: string, title: string): string {
  const url = new URL("https://news.ycombinator.com/submitlink");
  url.searchParams.set("u", pageUrl);
  url.searchParams.set("t", title);
  return url.toString();
}

/**
 * Build the post-action descriptor for a share-copy variant.
 *
 * PREFILL: tweet, reddit_post, hackernews_show (when live).
 * COPY_OPEN: linkedin_post (copy text, open feed).
 * COPY_ONLY: dm_opener; hackernews_show when not live.
 */
export function buildSharePostAction(
  args: BuildSharePostActionArgs,
): SharePostAction {
  const { surface, text, experimentName, slug, isLive } = args;
  const tracked = trackedUrlFor(surface, slug, isLive);
  const clipboardBase = text.trim();

  switch (surface) {
    case "tweet": {
      const tweetText = appendUrl(clipboardBase, tracked);
      return {
        mode: "prefill",
        buttonLabel: "POST TO TWITTER",
        openUrl: twitterIntentUrl(tweetText),
        clipboardText: tweetText,
        toastMessage: null,
      };
    }
    case "reddit_post": {
      const { title, body } = splitRedditTitleBody(text, experimentName);
      const bodyWithUrl = appendUrl(body, tracked);
      return {
        mode: "prefill",
        buttonLabel: "POST TO REDDIT",
        openUrl: redditSubmitUrl(title, bodyWithUrl),
        clipboardText: appendUrl(
          title === body ? body : `${title}\n\n${body}`,
          tracked,
        ),
        toastMessage: null,
      };
    }
    case "hackernews_show": {
      if (!tracked) {
        return {
          mode: "copy_only",
          buttonLabel: "COPY",
          openUrl: null,
          clipboardText: clipboardBase,
          toastMessage: "Copied — paste it into your HN submission",
        };
      }
      return {
        mode: "prefill",
        buttonLabel: "POST TO HN",
        openUrl: hnSubmitUrl(tracked, clipboardBase),
        clipboardText: clipboardBase,
        toastMessage: null,
      };
    }
    case "linkedin_post": {
      return {
        mode: "copy_open",
        buttonLabel: "COPY & OPEN LINKEDIN",
        openUrl: "https://www.linkedin.com/feed/",
        clipboardText: appendUrl(clipboardBase, tracked),
        toastMessage: "Copied — paste it into your LinkedIn post",
      };
    }
    case "dm_opener": {
      return {
        mode: "copy_only",
        buttonLabel: "COPY",
        openUrl: null,
        clipboardText: appendUrl(clipboardBase, tracked),
        toastMessage: "Copied — send it as a DM",
      };
    }
    default: {
      const _exhaustive: never = surface;
      return _exhaustive;
    }
  }
}
