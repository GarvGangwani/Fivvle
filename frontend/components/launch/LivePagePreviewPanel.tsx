"use client";

import { useState } from "react";
import {
  buildInAppPreviewUrl,
  buildPublicLandingPageUrl,
} from "@/lib/landing-host";

type Viewport = "mobile" | "desktop";

/**
 * - generate:   RESEARCH_READY, no landing page yet → offer to build one.
 * - generating: LANDING_GENERATING → building state, parent polls for the flip.
 * - draft:      LANDING_DRAFT (built, not live) → no live URL to iframe; the real
 *               draft preview arrives in PR 3 via the design-edit toggle (D6 / Option A).
 * - live:       LANDING_LIVE+ → iframe same-origin /e/{slug}; URL bar shows public URL.
 */
export type PreviewState = "generate" | "generating" | "draft" | "live";

type Props = {
  previewState: PreviewState;
  slug: string | null;
  /** Bumps on Copy/Design PATCH success so the iframe reloads past cache. */
  cacheBust?: number;
  onGenerateLandingPage: () => void;
};

const DOT_GRID_STYLE: React.CSSProperties = {
  backgroundColor: "var(--fv-canvas-bg)",
  backgroundImage: "radial-gradient(circle, #000 1px, transparent 1px)",
  backgroundSize: "40px 40px",
};

export function LivePagePreviewPanel({
  previewState,
  slug,
  cacheBust = 0,
  onGenerateLandingPage,
}: Props) {
  const [viewport, setViewport] = useState<Viewport>("desktop");

  const publicUrl =
    previewState === "live" && slug ? buildPublicLandingPageUrl(slug) : null;
  const previewUrl =
    previewState === "live" && slug
      ? `${buildInAppPreviewUrl(slug)}?v=${cacheBust}`
      : null;

  // URL bar never shows a fake/live URL for a non-live page (Edit 1, rule 4).
  // Always the shareable public subdomain URL — not the in-app iframe path.
  const urlBarLabel =
    previewState === "live" && publicUrl
      ? publicUrl
      : previewState === "draft"
        ? `${slug ?? "draft"}.preview`
        : "not yet published";

  const showToolbar = previewState === "draft" || previewState === "live";

  return (
    <div className="flex h-full min-h-0 flex-col">
      {showToolbar ? (
        <div className="flex h-10 shrink-0 items-center gap-4 border-b-2 border-border-master bg-surface-card px-4">
          <div className="flex shrink-0 items-center gap-2">
            <span className="h-3 w-3 rounded-full border border-black bg-red-400" />
            <span className="h-3 w-3 rounded-full border border-black bg-yellow-400" />
            <span className="h-3 w-3 rounded-full border border-black bg-green-400" />
          </div>

          <div className="flex min-w-0 flex-1 items-center gap-2 border border-border-master bg-surface-elevated px-3 py-1">
            <span
              className="material-symbols-outlined shrink-0 text-ink-tertiary"
              style={{ fontSize: 12 }}
              aria-hidden="true"
            >
              lock
            </span>
            <span className="truncate font-mono text-[11px] text-ink-primary/70">
              {urlBarLabel}
            </span>
          </div>

          <div className="flex shrink-0 items-center gap-3">
            <button
              type="button"
              onClick={() => setViewport("mobile")}
              aria-label="Mobile preview"
              aria-pressed={viewport === "mobile"}
              disabled={previewState !== "live"}
              className={`material-symbols-outlined text-ink-primary transition-opacity disabled:cursor-not-allowed ${
                viewport === "mobile" ? "opacity-100" : "opacity-50"
              }`}
            >
              smartphone
            </button>
            <button
              type="button"
              onClick={() => setViewport("desktop")}
              aria-label="Desktop preview"
              aria-pressed={viewport === "desktop"}
              disabled={previewState !== "live"}
              className={`material-symbols-outlined text-ink-primary transition-opacity disabled:cursor-not-allowed ${
                viewport === "desktop" ? "opacity-100" : "opacity-50"
              }`}
            >
              desktop_windows
            </button>
          </div>
        </div>
      ) : null}

      <div
        className="flex min-h-0 flex-1 items-center justify-center overflow-y-auto p-12"
        style={DOT_GRID_STYLE}
      >
        {previewState === "live" && previewUrl ? (
          <div
            className={
              viewport === "mobile" ? "mx-auto w-[375px]" : "mx-auto w-full"
            }
          >
            <iframe
              src={previewUrl}
              title="Landing page preview"
              className="block border-2 border-border-master bg-surface-card shadow-brutal-xl"
              style={{
                width: viewport === "mobile" ? 375 : "100%",
                height: viewport === "mobile" ? 667 : 800,
              }}
            />
          </div>
        ) : previewState === "generating" ? (
          <PreviewCard
            icon="rocket_launch"
            title="Building your page"
            subtext="This usually takes 40-60 seconds"
          >
            <div className="mt-2 h-3 w-48 border-2 border-border-master bg-surface-card">
              <div className="h-full w-1/3 animate-pulse bg-ink-primary" />
            </div>
          </PreviewCard>
        ) : previewState === "draft" ? (
          <PreviewCard
            icon="rocket_launch"
            title="Your page is built"
            subtext="Publish it to preview the live page here"
          />
        ) : (
          <PreviewCard
            icon="draft"
            title="Your landing page hasn't been built yet"
            subtext="Generate a page from your validated idea"
          >
            <button
              type="button"
              onClick={onGenerateLandingPage}
              className="mt-2 border-2 border-border-master bg-ink-primary px-4 py-2 font-label-md text-label-md uppercase tracking-wider text-ink-inverse shadow-brutal-md transition-all hover:-translate-y-0.5"
            >
              Generate landing page
            </button>
          </PreviewCard>
        )}
      </div>
    </div>
  );
}

function PreviewCard({
  icon,
  title,
  subtext,
  children,
}: {
  icon: string;
  title: string;
  subtext: string;
  children?: React.ReactNode;
}) {
  return (
    <div className="mx-auto flex max-w-md flex-col items-center gap-3 border-2 border-border-master bg-surface-card p-10 text-center shadow-brutal-md">
      <span
        className="material-symbols-outlined text-ink-tertiary"
        style={{ fontSize: 40 }}
        aria-hidden="true"
      >
        {icon}
      </span>
      <p className="font-headline text-headline-md uppercase tracking-tighter text-ink-primary">
        {title}
      </p>
      <p className="font-mono text-mono-sm uppercase text-ink-primary/60">
        {subtext}
      </p>
      {children}
    </div>
  );
}
