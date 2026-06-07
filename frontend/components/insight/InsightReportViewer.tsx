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
      return "bg-green-100 text-green-900 ring-green-300";
    case "iterate":
      return "bg-blue-100 text-blue-900 ring-blue-300";
    case "pivot":
      return "bg-yellow-100 text-yellow-900 ring-yellow-300";
    case "kill":
      return "bg-red-100 text-red-900 ring-red-300";
  }
}

function formatRecommendation(type: InsightRecommendationType): string {
  return type.charAt(0).toUpperCase() + type.slice(1);
}

function sourceTypeBadgeClass(type: TakeawaySourceType): string {
  switch (type) {
    case "BEHAVIORAL":
      return "bg-purple-100 text-purple-800 ring-purple-200";
    case "COGNITIVE":
      return "bg-sky-100 text-sky-800 ring-sky-200";
    case "SYNTHESIZED":
      return "bg-indigo-100 text-indigo-800 ring-indigo-200";
  }
}

function TakeawayCard({ takeaway }: { takeaway: ResearchTakeaway }) {
  return (
    <div className="rounded-lg border border-gray-100 bg-gray-50 p-4">
      <div className="mb-2 flex flex-wrap items-center gap-2">
        <span
          className={`inline-flex rounded-full px-2 py-0.5 text-xs font-semibold ring-1 ring-inset ${sourceTypeBadgeClass(takeaway.source_type)}`}
        >
          {takeaway.source_type}
        </span>
        <span className="text-xs text-gray-400">
          {takeaway.confidence} confidence
        </span>
      </div>
      <p className="text-sm leading-relaxed text-gray-900 whitespace-pre-wrap">
        {takeaway.claim}
      </p>
      {takeaway.cited_finding_ids.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-1.5">
          {takeaway.cited_finding_ids.map((id) => (
            <span
              key={id}
              className="rounded-md bg-white px-2 py-0.5 text-xs font-mono text-gray-500 ring-1 ring-gray-200"
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
        <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
      </div>
    );
  }

  if (error || !report) {
    return (
      <div className="rounded-xl border border-red-200 bg-red-50 px-6 py-8 text-center">
        <p className="text-sm text-red-700">
          {error ?? "Insight report not available."}
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <section className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm text-center sm:text-left">
        <p className="text-sm font-medium uppercase tracking-wide text-gray-500">
          AI recommendation
        </p>
        <span
          className={`mt-4 inline-flex rounded-full px-5 py-2 text-lg font-bold ring-2 ring-inset ${recommendationBadgeClass(report.recommendation_type)}`}
        >
          {formatRecommendation(report.recommendation_type)}
        </span>
        <p className="mt-4 text-sm leading-relaxed text-gray-700 whitespace-pre-wrap">
          {report.recommendation}
        </p>
        <p className="mt-3 text-xs text-gray-400 whitespace-pre-wrap">
          {report.recommendation_rationale}
        </p>
      </section>

      {report.traffic_summary && (
        <section className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-gray-900">
            Traffic summary
          </h2>
          <p className="mt-1 text-sm font-medium text-gray-600">
            {report.traffic_summary.headline_metric}
          </p>
          <p className="mt-3 text-sm leading-relaxed text-gray-700 whitespace-pre-wrap">
            {report.traffic_summary.narrative}
          </p>
        </section>
      )}

      <section className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
        <h2 className="text-lg font-semibold text-gray-900">
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
        <section className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-gray-900">
            Conversion by source
          </h2>
          <p className="mt-2 text-sm text-gray-600 whitespace-pre-wrap">
            {report.conversion_by_source.warm_network_bias_commentary}
          </p>
          <ul className="mt-4 space-y-3">
            {report.conversion_by_source.per_source.map((src) => (
              <li
                key={src.source_name}
                className="rounded-lg border border-gray-100 bg-gray-50 p-4"
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="font-medium text-gray-900">
                    {src.source_name}
                  </span>
                  <span className="text-xs text-gray-500">
                    {src.views} views · {src.signups} signups ·{" "}
                    {(src.conversion_rate * 100).toFixed(1)}%
                  </span>
                </div>
                <p className="mt-2 text-sm text-gray-600 whitespace-pre-wrap">
                  {src.commentary}
                </p>
              </li>
            ))}
          </ul>
        </section>
      )}

      <section className="rounded-xl border border-amber-200 bg-amber-50 p-6">
        <h2 className="text-sm font-semibold text-amber-900">
          What would change this?
        </h2>
        <p className="mt-2 text-sm leading-relaxed text-amber-800 whitespace-pre-wrap">
          {report.what_would_change_this}
        </p>
      </section>
    </div>
  );
}
