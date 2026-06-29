"use client";

import { ExperimentDetailPanel } from "@/components/dashboard/ExperimentDetailPanel";
import type { ExperimentStageId } from "@/lib/experiment-stages";
import { useParams, useSearchParams } from "next/navigation";

function parseInitialStage(value: string | null): ExperimentStageId | undefined {
  if (
    value === "refine" ||
    value === "report" ||
    value === "landing" ||
    value === "metrics" ||
    value === "insight"
  ) {
    return value;
  }
  return undefined;
}

export default function ExperimentDetailPage() {
  const params = useParams<{ id: string }>();
  const searchParams = useSearchParams();
  const initialStage = parseInitialStage(searchParams.get("stage"));

  return (
    <div className="flex h-full min-h-0 flex-col">
      <ExperimentDetailPanel
        experimentId={params.id}
        initialStage={initialStage}
      />
    </div>
  );
}
