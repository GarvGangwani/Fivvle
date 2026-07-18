import { describe, expect, it } from "vitest";

import {
  SURFACE_UTM_MAP,
  buildSharePostAction,
  splitRedditTitleBody,
  truncateAtWordBoundary,
} from "../launch-channel-intents";

describe("SURFACE_UTM_MAP", () => {
  it("maps every ShareSurface to a dedicated utm tag", () => {
    expect(SURFACE_UTM_MAP).toEqual({
      tweet: "twitter",
      reddit_post: "reddit",
      linkedin_post: "linkedin",
      hackernews_show: "hackernews",
      dm_opener: "dm",
    });
  });
});

describe("truncateAtWordBoundary", () => {
  it("returns text unchanged when under the max", () => {
    expect(truncateAtWordBoundary("short title", 300)).toBe("short title");
  });

  it("truncates at a word boundary with no ellipsis", () => {
    const words = Array.from({ length: 80 }, (_, i) => `word${i}`).join(" ");
    const out = truncateAtWordBoundary(words, 300);
    expect(out.length).toBeLessThanOrEqual(300);
    expect(out.endsWith("...")).toBe(false);
    expect(out.includes("…")).toBe(false);
    expect(out.endsWith(" ")).toBe(false);
  });

  it("hard-cuts when there is no space in the window", () => {
    const blob = "a".repeat(400);
    expect(truncateAtWordBoundary(blob, 300)).toBe("a".repeat(300));
  });
});

describe("splitRedditTitleBody", () => {
  it("uses first non-empty line as title and the rest as body (multi-line)", () => {
    const { title, body } = splitRedditTitleBody(
      "Hook line\n\nBody paragraph one.\nBody paragraph two.",
      "My Project",
    );
    expect(title).toBe("Hook line");
    expect(body).toBe("Body paragraph one.\nBody paragraph two.");
  });

  it("truncates a single-paragraph blob for title and keeps full text as body", () => {
    const words = Array.from({ length: 80 }, (_, i) => `word${i}`).join(" ");
    expect(words.length).toBeGreaterThan(300);
    const { title, body } = splitRedditTitleBody(words, "My Project");
    expect(title.length).toBeLessThanOrEqual(300);
    expect(title.endsWith("...")).toBe(false);
    expect(body).toBe(words);
  });

  it("falls back to experimentName when title would be empty", () => {
    const { title, body } = splitRedditTitleBody("\n\n   \n", "Fallback Name");
    expect(title).toBe("Fallback Name");
    expect(body).toBe("");
  });

  it("truncates an over-300 first line without ellipsis", () => {
    const longLine = Array.from({ length: 80 }, (_, i) => `title${i}`).join(" ");
    const { title, body } = splitRedditTitleBody(
      `${longLine}\nRest of the post.`,
      "My Project",
    );
    expect(title.length).toBeLessThanOrEqual(300);
    expect(title.endsWith("...")).toBe(false);
    expect(body).toBe("Rest of the post.");
  });
});

describe("buildSharePostAction", () => {
  const base = {
    text: "Ship this thing",
    experimentName: "Fivvle",
    slug: "fivvle-demo",
    isLive: true,
  };

  it("builds a Twitter intent URL with text and tracked link", () => {
    const action = buildSharePostAction({ ...base, surface: "tweet" });
    expect(action.mode).toBe("prefill");
    expect(action.buttonLabel).toBe("POST TO TWITTER");
    expect(action.openUrl).toContain("twitter.com/intent/tweet");
    const tweetText = new URL(action.openUrl!).searchParams.get("text");
    expect(tweetText).toContain("Ship this thing");
    expect(tweetText).toContain("utm_source=twitter");
  });

  it("builds a Reddit submit URL with title + body split", () => {
    const action = buildSharePostAction({
      ...base,
      surface: "reddit_post",
      text: "Title here\nBody here",
    });
    expect(action.mode).toBe("prefill");
    expect(action.buttonLabel).toBe("POST TO REDDIT");
    expect(action.openUrl).toContain("reddit.com/submit");
    expect(action.openUrl).toContain("title=Title");
    expect(action.openUrl).toContain("text=Body");
  });

  it("prefills HN with url + title when live", () => {
    const action = buildSharePostAction({
      ...base,
      surface: "hackernews_show",
    });
    expect(action.mode).toBe("prefill");
    expect(action.buttonLabel).toBe("POST TO HN");
    expect(action.openUrl).toContain("news.ycombinator.com/submitlink");
    expect(decodeURIComponent(action.openUrl!)).toContain(
      "utm_source=hackernews",
    );
    // Title is share copy only — URL must not be duplicated into t=
    const titleParam = new URL(action.openUrl!).searchParams.get("t");
    expect(titleParam).toBe("Ship this thing");
    expect(titleParam).not.toContain("http");
  });

  it("degrades HN to COPY when not live", () => {
    const action = buildSharePostAction({
      ...base,
      surface: "hackernews_show",
      isLive: false,
      slug: null,
    });
    expect(action.mode).toBe("copy_only");
    expect(action.buttonLabel).toBe("COPY");
    expect(action.openUrl).toBeNull();
    expect(action.toastMessage).toMatch(/HN/i);
  });

  it("treats LinkedIn as copy-open to the feed (no unofficial text prefill)", () => {
    const action = buildSharePostAction({
      ...base,
      surface: "linkedin_post",
    });
    expect(action.mode).toBe("copy_open");
    expect(action.buttonLabel).toBe("COPY & OPEN LINKEDIN");
    expect(action.openUrl).toBe("https://www.linkedin.com/feed/");
    expect(action.toastMessage).toBe(
      "Copied — paste it into your LinkedIn post",
    );
    expect(action.openUrl).not.toContain("shareActive");
  });

  it("treats DM opener as copy-only with no open target", () => {
    const action = buildSharePostAction({
      ...base,
      surface: "dm_opener",
    });
    expect(action.mode).toBe("copy_only");
    expect(action.buttonLabel).toBe("COPY");
    expect(action.openUrl).toBeNull();
    expect(action.toastMessage).toBe("Copied — send it as a DM");
  });
});
