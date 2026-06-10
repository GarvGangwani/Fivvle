"use client";

import Link from "next/link";
import type { ExperimentSummary } from "@/lib/types";
import { StatusBadge } from "./StatusBadge";

type ExperimentWithRefinement = ExperimentSummary & {
  refined_idea?: { one_liner?: string; refined_one_liner?: string } | null;
};

interface ExperimentCardProps {
  experiment: ExperimentWithRefinement;
}

function getIdeaName(experiment: ExperimentWithRefinement): string {
  const oneLiner =
    experiment.refined_idea?.one_liner ??
    experiment.refined_idea?.refined_one_liner;
  if (oneLiner) return oneLiner;

  const raw = experiment.raw_idea;
  if (raw.length <= 80) return raw;
  return `${raw.slice(0, 80)}…`;
}

function formatRelativeTime(dateStr: string): string {
  const date = new Date(dateStr);
  const seconds = Math.floor((Date.now() - date.getTime()) / 1000);

  if (seconds < 60) return "just now";

  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) {
    return `${minutes} minute${minutes === 1 ? "" : "s"} ago`;
  }

  const hours = Math.floor(minutes / 60);
  if (hours < 24) {
    return `${hours} hour${hours === 1 ? "" : "s"} ago`;
  }

  const days = Math.floor(hours / 24);
  if (days < 30) {
    return `${days} day${days === 1 ? "" : "s"} ago`;
  }

  const months = Math.floor(days / 30);
  if (months < 12) {
    return `${months} month${months === 1 ? "" : "s"} ago`;
  }

  const years = Math.floor(months / 12);
  return `${years} year${years === 1 ? "" : "s"} ago`;
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

export function ExperimentCard({ experiment }: ExperimentCardProps) {
  const ideaName = getIdeaName(experiment);

  return (
    <Link
      href={`/experiment/${experiment.id}`}
      className="fv-card fv-card-hover group flex h-full flex-col p-5 no-underline"
    >
      <div className="mb-3 flex items-start justify-between gap-3">
        <h2 className="line-clamp-2 text-base font-semibold text-[var(--fv-text)] group-hover:text-[var(--fv-text-soft)]">
          {ideaName}
        </h2>
        <StatusBadge status={experiment.status} />
      </div>

      {experiment.slug && (
        <p className="mb-4 font-mono text-sm text-[var(--fv-text-muted)]">
          {experiment.slug}
        </p>
      )}

      <div className="mt-auto flex flex-wrap items-center gap-x-4 gap-y-1 pt-3 text-xs text-[var(--fv-text-muted)]">
        <span>Created {formatDate(experiment.created_at)}</span>
        <span>Updated {formatRelativeTime(experiment.updated_at)}</span>
      </div>
    </Link>
  );
}
