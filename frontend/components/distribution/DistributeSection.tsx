"use client";

import { useCallback, useEffect, useState } from "react";
import { Loader2 } from "lucide-react";
import { getExperimentAnalytics, ApiError } from "@/lib/api";
import type { ExperimentAnalytics } from "@/lib/types";
import { ShareLinksPanel } from "./ShareLinksPanel";

const DISTRIBUTION_TIPS = [
  "Post in 2-3 relevant communities where your target users hang out",
  "Share with 10 people who have the problem your idea solves — not just friends",
  "Add the link to your social media bios for passive traffic",
  "Write a short post explaining the problem, not your solution — link at the end",
] as const;

function formatPercent(rate: number): string {
  return `${(rate * 100).toFixed(1)}%`;
}

interface DistributeSectionProps {
  experimentId: string;
  slug: string;
  experimentName: string;
}

export function DistributeSection({
  experimentId,
  slug,
  experimentName,
}: DistributeSectionProps) {
  const [analytics, setAnalytics] = useState<ExperimentAnalytics | null>(null);
  const [analyticsLoading, setAnalyticsLoading] = useState(true);

  const loadAnalytics = useCallback(async () => {
    try {
      const data = await getExperimentAnalytics(experimentId);
      setAnalytics(data);
    } catch (err) {
      if (!(err instanceof ApiError && err.status === 404)) {
        setAnalytics(null);
      }
    } finally {
      setAnalyticsLoading(false);
    }
  }, [experimentId]);

  useEffect(() => {
    void loadAnalytics();
    const intervalId = setInterval(loadAnalytics, 15000);
    return () => clearInterval(intervalId);
  }, [loadAnalytics]);

  return (
    <section
      id="distribute"
      className="fv-card mb-4 shrink-0 scroll-mt-6 p-4 sm:p-5"
      aria-labelledby="distribute-heading"
    >
      <div className="mb-4">
        <h2
          id="distribute-heading"
          className="text-base font-semibold text-[var(--fv-text)]"
        >
          Drive traffic to your page
        </h2>
        <p className="mt-1 text-[13px] text-[var(--fv-text-muted)]">
          Share your landing page to collect real interest signals
        </p>
      </div>

      {analyticsLoading ? (
        <div className="mb-4 flex items-center gap-2 text-[13px] text-[var(--fv-text-muted)]">
          <Loader2 className="h-3.5 w-3.5 animate-spin" />
          Loading metrics…
        </div>
      ) : analytics ? (
        <div className="mb-4 flex flex-wrap items-center gap-x-4 gap-y-1 text-[13px] text-[var(--fv-text-soft)]">
          <span>
            <span className="font-semibold text-[var(--fv-accent)]">
              {analytics.total_page_views.toLocaleString()}
            </span>
            {" views"}
          </span>
          <span className="text-[var(--fv-text-dim)]">·</span>
          <span>
            <span className="font-semibold text-[var(--fv-accent)]">
              {analytics.total_signups.toLocaleString()}
            </span>
            {" signups"}
          </span>
          <span className="text-[var(--fv-text-dim)]">·</span>
          <span>
            <span className="font-semibold text-[var(--fv-accent)]">
              {formatPercent(analytics.conversion_rate)}
            </span>
            {" conversion"}
          </span>
        </div>
      ) : null}

      <ShareLinksPanel slug={slug} experimentName={experimentName} />

      <div className="mt-5 border-t border-[var(--fv-border)] pt-4">
        <p className="mb-2 text-[12px] font-medium uppercase tracking-wide text-[var(--fv-text-muted)]">
          Quick tips
        </p>
        <ul className="space-y-2 text-[13px] text-[var(--fv-text-soft)]">
          {DISTRIBUTION_TIPS.map((tip) => (
            <li key={tip} className="flex gap-2">
              <span className="shrink-0 text-[var(--fv-accent)]" aria-hidden>
                →
              </span>
              <span>{tip}</span>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
