"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import type { ExperimentSummary } from "@/lib/types";
import { marketingButtonClass } from "@/components/marketing/marketing-styles";
import {
  getActLabel,
  getExperimentDisplayTitle,
  getInsightDataPoint,
  mapStatusToPill,
} from "./dashboard-helpers";

interface WorkspaceInsightCardProps {
  experiment: ExperimentSummary | null;
  hasExperiments: boolean;
}

export function WorkspaceInsightCard({
  experiment,
  hasExperiments,
}: WorkspaceInsightCardProps) {
  const router = useRouter();

  if (!hasExperiments || !experiment) {
    return (
      <div className="flex min-h-[280px] flex-col justify-between rounded-md border-2 border-border-master bg-accent p-6 pb-8 text-ink-inverse shadow-brutal-md lg:min-h-[320px]">
        <div>
          <p className="font-label-md text-label-md uppercase opacity-70">
            LATEST SIGNAL
          </p>
          <h2 className="mt-3 font-headline text-headline-lg text-ink-inverse">
            Ready to validate your first idea?
          </h2>
          <p className="mt-3 max-w-lg font-body-md text-body-md opacity-90">
            Start a new validation and Fivvle will research, test, and score it
            against real signal.
          </p>
        </div>
        <Link
          href="/new"
          className={`${marketingButtonClass} mt-6 inline-flex w-fit bg-accent px-6 py-3 font-label-md text-label-md uppercase text-ink-inverse no-underline`}
        >
          START NEW VALIDATION
        </Link>
      </div>
    );
  }

  const pill = mapStatusToPill(experiment.status);
  const title = getExperimentDisplayTitle(experiment);
  const dataPoint = getInsightDataPoint(experiment);

  return (
    <div className="flex min-h-[280px] flex-col justify-between rounded-md border-2 border-border-master bg-accent p-6 pb-8 text-ink-inverse shadow-brutal-md lg:min-h-[320px]">
      <div>
        <p className="font-label-md text-label-md uppercase opacity-70">
          LATEST SIGNAL
        </p>
        <h2 className="mt-3 font-headline text-headline-lg text-ink-inverse">
          Your most active validation
        </h2>
        <p className="mt-4 font-headline text-headline-md text-ink-inverse">
          {title}
        </p>
        <p className="mt-2 font-label-md text-label-md uppercase opacity-80">
          ACT: {getActLabel(pill)}
        </p>
        <p className="mt-2 font-body-md text-body-md opacity-90">{dataPoint}</p>
      </div>

      <div className="mt-6 flex flex-col gap-3 sm:flex-row sm:flex-wrap">
        <button
          type="button"
          onClick={() => router.push(`/experiment/${experiment.id}`)}
          className={`${marketingButtonClass} bg-brutalist-yellow px-6 py-3 font-label-md text-label-md uppercase text-ink-primary`}
        >
          OPEN EXPERIMENT →
        </button>
        <Link
          href="/experiments"
          className={`${marketingButtonClass} bg-surface-card px-6 py-3 font-label-md text-label-md uppercase text-ink-primary no-underline`}
        >
          VIEW ALL SIGNAL
        </Link>
      </div>
    </div>
  );
}
