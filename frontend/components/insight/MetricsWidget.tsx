"use client";

import { useCallback, useEffect, useState } from "react";
import {
  BarChart3,
  Loader2,
  MousePointerClick,
  Sparkles,
  Users,
} from "lucide-react";
import {
  generateInsight,
  getExperimentAnalytics,
  ApiError,
} from "@/lib/api";
import type { ExperimentAnalytics } from "@/lib/types";

const POLL_INTERVAL_MS = 15000;

function meetsInsightThreshold(analytics: ExperimentAnalytics): boolean {
  return analytics.total_page_views >= 10 || analytics.total_signups >= 1;
}

function formatPercent(rate: number): string {
  return `${(rate * 100).toFixed(1)}%`;
}

interface MetricsWidgetProps {
  experimentId: string;
  onInsightStarted?: () => void;
}

export function MetricsWidget({
  experimentId,
  onInsightStarted,
}: MetricsWidgetProps) {
  const [analytics, setAnalytics] = useState<ExperimentAnalytics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [generating, setGenerating] = useState(false);

  const loadAnalytics = useCallback(async () => {
    try {
      const data = await getExperimentAnalytics(experimentId);
      setAnalytics(data);
      setError(null);
    } catch (err) {
      if (!(err instanceof ApiError && err.status === 404)) {
        setError("Could not load metrics.");
      }
    } finally {
      setLoading(false);
    }
  }, [experimentId]);

  useEffect(() => {
    loadAnalytics();
    const intervalId = setInterval(loadAnalytics, POLL_INTERVAL_MS);
    return () => clearInterval(intervalId);
  }, [loadAnalytics]);

  async function handleGenerateInsight() {
    if (!analytics || !meetsInsightThreshold(analytics)) return;
    setGenerating(true);
    setError(null);
    try {
      await generateInsight(experimentId);
      onInsightStarted?.();
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        setError(
          "Not enough data yet. You need at least 10 page views or 1 signup.",
        );
      } else {
        setError("Could not start insight generation. Please try again.");
      }
    } finally {
      setGenerating(false);
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center rounded-xl border border-gray-200 bg-white py-12">
        <Loader2 className="h-5 w-5 animate-spin text-gray-400" />
      </div>
    );
  }

  if (!analytics) {
    return (
      <div className="rounded-xl border border-gray-200 bg-white px-6 py-8 text-center">
        <p className="text-sm text-gray-500">
          {error ?? "Metrics will appear once your landing page is live."}
        </p>
      </div>
    );
  }

  const thresholdMet = meetsInsightThreshold(analytics);
  const sources = Object.keys(analytics.views_by_source).sort(
    (a, b) => (analytics.views_by_source[b] ?? 0) - (analytics.views_by_source[a] ?? 0),
  );

  return (
    <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
      <div className="mb-6 flex items-start justify-between gap-4">
        <div>
          <h2 className="flex items-center gap-2 text-lg font-semibold text-gray-900">
            <BarChart3 className="h-5 w-5 text-gray-500" />
            Live metrics
          </h2>
          <p className="mt-1 text-sm text-gray-500">
            {analytics.days_live === 0
              ? "Published today"
              : `${analytics.days_live} day${analytics.days_live === 1 ? "" : "s"} live`}
            {" · "}
            Share your link to gather behavioral signal.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
        <div className="rounded-lg border border-gray-100 bg-gray-50 p-4">
          <div className="flex items-center gap-1.5 text-xs font-medium uppercase tracking-wide text-gray-500">
            <MousePointerClick className="h-3.5 w-3.5" />
            Page views
          </div>
          <p className="mt-2 text-2xl font-bold text-gray-900">
            {analytics.total_page_views.toLocaleString()}
          </p>
        </div>
        <div className="rounded-lg border border-gray-100 bg-gray-50 p-4">
          <div className="flex items-center gap-1.5 text-xs font-medium uppercase tracking-wide text-gray-500">
            <Users className="h-3.5 w-3.5" />
            Signups
          </div>
          <p className="mt-2 text-2xl font-bold text-gray-900">
            {analytics.total_signups.toLocaleString()}
          </p>
        </div>
        <div className="col-span-2 rounded-lg border border-gray-100 bg-gray-50 p-4 sm:col-span-1">
          <p className="text-xs font-medium uppercase tracking-wide text-gray-500">
            Conversion rate
          </p>
          <p className="mt-2 text-2xl font-bold text-gray-900">
            {formatPercent(analytics.conversion_rate)}
          </p>
        </div>
      </div>

      {sources.length > 0 && (
        <div className="mt-6">
          <h3 className="mb-3 text-sm font-semibold text-gray-900">
            Source breakdown
          </h3>
          <div className="space-y-2">
            {sources.map((source) => {
              const views = analytics.views_by_source[source] ?? 0;
              const signups = analytics.signups_by_source[source] ?? 0;
              const rate = analytics.conversion_rate_by_source[source] ?? 0;
              return (
                <div
                  key={source}
                  className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-gray-100 px-3 py-2 text-sm"
                >
                  <span className="font-medium text-gray-700">{source}</span>
                  <span className="text-gray-500">
                    {views} views · {signups} signups · {formatPercent(rate)}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {error && (
        <p className="mt-4 text-sm text-red-600">{error}</p>
      )}

      <div className="mt-6 border-t border-gray-100 pt-6">
        <button
          type="button"
          onClick={handleGenerateInsight}
          disabled={!thresholdMet || generating}
          className="inline-flex w-full items-center justify-center gap-2 rounded-lg bg-gray-900 px-5 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-gray-700 disabled:cursor-not-allowed disabled:opacity-50 sm:w-auto"
        >
          {generating ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Sparkles className="h-4 w-4" />
          )}
          {generating ? "Starting insight…" : "Generate insight"}
        </button>
        {!thresholdMet && (
          <p className="mt-2 text-xs text-gray-500">
            Need at least 10 page views or 1 signup to generate an insight
            report.
          </p>
        )}
      </div>
    </div>
  );
}
