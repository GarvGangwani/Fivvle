"use client";

import type { InsightProgress } from "@/lib/types";

export type ThresholdTrackId = "views" | "signups" | "days";

export type ThresholdTrack = {
  id: ThresholdTrackId;
  label: string;
  current: number;
  target: number;
  /** Units remaining to complete this path (display only — not gate math). */
  remaining: number;
  /** 0–1 fill from server current/target. */
  fill: number;
  complete: boolean;
};

export function buildThresholdTracks(
  progress: InsightProgress,
): ThresholdTrack[] {
  const defs: Array<{
    id: ThresholdTrackId;
    label: string;
    current: number;
    target: number;
  }> = [
    {
      id: "views",
      label: "Page views",
      current: progress.views_current,
      target: progress.views_target,
    },
    {
      id: "signups",
      label: "Waitlist signups",
      current: progress.signups_current,
      target: progress.signups_target,
    },
    {
      id: "days",
      label: "Days live",
      current: progress.days_current,
      target: progress.days_target,
    },
  ];

  return defs.map((d) => {
    const remaining = Math.max(0, d.target - d.current);
    const fill =
      d.target <= 0 ? 0 : Math.min(1, Math.max(0, d.current / d.target));
    return {
      ...d,
      remaining,
      fill,
      complete: remaining === 0 && d.target > 0,
    };
  });
}

/** Closest incomplete path by proportion complete; if all complete, first track. */
export function pickClosestTrack(tracks: ThresholdTrack[]): ThresholdTrack {
  const incomplete = tracks.filter((t) => !t.complete);
  if (incomplete.length === 0) return tracks[0]!;
  // Tie-break: easiest path first (views → days → signups).
  const tieBreak: Record<ThresholdTrackId, number> = {
    views: 0,
    days: 1,
    signups: 2,
  };
  return [...incomplete].sort((a, b) => {
    if (a.fill !== b.fill) return b.fill - a.fill;
    return tieBreak[a.id] - tieBreak[b.id];
  })[0]!;
}

function remainingCopy(track: ThresholdTrack): string {
  if (track.complete) return "Path complete";
  if (track.id === "views") {
    return track.remaining === 1
      ? "1 more view"
      : `${track.remaining} more views`;
  }
  if (track.id === "signups") {
    return track.remaining === 1
      ? "1 more signup"
      : `${track.remaining} more signups`;
  }
  return track.remaining === 1
    ? "1 more day"
    : `${track.remaining} more days`;
}

function TrackBar({
  track,
  emphasized,
}: {
  track: ThresholdTrack;
  emphasized: boolean;
}) {
  return (
    <div className={emphasized ? "" : "opacity-70"}>
      <div className="mb-1.5 flex items-baseline justify-between gap-3">
        <p
          className={`font-label-md uppercase tracking-wider text-ink-primary ${
            emphasized ? "text-label-md" : "text-label-sm"
          }`}
        >
          {track.label}
          {track.complete ? (
            <span className="ml-2 text-ink-tertiary">· met</span>
          ) : null}
        </p>
        <p className="font-mono text-mono-sm text-ink-secondary">
          {track.current} / {track.target}
        </p>
      </div>
      <div className="h-3 border-2 border-border-master bg-surface-card">
        <div
          className={`h-full transition-all ${
            track.complete ? "bg-brutalist-yellow" : "bg-ink-primary"
          }`}
          style={{ width: `${Math.round(track.fill * 100)}%` }}
          role="progressbar"
          aria-valuenow={track.current}
          aria-valuemin={0}
          aria-valuemax={track.target}
          aria-label={`${track.label}: ${track.current} of ${track.target}`}
        />
      </div>
      {!track.complete && emphasized ? (
        <p className="mt-1.5 font-mono text-mono-sm uppercase text-ink-tertiary">
          {remainingCopy(track)} to unlock on this path
        </p>
      ) : null}
    </div>
  );
}

type Props = {
  progress: InsightProgress;
};

/**
 * Distance-to-threshold hero. Expresses OR: any one track unlocks a verdict.
 * Closest incomplete path is visually primary; others are demoted alternatives.
 */
export function ThresholdDistanceHero({ progress }: Props) {
  const tracks = buildThresholdTracks(progress);
  const closest = pickClosestTrack(tracks);
  const others = tracks.filter((t) => t.id !== closest.id);
  const allComplete = tracks.every((t) => t.complete);

  return (
    <section
      className="border-2 border-border-master bg-surface-card p-6 shadow-brutal-md"
      aria-labelledby="threshold-hero-heading"
    >
      <div className="mb-3 inline-block border-2 border-border-master bg-brutalist-yellow px-3 py-1 font-label-md text-label-sm uppercase tracking-wider text-ink-primary shadow-brutal-sm">
        Watching
      </div>

      <h2
        id="threshold-hero-heading"
        className="font-headline text-headline-md uppercase tracking-tighter text-ink-primary"
      >
        Distance to a verdict
      </h2>

      <p className="mt-2 text-body-md text-ink-secondary">
        Any <span className="font-label-md text-label-sm uppercase text-ink-primary">one</span>{" "}
        path unlocks a verdict — whichever comes first. Not all three.
      </p>

      {!allComplete ? (
        <p className="mt-4 border-2 border-border-master bg-surface-elevated px-3 py-2 font-label-md text-label-md uppercase tracking-wider text-ink-primary shadow-brutal-sm">
          Closest: {remainingCopy(closest)}
        </p>
      ) : (
        <p className="mt-4 border-2 border-border-master bg-brutalist-yellow px-3 py-2 font-label-md text-label-md uppercase tracking-wider text-ink-primary shadow-brutal-sm">
          Threshold crossed on every path
        </p>
      )}

      <div className="mt-6 space-y-5">
        <TrackBar track={closest} emphasized />
        {others.length > 0 ? (
          <div className="space-y-4 border-t-2 border-border-master pt-5">
            <p className="font-mono text-mono-sm uppercase text-ink-tertiary">
              Other paths (also enough alone)
            </p>
            {others.map((track) => (
              <TrackBar key={track.id} track={track} emphasized={false} />
            ))}
          </div>
        ) : null}
      </div>
    </section>
  );
}
