"use client";

import { useRouter } from "next/navigation";
import type { KeyboardEvent } from "react";
import type { ExperimentSummary } from "@/lib/types";
import { StatusBadge } from "./StatusBadge";
import { cacheExperimentName } from "@/lib/experiment-name-cache";
import {
  formatExperimentId,
  getActLabel,
  getExperimentDisplayTitle,
  getHardcodedProgressPercent,
  getProgressBarFillClass,
  mapStatusToPill,
} from "./dashboard-helpers";

interface ProjectCardProps {
  experiment: ExperimentSummary;
  archived?: boolean;
}

export function ProjectCard({ experiment, archived = false }: ProjectCardProps) {
  const router = useRouter();
  const pill = archived ? "ARCHIVED" : mapStatusToPill(experiment.status);
  const progress = getHardcodedProgressPercent(
    experiment.status,
    experiment.id,
  );
  const href = `/experiment/${experiment.id}`;

  function navigate() {
    cacheExperimentName(experiment.id, getExperimentDisplayTitle(experiment));
    router.push(href);
  }

  function handleKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      navigate();
    }
  }

  const hoverClass = archived
    ? ""
    : "shadow-brutal-md fv-brutal-hover";

  const tags = experiment.tags ?? [];

  return (
    <div
      role="link"
      tabIndex={0}
      onClick={navigate}
      onKeyDown={handleKeyDown}
      onMouseEnter={() => {
        router.prefetch(href);
      }}
      className={`group flex cursor-pointer flex-col rounded-md border-2 border-border-master bg-surface-card ${hoverClass} ${
        archived ? "opacity-70" : ""
      }`}
    >
      <div className="flex flex-1 flex-col p-card-padding">
        <div className="mb-3 flex items-start justify-between gap-3">
          <span className="font-mono text-mono-sm uppercase tracking-wide text-ink-tertiary">
            ID: {formatExperimentId(experiment.id)}
          </span>
          <StatusBadge
            status={experiment.status}
            forcePill={archived ? "ARCHIVED" : undefined}
          />
        </div>

        <h3 className="font-headline text-headline-md text-ink-primary">
          {getExperimentDisplayTitle(experiment)}
        </h3>

        <div className="mt-4 flex items-center justify-between gap-2">
          <span className="font-label-md text-label-md uppercase text-ink-secondary">
            ACT: {getActLabel(pill)}
          </span>
          <span className="font-mono text-mono-md text-ink-primary">
            {progress}%
          </span>
        </div>

        <div
          className="mt-2 h-2 border border-border-master bg-surface-card"
          role="progressbar"
          aria-valuenow={progress}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-label={`${getActLabel(pill)} act progress`}
        >
          <div
            className={`h-full ${getProgressBarFillClass(pill)}`}
            style={{ width: `${progress}%` }}
          />
        </div>

        <div className="mt-4 flex flex-wrap gap-2">
          {tags.length > 0 ? (
            tags.map((tag) => (
              <span
                key={tag}
                className="rounded-sm border-2 border-border-master bg-surface-elevated px-2 py-1 font-mono text-mono-sm uppercase text-ink-secondary"
              >
                {tag}
              </span>
            ))
          ) : (
            <span className="font-mono text-mono-sm uppercase text-ink-tertiary">
              Generating tags...
            </span>
          )}
        </div>
      </div>

      <div className="border-t-2 border-border-master px-card-padding py-3 transition-colors group-hover:bg-accent group-hover:text-ink-inverse">
        <span className="block font-label-md text-label-md uppercase">
          VIEW EXPERIMENT →
        </span>
      </div>
    </div>
  );
}
