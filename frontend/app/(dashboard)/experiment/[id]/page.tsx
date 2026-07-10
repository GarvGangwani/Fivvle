"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { ExperimentCanvas } from "@/components/experiment/ExperimentCanvas";
import { ApiError, getExperiment } from "@/lib/api";
import type { Experiment } from "@/lib/types";

export default function ExperimentDetailPage() {
  const params = useParams<{ id: string }>();
  const [experiment, setExperiment] = useState<Experiment | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    void getExperiment(params.id)
      .then((data) => {
        if (!cancelled) setExperiment(data);
      })
      .catch((err) => {
        if (cancelled) return;
        if (err instanceof ApiError && err.status === 404) {
          setError("Experiment not found.");
          return;
        }
        setError("Could not load experiment.");
      });
    return () => {
      cancelled = true;
    };
  }, [params.id]);

  if (error) {
    return (
      <div className="p-8 font-body-md text-body-md text-status-critical">{error}</div>
    );
  }

  if (!experiment) {
    return (
      <div className="p-8 font-body-md text-body-md text-ink-secondary">
        Loading canvas...
      </div>
    );
  }

  return (
    <div className="-mx-gutter -mb-gutter h-[calc(100vh-4rem)] min-h-0">
      <ExperimentCanvas experiment={experiment} />
    </div>
  );
}
