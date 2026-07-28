"use client";

import { useEffect, useState } from "react";
import { BarChart3, Brain, Lightbulb, Loader2, Sparkles, TrendingUp } from "lucide-react";
import { getInsightReport } from "@/lib/api";
import {
  confidenceBadgeClass,
  recommendationBadgeClass,
} from "@/lib/report-badges";
import type {
  InsightRecommendationType,
  InsightReport,
  ResearchTakeaway,
  TakeawaySourceType,
} from "@/lib/types";

/**
 * Signal verdict insight report — owns GET /insight-report.
 * Frontend `InsightReport` omits backend `schema_version`; extras are ignored.
 */

function formatRecommendation(type: InsightRecommendationType): string {
  return type.charAt(0).toUpperCase() + type.slice(1);
}

function sourceTypeLabel(type: TakeawaySourceType): string {
  switch (type) {
    case "BEHAVIORAL":
      return "Behavioral";
    case "COGNITIVE":
      return "Research";
    case "SYNTHESIZED":
      return "Combined";
  }
}

function TakeawayCard({ takeaway }: { takeaway: ResearchTakeaway }) {
  return (
    <div className="border-2 border-border-master bg-surface-card p-4 shadow-brutal-sm">
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <span className="border-2 border-border-master bg-surface-elevated px-2 py-0.5 font-label-md text-label-sm uppercase tracking-wider text-ink-secondary">
          {sourceTypeLabel(takeaway.source_type)}
        </span>
        <span
          className={`border-2 px-2 py-0.5 font-label-md text-label-sm uppercase tracking-wider ${confidenceBadgeClass(takeaway.confidence)}`}
        >
          {takeaway.confidence === "low"
            ? "LOW CONFIDENCE"
            : `${takeaway.confidence} confidence`}
        </span>
      </div>
      <p className="text-body-md leading-relaxed text-ink-primary">
        {takeaway.claim}
      </p>
    </div>
  );
}

type Props = {
  experimentId: string;
};

export function SignalInsightReport({ experimentId }: Props) {
  const [report, setReport] = useState<InsightReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const data = await getInsightReport(experimentId);
        if (!cancelled) setReport(data);
      } catch {
        if (!cancelled) setError("Could not load the insight report.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, [experimentId]);

  if (loading) {
    return (
      <div
        className="flex flex-col items-center justify-center gap-3 border-2 border-border-master bg-surface-card py-16 shadow-brutal-sm"
        aria-busy="true"
      >
        <Loader2 className="h-6 w-6 animate-spin text-ink-primary" />
        <p className="font-mono text-mono-sm uppercase text-ink-tertiary">
          Loading insight report…
        </p>
      </div>
    );
  }

  if (error || !report) {
    return (
      <div
        role="alert"
        className="border-2 border-border-master bg-surface-card p-4 shadow-brutal-sm"
      >
        <p className="text-body-md text-status-critical">
          {error ?? "Insight report not available."}
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* 1. AI recommendation */}
      <section className="border-2 border-border-master bg-surface-card p-5 shadow-brutal-md">
        <div className="flex items-start gap-4">
          <div className="flex h-12 w-12 shrink-0 items-center justify-center border-2 border-border-master bg-brutalist-yellow shadow-brutal-sm">
            <Sparkles className="h-6 w-6 text-ink-primary" aria-hidden />
          </div>
          <div className="min-w-0 flex-1">
            <p className="mb-2 font-label-md text-label-sm uppercase tracking-wider text-ink-tertiary">
              AI recommendation
            </p>
            <span
              className={`inline-flex border-2 px-3 py-1 font-label-md text-label-sm uppercase tracking-wider ${recommendationBadgeClass(report.recommendation_type)}`}
            >
              {formatRecommendation(report.recommendation_type)}
            </span>
            <p className="mt-4 text-body-md text-ink-primary">
              {report.recommendation}
            </p>
            {report.recommendation_rationale ? (
              <p className="mt-3 text-body-sm leading-relaxed text-ink-secondary">
                {report.recommendation_rationale}
              </p>
            ) : null}
          </div>
        </div>
      </section>

      {/* 2. Traffic summary */}
      {report.traffic_summary ? (
        <section className="border-2 border-border-master bg-surface-card p-5 shadow-brutal-md">
          <div className="mb-4 flex items-center gap-2">
            <BarChart3 className="h-5 w-5 text-ink-primary" aria-hidden />
            <h2 className="font-headline text-headline-md uppercase tracking-tighter text-ink-primary">
              Traffic summary
            </h2>
          </div>
          <p className="font-headline text-headline-lg tracking-tight text-ink-primary">
            {report.traffic_summary.headline_metric}
          </p>
          <p className="mt-3 whitespace-pre-wrap text-body-md text-ink-secondary">
            {report.traffic_summary.narrative}
          </p>
        </section>
      ) : null}

      {/* 3. Key takeaways */}
      <section>
        <div className="mb-4 flex items-center gap-2">
          <Lightbulb className="h-5 w-5 text-ink-primary" aria-hidden />
          <h2 className="font-headline text-headline-md uppercase tracking-tighter text-ink-primary">
            Key takeaways
          </h2>
        </div>
        <div className="space-y-3">
          {report.research_takeaways.map((takeaway) => (
            <TakeawayCard
              key={`${takeaway.source_type}-${takeaway.claim.slice(0, 48)}`}
              takeaway={takeaway}
            />
          ))}
        </div>
      </section>

      {/* 4. Conversion by source */}
      {report.conversion_by_source?.per_source?.length > 0 ? (
        <section className="border-2 border-border-master bg-surface-card p-5 shadow-brutal-md">
          <div className="mb-4 flex items-center gap-2">
            <TrendingUp className="h-5 w-5 text-ink-primary" aria-hidden />
            <h2 className="font-headline text-headline-md uppercase tracking-tighter text-ink-primary">
              Conversion by source
            </h2>
          </div>
          <p className="text-body-md text-ink-secondary">
            {report.conversion_by_source.warm_network_bias_commentary}
          </p>
          <div className="mt-4 grid gap-3 sm:grid-cols-2">
            {report.conversion_by_source.per_source.map((src) => (
              <div
                key={src.source_name}
                className="border-2 border-border-master bg-surface-elevated p-4 shadow-brutal-sm"
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="font-label-md text-label-md uppercase tracking-wider text-ink-primary">
                    {src.source_name}
                  </span>
                  <span className="font-mono text-mono-sm text-ink-primary">
                    {(src.conversion_rate * 100).toFixed(1)}%
                  </span>
                </div>
                <p className="mt-1 font-mono text-mono-sm text-ink-tertiary">
                  {src.views} views · {src.signups} signups
                </p>
                <p className="mt-2 text-body-sm leading-relaxed text-ink-secondary">
                  {src.commentary}
                </p>
              </div>
            ))}
          </div>
        </section>
      ) : null}

      {/* 5. What would change this? */}
      <section className="border-2 border-border-master bg-surface-elevated p-5 shadow-brutal-sm">
        <div className="flex items-start gap-3">
          <Brain className="mt-0.5 h-5 w-5 shrink-0 text-ink-primary" aria-hidden />
          <div>
            <h2 className="font-label-md text-label-md uppercase tracking-wider text-ink-primary">
              What would change this?
            </h2>
            <p className="mt-2 whitespace-pre-wrap text-body-md text-ink-secondary">
              {report.what_would_change_this}
            </p>
          </div>
        </div>
      </section>
    </div>
  );
}
