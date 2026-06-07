"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, Loader2 } from "lucide-react";
import { getExperiment, getLandingPage, ApiError } from "@/lib/api";
import type { Experiment, LandingPage } from "@/lib/types";
import { StatusBadge } from "@/components/dashboard/StatusBadge";
import { EditorLayout } from "@/components/landing-page-editor/EditorLayout";

const LP_EDITOR_STATUSES = new Set(["LANDING_DRAFT", "LANDING_LIVE"]);

export default function LandingPageEditorPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const experimentId = params.id;

  const [experiment, setExperiment] = useState<Experiment | null>(null);
  const [landingPage, setLandingPage] = useState<LandingPage | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    try {
      const [exp, lp] = await Promise.all([
        getExperiment(experimentId),
        getLandingPage(experimentId),
      ]);
      setExperiment(exp);
      setLandingPage(lp);
      setError(null);

      if (exp.status === "LANDING_GENERATING") {
        return;
      }
      if (!LP_EDITOR_STATUSES.has(exp.status)) {
        router.replace(`/experiment/${experimentId}`);
      }
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) {
        setError("Landing page not found. It may still be generating.");
      } else {
        setError("Could not load landing page data.");
      }
    } finally {
      setLoading(false);
    }
  }, [experimentId, router]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  useEffect(() => {
    if (experiment?.status !== "LANDING_GENERATING") return;

    const intervalId = setInterval(() => {
      void loadData();
    }, 3000);

    return () => clearInterval(intervalId);
  }, [experiment?.status, loadData]);

  if (loading) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
      </div>
    );
  }

  if (experiment?.status === "LANDING_GENERATING") {
    return (
      <div className="mx-auto max-w-lg px-4 py-20 text-center">
        <Loader2 className="mx-auto h-8 w-8 animate-spin text-gray-400" />
        <p className="mt-4 text-sm font-medium text-gray-900">
          Generating your landing page…
        </p>
        <p className="mt-1 text-sm text-gray-500">This usually takes a moment.</p>
      </div>
    );
  }

  if (error || !experiment || !landingPage) {
    return (
      <div className="mx-auto max-w-lg px-4 py-16 text-center">
        <p className="text-sm text-red-700">
          {error ?? "Landing page unavailable."}
        </p>
        <Link
          href={`/experiment/${experimentId}`}
          className="mt-4 inline-block text-sm font-medium text-gray-900 hover:underline"
        >
          Back to experiment
        </Link>
      </div>
    );
  }

  return (
    <div className="flex min-h-[calc(100dvh-4rem)] flex-col px-4 py-4 sm:px-6 sm:py-6">
      <div className="mb-4 shrink-0">
        <Link
          href={`/experiment/${experimentId}`}
          className="mb-3 inline-flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-900"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to experiment
        </Link>
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="text-xl font-bold text-gray-900">Landing page editor</h1>
          <StatusBadge status={experiment.status} />
        </div>
      </div>

      <EditorLayout
        experimentId={experimentId}
        experimentStatus={experiment.status}
        landingPage={landingPage}
        onPublished={loadData}
      />
    </div>
  );
}
