"use client";

import { useEffect, useState } from "react";
import {
  BarChart3,
  Brain,
  Lightbulb,
  Loader2,
  Sparkles,
  TrendingUp,
} from "lucide-react";
import { getInsightReport, ApiError } from "@/lib/api";
import type {
  InsightRecommendationType,
  InsightReport,
  ResearchTakeaway,
  TakeawaySourceType,
} from "@/lib/types";
import { ErrorBanner } from "@/components/ui/ErrorBanner";
import { LoadingState } from "@/components/ui/LoadingState";

function recommendationBadgeClass(type: InsightRecommendationType): string {
  switch (type) {
    case "proceed":
      return "badge-proceed";
    case "iterate":
      return "badge-iterate";
    case "pivot":
      return "badge-pivot";
    case "kill":
      return "badge-kill";
  }
}

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

function sourceTypeClass(type: TakeawaySourceType): string {
  switch (type) {
    case "BEHAVIORAL":
      return "bg-purple-500/15 text-purple-300 ring-purple-500/30";
    case "COGNITIVE":
      return "bg-[var(--fv-accent-muted)] text-[var(--fv-accent)] ring-[color-mix(in_srgb,var(--fv-accent)_30%,transparent)]";
    case "SYNTHESIZED":
      return "bg-indigo-500/15 text-indigo-300 ring-indigo-500/30";
  }
}

function TakeawayCard({ takeaway }: { takeaway: ResearchTakeaway }) {
  return (
    <div className="rounded-xl border border-[var(--fv-border)] bg-[var(--fv-surface)] p-4">
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <span
          className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-semibold ring-1 ring-inset ${sourceTypeClass(takeaway.source_type)}`}
        >
          {sourceTypeLabel(takeaway.source_type)}
        </span>
        <span className={`fv-confidence-badge ${takeaway.confidence === "high" ? "fv-confidence-high" : takeaway.confidence === "medium" ? "fv-confidence-medium" : "fv-confidence-low"}`}>
          {takeaway.confidence} confidence
        </span>
      </div>
      <p className="text-sm leading-relaxed text-[var(--fv-text)]">
        {takeaway.claim}
      </p>
    </div>
  );
}

interface InsightReportViewerProps {
  experimentId: string;
}

export function InsightReportViewer({ experimentId }: InsightReportViewerProps) {
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
    load();
    return () => {
      cancelled = true;
    };
  }, [experimentId]);

  if (loading) {
    return <LoadingState label="Loading insight report…" />;
  }

  if (error || !report) {
    return <ErrorBanner message={error ?? "Insight report not available."} />;
  }

  return (
    <div className="space-y-6">
      <div className="fv-section-card border-[color-mix(in_srgb,var(--fv-accent)_25%,transparent)] bg-gradient-to-br from-[color-mix(in_srgb,var(--fv-accent)_8%,transparent)] to-transparent">
        <div className="flex items-start gap-4">
          <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-[var(--fv-accent-muted)]">
            <Sparkles className="h-6 w-6 text-[var(--fv-accent)]" />
          </div>
          <div className="min-w-0 flex-1">
            <p className="fv-panel-label mb-2">AI recommendation</p>
            <span
              className={`inline-flex rounded-lg px-3 py-1 text-sm font-bold uppercase tracking-wide ${recommendationBadgeClass(report.recommendation_type)}`}
            >
              {formatRecommendation(report.recommendation_type)}
            </span>
            <p className="fv-prose mt-4 text-sm">{report.recommendation}</p>
            {report.recommendation_rationale && (
              <p className="mt-3 text-xs leading-relaxed text-[var(--fv-text-muted)]">
                {report.recommendation_rationale}
              </p>
            )}
          </div>
        </div>
      </div>

      {report.traffic_summary && (
        <div className="fv-section-card">
          <div className="mb-4 flex items-center gap-2">
            <BarChart3 className="h-5 w-5 text-[var(--fv-accent)]" />
            <h2 className="text-lg font-semibold text-[var(--fv-text)]">
              Traffic summary
            </h2>
          </div>
          <p className="text-2xl font-bold tracking-tight text-[var(--fv-text)]">
            {report.traffic_summary.headline_metric}
          </p>
          <p className="fv-prose mt-3 text-sm whitespace-pre-wrap">
            {report.traffic_summary.narrative}
          </p>
        </div>
      )}

      <div>
        <div className="mb-4 flex items-center gap-2">
          <Lightbulb className="h-5 w-5 text-[var(--fv-accent)]" />
          <h2 className="text-lg font-semibold text-[var(--fv-text)]">
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
      </div>

      {report.conversion_by_source?.per_source?.length > 0 && (
        <div className="fv-section-card">
          <div className="mb-4 flex items-center gap-2">
            <TrendingUp className="h-5 w-5 text-[var(--fv-accent)]" />
            <h2 className="text-lg font-semibold text-[var(--fv-text)]">
              Conversion by source
            </h2>
          </div>
          <p className="text-sm text-[var(--fv-text-muted)]">
            {report.conversion_by_source.warm_network_bias_commentary}
          </p>
          <div className="mt-4 grid gap-3 sm:grid-cols-2">
            {report.conversion_by_source.per_source.map((src) => (
              <div
                key={src.source_name}
                className="rounded-xl border border-[var(--fv-border)] bg-[var(--fv-surface)] p-4"
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="font-medium text-[var(--fv-text)]">
                    {src.source_name}
                  </span>
                  <span className="font-mono text-sm font-semibold text-[var(--fv-accent)]">
                    {(src.conversion_rate * 100).toFixed(1)}%
                  </span>
                </div>
                <p className="mt-1 text-xs text-[var(--fv-text-muted)]">
                  {src.views} views · {src.signups} signups
                </p>
                <p className="mt-2 text-sm leading-relaxed text-[var(--fv-text-soft)]">
                  {src.commentary}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="rounded-xl border border-[color-mix(in_srgb,var(--fv-warning)_25%,transparent)] bg-[color-mix(in_srgb,var(--fv-warning)_8%,transparent)] p-5">
        <div className="flex items-start gap-3">
          <Brain className="mt-0.5 h-5 w-5 shrink-0 text-[var(--fv-warning)]" />
          <div>
            <h2 className="text-sm font-semibold text-[var(--fv-warning)]">
              What would change this?
            </h2>
            <p className="fv-prose mt-2 text-sm whitespace-pre-wrap">
              {report.what_would_change_this}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
