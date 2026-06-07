"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { ArrowLeft, Loader2, RefreshCw } from "lucide-react";
import {
  confirmExperiment,
  generateInsight,
  generateLandingPage,
  getExperiment,
  ApiError,
} from "@/lib/api";
import type { Experiment, FounderDecision } from "@/lib/types";
import { StatusBadge } from "@/components/dashboard/StatusBadge";
import { DecisionPanel } from "@/components/insight/DecisionPanel";
import { InsightReportViewer } from "@/components/insight/InsightReportViewer";
import { MetricsWidget } from "@/components/insight/MetricsWidget";
import { ResearchProgress } from "@/components/research/ResearchProgress";
import { ValidationReportViewer } from "@/components/research/ValidationReportViewer";

const RESEARCH_IN_PROGRESS = new Set([
  "RESEARCHING",
  "RESEARCH_PLANNING",
  "RESEARCH_SEARCHING",
  "RESEARCH_READING",
  "RESEARCH_REFLECTING",
  "RESEARCH_SYNTHESIZING",
]);

export default function ExperimentDetailPage() {
  const params = useParams<{ id: string }>();
  const experimentId = params.id;

  const [experiment, setExperiment] = useState<Experiment | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [retrying, setRetrying] = useState(false);
  const [generatingLp, setGeneratingLp] = useState(false);
  const [retryingInsight, setRetryingInsight] = useState(false);

  const loadExperiment = useCallback(async () => {
    try {
      const data = await getExperiment(experimentId);
      setExperiment(data);
      setError(null);
    } catch (err) {
      setError(
        err instanceof ApiError && err.status === 404
          ? "Experiment not found."
          : "Could not load experiment.",
      );
    } finally {
      setLoading(false);
    }
  }, [experimentId]);

  useEffect(() => {
    loadExperiment();
  }, [loadExperiment]);

  useEffect(() => {
    if (experiment?.status !== "INSIGHT_GENERATING") return;

    const intervalId = setInterval(() => {
      void loadExperiment();
    }, 3000);

    return () => clearInterval(intervalId);
  }, [experiment?.status, loadExperiment]);

  const handleResearchComplete = useCallback(() => {
    loadExperiment();
  }, [loadExperiment]);

  async function handleRetryResearch() {
    setRetrying(true);
    try {
      await confirmExperiment(experimentId);
      await loadExperiment();
    } catch {
      setError("Could not restart research. Please try again.");
    } finally {
      setRetrying(false);
    }
  }

  async function handleGenerateLandingPage() {
    setGeneratingLp(true);
    try {
      await generateLandingPage(experimentId);
      await loadExperiment();
    } catch {
      setError("Could not start landing page generation. Please try again.");
    } finally {
      setGeneratingLp(false);
    }
  }

  async function handleRetryInsight() {
    setRetryingInsight(true);
    try {
      await generateInsight(experimentId);
      await loadExperiment();
    } catch {
      setError("Could not restart insight generation. Please try again.");
    } finally {
      setRetryingInsight(false);
    }
  }

  function handleDecision(_decision: FounderDecision) {
    void loadExperiment();
  }

  if (loading) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-[var(--fv-accent)]" />
      </div>
    );
  }

  if (error && !experiment) {
    return (
      <div className="mx-auto max-w-2xl px-4 py-16 text-center">
        <p className="text-sm text-red-300">{error}</p>
        <Link
          href="/dashboard"
          className="mt-4 inline-block text-sm font-medium text-[var(--fv-accent)] hover:text-[var(--fv-accent-hover)] no-underline"
        >
          Back to dashboard
        </Link>
      </div>
    );
  }

  if (!experiment) return null;

  const status = experiment.status;

  return (
    <div className="mx-auto max-w-3xl px-4 py-6 sm:px-6 sm:py-10">
      <div className="mb-8">
        <Link
          href="/dashboard"
          className="mb-4 inline-flex items-center gap-1.5 text-sm text-[var(--fv-text-muted)] hover:text-[var(--fv-text)] no-underline"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to dashboard
        </Link>
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="text-xl font-bold text-[var(--fv-text)] sm:text-2xl">
            Experiment
          </h1>
          <StatusBadge status={status} />
        </div>
      </div>

      {error && (
        <div className="fv-error mb-6 px-4 py-3 text-sm">
          {error}
        </div>
      )}

      {RESEARCH_IN_PROGRESS.has(status) && (
        <ResearchProgress
          experimentId={experimentId}
          onComplete={handleResearchComplete}
        />
      )}

      {status === "RESEARCH_READY" && (
        <ValidationReportViewer
          experimentId={experimentId}
          onGenerateLandingPage={handleGenerateLandingPage}
          generatingLandingPage={generatingLp}
        />
      )}

      {status === "RESEARCH_FAILED" && (
        <div className="fv-error px-6 py-8 text-center">
          <h2 className="text-lg font-semibold text-red-300">
            Research failed
          </h2>
          <p className="mt-2 text-sm text-red-200/80">
            Something went wrong during market research. You can retry and
            we&apos;ll pick up where we left off.
          </p>
          <button
            type="button"
            onClick={handleRetryResearch}
            disabled={retrying}
            className="fv-btn-ghost mt-6 inline-flex items-center gap-2 border-[rgba(239,68,68,0.3)] px-5 py-2.5 text-sm font-semibold text-red-300 hover:border-[rgba(239,68,68,0.5)] disabled:cursor-not-allowed disabled:opacity-50"
          >
            {retrying ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <RefreshCw className="h-4 w-4" />
            )}
            Retry research
          </button>
        </div>
      )}

      {status === "LANDING_LIVE" && (
        <div className="space-y-6">
          <MetricsWidget
            experimentId={experimentId}
            onInsightStarted={loadExperiment}
          />
          <div className="fv-card px-6 py-8">
            <h2 className="text-lg font-semibold text-[var(--fv-text)]">
              Landing page is live
            </h2>
            <p className="mt-2 text-sm text-[var(--fv-text-soft)]">
              Your landing page is published and collecting traffic. Drive
              distribution while metrics accumulate.
            </p>
            <Link
              href={`/experiment/${experimentId}/landing-page`}
              className="fv-btn-primary mt-6 px-5 py-2.5 text-sm no-underline"
            >
              Open landing page editor
            </Link>
          </div>
        </div>
      )}

      {status === "LANDING_DRAFT" && (
        <div className="fv-card px-6 py-8">
          <h2 className="text-lg font-semibold text-[var(--fv-text)]">
            Landing page draft ready
          </h2>
          <p className="mt-2 text-sm text-[var(--fv-text-soft)]">
            Your landing page draft has been generated. Review and customize it
            before publishing.
          </p>
          <Link
            href={`/experiment/${experimentId}/landing-page`}
            className="fv-btn-primary mt-6 px-5 py-2.5 text-sm no-underline"
          >
            Review & customize landing page
          </Link>
        </div>
      )}

      {status === "INSIGHT_GENERATING" && (
        <div className="fv-card flex flex-col items-center px-6 py-16 text-center">
          <Loader2 className="h-8 w-8 animate-spin text-[var(--fv-accent)]" />
          <p className="mt-4 text-sm font-medium text-[var(--fv-text)]">
            Generating insight report…
          </p>
          <p className="mt-1 text-sm text-[var(--fv-text-muted)]">
            Synthesizing cognitive research with your landing page behavior.
            This usually takes under a minute.
          </p>
        </div>
      )}

      {status === "INSIGHT_READY" && (
        <div className="space-y-8">
          <InsightReportViewer experimentId={experimentId} />
          <DecisionPanel
            experimentId={experimentId}
            onDecision={handleDecision}
          />
        </div>
      )}

      {status === "INSIGHT_FAILED" && (
        <div className="fv-error px-6 py-8 text-center">
          <h2 className="text-lg font-semibold text-red-300">
            Insight generation failed
          </h2>
          <p className="mt-2 text-sm text-red-200/80">
            Something went wrong while building your insight report. You can
            retry once you have enough traffic data.
          </p>
          <button
            type="button"
            onClick={handleRetryInsight}
            disabled={retryingInsight}
            className="fv-btn-ghost mt-6 inline-flex items-center gap-2 border-[rgba(239,68,68,0.3)] px-5 py-2.5 text-sm font-semibold text-red-300 hover:border-[rgba(239,68,68,0.5)] disabled:cursor-not-allowed disabled:opacity-50"
          >
            {retryingInsight ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <RefreshCw className="h-4 w-4" />
            )}
            Retry insight generation
          </button>
        </div>
      )}

      {status === "LANDING_GENERATING" && (
        <div className="fv-card flex flex-col items-center px-6 py-16 text-center">
          <Loader2 className="h-8 w-8 animate-spin text-[var(--fv-accent)]" />
          <p className="mt-4 text-sm font-medium text-[var(--fv-text)]">
            Generating your landing page…
          </p>
          <p className="mt-1 text-sm text-[var(--fv-text-muted)]">This usually takes a moment.</p>
        </div>
      )}

      {!RESEARCH_IN_PROGRESS.has(status) &&
        status !== "RESEARCH_READY" &&
        status !== "RESEARCH_FAILED" &&
        status !== "LANDING_DRAFT" &&
        status !== "LANDING_LIVE" &&
        status !== "LANDING_GENERATING" &&
        status !== "INSIGHT_GENERATING" &&
        status !== "INSIGHT_READY" &&
        status !== "INSIGHT_FAILED" && (
          <div className="fv-card px-6 py-8 text-center">
            <p className="text-sm text-[var(--fv-text-soft)]">
              This experiment is in{" "}
              <span className="font-medium text-[var(--fv-text)]">{status.replace(/_/g, " ").toLowerCase()}</span>{" "}
              status.
            </p>
            {(status === "DRAFT" ||
              status === "REFINING" ||
              status === "REFINED") && (
              <Link
                href="/new"
                className="mt-4 inline-block text-sm font-semibold text-[var(--fv-accent)] hover:text-[var(--fv-accent-hover)] no-underline"
              >
                Continue in chat
              </Link>
            )}
          </div>
        )}
    </div>
  );
}
