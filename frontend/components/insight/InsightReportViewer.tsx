"use client";

import { useEffect, useState } from "react";
import { Loader2 } from "lucide-react";
import { getInsightReport, ApiError } from "@/lib/api";
import type {
  InsightRecommendationType,
  InsightReport,
  ResearchTakeaway,
  TakeawaySourceType,
} from "@/lib/types";

function recommendationBadgeClass(
  type: InsightRecommendationType,
): string {
  switch (type) {
    case "proceed":
      return "bg-[rgba(16,185,129,0.15)] text-[var(--fv-success)] ring-[rgba(16,185,129,0.3)]";
    case "iterate":
      return "bg-[var(--fv-accent-muted)] text-[var(--fv-accent)] ring-[rgba(6,182,212,0.3)]";
    case "pivot":
      return "bg-[rgba(245,158,11,0.15)] text-[var(--fv-warning)] ring-[rgba(245,158,11,0.3)]";
    case "kill":
      return "bg-[rgba(239,68,68,0.15)] text-red-300 ring-[rgba(239,68,68,0.3)]";
  }
}

function formatRecommendation(type: InsightRecommendationType): string {
  return type.charAt(0).toUpperCase() + type.slice(1);
}

function sourceTypeBadgeClass(type: TakeawaySourceType): string {
  switch (type) {
    case "BEHAVIORAL":
      return "bg-[rgba(168,85,247,0.15)] text-purple-300 ring-[rgba(168,85,247,0.3)]";
    case "COGNITIVE":
      return "bg-[var(--fv-accent-muted)] text-[var(--fv-accent)] ring-[rgba(6,182,212,0.3)]";
    case "SYNTHESIZED":
      return "bg-[rgba(99,102,241,0.15)] text-indigo-300 ring-[rgba(99,102,241,0.3)]";
  }
}

function TakeawayCard({ takeaway }: { takeaway: ResearchTakeaway }) {
  return (
    <div className="fv-card p-4">
      <div className="mb-2 flex flex-wrap items-center gap-2">
        <span
          className={`inline-flex rounded-full px-2 py-0.5 text-xs font-semibold ring-1 ring-inset ${sourceTypeBadgeClass(takeaway.source_type)}`}
        >
          {takeaway.source_type}
        </span>
        <span className="text-xs text-[var(--fv-text-muted)]">
          {takeaway.confidence} confidence
        </span>
      </div>
      <p className="whitespace-pre-wrap text-sm leading-relaxed text-[var(--fv-text)]">
        {takeaway.claim}
      </p>
      {takeaway.cited_finding_ids.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-1.5">
          {takeaway.cited_finding_ids.map((id) => (
            <span
              key={id}
              className="rounded-md bg-white/5 px-2 py-0.5 font-mono text-xs text-[var(--fv-text-muted)] ring-1 ring-[var(--fv-border)]"
            >
              {id}
            </span>
          ))}
        </div>
      )}
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
      } catch (err) {
        if (cancelled) return;
        setError(
          err instanceof ApiError
            ? "Could not load the insight report."
            : "Could not load the insight report.",
        );
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
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="h-6 w-6 animate-spin text-[var(--fv-accent)]" />
      </div>
    );
  }

  if (error || !report) {
    return (
      <div className="fv-error px-6 py-8 text-center">
        <p className="text-sm">
          {error ?? "Insight report not available."}
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <section className="fv-card p-6 text-center sm:text-left">
        <p className="text-sm font-medium uppercase tracking-wide text-[var(--fv-text-muted)]">
          AI recommendation
        </p>
        <span
          className={`mt-4 inline-flex rounded-full px-5 py-2 text-lg font-bold ring-2 ring-inset ${recommendationBadgeClass(report.recommendation_type)}`}
        >
          {formatRecommendation(report.recommendation_type)}
        </span>
        <p className="mt-4 whitespace-pre-wrap text-sm leading-relaxed text-[var(--fv-text-soft)]">
          {report.recommendation}
        </p>
        <p className="mt-3 whitespace-pre-wrap text-xs text-[var(--fv-text-muted)]">
          {report.recommendation_rationale}
        </p>
      </section>

      {report.traffic_summary && (
        <section className="fv-card p-6">
          <h2 className="text-lg font-semibold text-[var(--fv-text)]">
            Traffic summary
          </h2>
          <p className="mt-1 text-sm font-medium text-[var(--fv-text-soft)]">
            {report.traffic_summary.headline_metric}
          </p>
          <p className="mt-3 whitespace-pre-wrap text-sm leading-relaxed text-[var(--fv-text-soft)]">
            {report.traffic_summary.narrative}
          </p>
        </section>
      )}

      <section className="fv-card p-6">
        <h2 className="text-lg font-semibold text-[var(--fv-text)]">
          Research takeaways
        </h2>
        <div className="mt-4 space-y-3">
          {report.research_takeaways.map((takeaway) => (
            <TakeawayCard
              key={`${takeaway.source_type}-${takeaway.claim.slice(0, 40)}`}
              takeaway={takeaway}
            />
          ))}
        </div>
      </section>

      {report.conversion_by_source?.per_source?.length > 0 && (
        <section className="fv-card p-6">
          <h2 className="text-lg font-semibold text-[var(--fv-text)]">
            Conversion by source
          </h2>
          <p className="mt-2 whitespace-pre-wrap text-sm text-[var(--fv-text-soft)]">
            {report.conversion_by_source.warm_network_bias_commentary}
          </p>
          <ul className="mt-4 space-y-3">
            {report.conversion_by_source.per_source.map((src) => (
              <li
                key={src.source_name}
                className="fv-card p-4"
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="font-medium text-[var(--fv-text)]">
                    {src.source_name}
                  </span>
                  <span className="text-xs text-[var(--fv-text-muted)]">
                    {src.views} views · {src.signups} signups ·{" "}
                    {(src.conversion_rate * 100).toFixed(1)}%
                  </span>
                </div>
                <p className="mt-2 whitespace-pre-wrap text-sm text-[var(--fv-text-soft)]">
                  {src.commentary}
                </p>
              </li>
            ))}
          </ul>
        </section>
      )}

      <section className="fv-card border-[rgba(245,158,11,0.3)] bg-[rgba(245,158,11,0.08)] p-6">
        <h2 className="text-sm font-semibold text-[var(--fv-warning)]">
          What would change this?
        </h2>
        <p className="mt-2 whitespace-pre-wrap text-sm leading-relaxed text-[var(--fv-text-soft)]">
          {report.what_would_change_this}
        </p>
      </section>
    </div>
  );
}
