"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { getExperiment, getLandingPage, ApiError } from "@/lib/api";
import type { Experiment, LandingPage } from "@/lib/types";
import { EditorLayout } from "@/components/landing-page-editor/EditorLayout";
import { EditorLoadingSkeleton } from "@/components/landing-page-editor/EditorLoadingSkeleton";
import { LandingGenerationProgress } from "@/components/research/LandingGenerationProgress";

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
      const exp = await getExperiment(experimentId);
      setExperiment(exp);
      setError(null);

      if (exp.status === "LANDING_GENERATING") {
        return;
      }

      if (!LP_EDITOR_STATUSES.has(exp.status)) {
        router.replace(`/experiment/${experimentId}`);
        return;
      }

      const lp = await getLandingPage(experimentId);
      setLandingPage(lp);
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
    void loadData();
  }, [loadData]);

  if (loading) {
    return <EditorLoadingSkeleton />;
  }

  if (experiment?.status === "LANDING_GENERATING") {
    return (
      <div className="mx-auto max-w-lg px-4 py-10">
        <LandingGenerationProgress
          experimentId={experimentId}
          onComplete={() => {
            setLoading(true);
            void loadData();
          }}
        />
      </div>
    );
  }

  if (error || !experiment || !landingPage) {
    return (
      <div className="mx-auto max-w-lg px-4 py-16 text-center">
        <p className="text-sm text-red-300">
          {error ?? "Landing page unavailable."}
        </p>
        <Link
          href={`/experiment/${experimentId}`}
          className="mt-4 inline-block text-sm font-medium text-[var(--fv-accent)] no-underline hover:text-[var(--fv-accent-hover)]"
        >
          Back to experiment
        </Link>
      </div>
    );
  }

  const experimentName =
    landingPage.headline ||
    landingPage.copy_json?.hero?.headline ||
    "Landing page";

  return (
    <div className="flex min-h-[calc(100dvh-58px)] flex-col px-4 py-4 sm:px-6 sm:py-6">
      <EditorLayout
        experimentId={experimentId}
        experimentName={experimentName}
        experimentStatus={experiment.status}
        landingPage={landingPage}
        onPublished={loadData}
      />
    </div>
  );
}
