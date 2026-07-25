"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { ExperimentCanvas } from "@/components/experiment/ExperimentCanvas";
import { ExperimentLoadingScreen } from "@/components/experiment/ExperimentLoadingScreen";
import { useDelayedLoading } from "@/hooks/useDelayedLoading";
import { ApiError, getExperiment } from "@/lib/api";
import { peekExperimentName } from "@/lib/experiment-name-cache";
import type { Experiment } from "@/lib/types";

export default function ExperimentDetailPage() {
  const params = useParams<{ id: string }>();
  const [experiment, setExperiment] = useState<Experiment | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [cachedName, setCachedName] = useState<string | null>(null);

  const showLoading = useDelayedLoading(loading, 400);

  useEffect(() => {
    setCachedName(peekExperimentName(params.id));
  }, [params.id]);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    setExperiment(null);

    void getExperiment(params.id)
      .then((data) => {
        if (cancelled) return;
        setExperiment(data);
      })
      .catch((err) => {
        if (cancelled) return;
        if (err instanceof ApiError && err.status === 404) {
          setError("Experiment not found.");
          return;
        }
        setError("Could not load experiment.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [params.id]);

  if (error && !loading) {
    return (
      <div className="p-8 font-body-md text-body-md text-status-critical">
        {error}
      </div>
    );
  }

  if (showLoading) {
    return (
      <ExperimentLoadingScreen
        projectName={experiment?.name ?? cachedName}
      />
    );
  }

  if (!experiment) {
    return null;
  }

  return (
    <div className="h-screen min-h-0">
      <ExperimentCanvas
        experiment={experiment}
        onExperimentChange={setExperiment}
      />
    </div>
  );
}
