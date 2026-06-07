"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { ArrowLeft, Loader2, RefreshCw } from "lucide-react";
import {
  confirmExperiment,
  generateLandingPage,
  getExperiment,
  ApiError,
} from "@/lib/api";
import type { Experiment } from "@/lib/types";
import { StatusBadge } from "@/components/dashboard/StatusBadge";
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

  if (loading) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
      </div>
    );
  }

  if (error && !experiment) {
    return (
      <div className="mx-auto max-w-2xl px-4 py-16 text-center">
        <p className="text-sm text-red-700">{error}</p>
        <Link
          href="/dashboard"
          className="mt-4 inline-block text-sm font-medium text-gray-900 hover:underline"
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
          className="mb-4 inline-flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-900"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to dashboard
        </Link>
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="text-xl font-bold text-gray-900 sm:text-2xl">
            Experiment
          </h1>
          <StatusBadge status={status} />
        </div>
      </div>

      {error && (
        <div className="mb-6 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
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
        <div className="rounded-xl border border-red-200 bg-red-50 px-6 py-8 text-center">
          <h2 className="text-lg font-semibold text-red-900">
            Research failed
          </h2>
          <p className="mt-2 text-sm text-red-700">
            Something went wrong during market research. You can retry and
            we&apos;ll pick up where we left off.
          </p>
          <button
            type="button"
            onClick={handleRetryResearch}
            disabled={retrying}
            className="mt-6 inline-flex items-center gap-2 rounded-lg bg-red-800 px-5 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-red-900 disabled:cursor-not-allowed disabled:opacity-50"
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

      {(status === "LANDING_DRAFT" || status === "LANDING_LIVE") && (
        <div className="rounded-xl border border-gray-200 bg-white px-6 py-8 shadow-sm">
          <h2 className="text-lg font-semibold text-gray-900">
            {status === "LANDING_LIVE"
              ? "Landing page is live"
              : "Landing page draft ready"}
          </h2>
          <p className="mt-2 text-sm text-gray-600">
            {status === "LANDING_LIVE"
              ? "Your landing page is published and collecting traffic."
              : "Your landing page draft has been generated. Review and customize it before publishing."}
          </p>
          <Link
            href={`/experiment/${experimentId}/landing-page`}
            className="mt-6 inline-flex rounded-lg bg-gray-900 px-5 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-gray-700"
          >
            Open landing page editor
          </Link>
          <p className="mt-2 text-xs text-gray-400">(Coming in FE5)</p>
        </div>
      )}

      {status === "LANDING_GENERATING" && (
        <div className="flex flex-col items-center rounded-xl border border-gray-200 bg-white px-6 py-16 text-center shadow-sm">
          <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
          <p className="mt-4 text-sm font-medium text-gray-900">
            Generating your landing page…
          </p>
          <p className="mt-1 text-sm text-gray-500">This usually takes a moment.</p>
        </div>
      )}

      {!RESEARCH_IN_PROGRESS.has(status) &&
        status !== "RESEARCH_READY" &&
        status !== "RESEARCH_FAILED" &&
        status !== "LANDING_DRAFT" &&
        status !== "LANDING_LIVE" &&
        status !== "LANDING_GENERATING" && (
          <div className="rounded-xl border border-gray-200 bg-white px-6 py-8 text-center shadow-sm">
            <p className="text-sm text-gray-600">
              This experiment is in{" "}
              <span className="font-medium">{status.replace(/_/g, " ").toLowerCase()}</span>{" "}
              status.
            </p>
            {(status === "DRAFT" ||
              status === "REFINING" ||
              status === "REFINED") && (
              <Link
                href="/new"
                className="mt-4 inline-block text-sm font-semibold text-gray-900 hover:underline"
              >
                Continue in chat
              </Link>
            )}
          </div>
        )}
    </div>
  );
}
