"use client";

import { ArrowRight, BarChart3, Coins, Eye, Lock, MousePointerClick, Users } from "lucide-react";
import type { ExperimentSummary } from "@/lib/types";
import { formatRelativeTime } from "@/lib/format-time";
import { getExperimentDisplayName } from "@/lib/experiment-name";
import { METRICS_PAYWALL_CREDITS } from "@/lib/pricing";
import { StatusBadge } from "./StatusBadge";

const LIVE_STATUSES = new Set([
  "LANDING_LIVE",
  "INSIGHT_GENERATING",
  "INSIGHT_READY",
  "INSIGHT_FAILED",
  "COMPLETED",
]);

const STAGE_HINTS: Record<string, string> = {
  DRAFT: "Idea captured",
  REFINING: "AI refinement in progress",
  REFINED: "Ready to start research",
  RESEARCHING: "Market research running",
  RESEARCH_PLANNING: "Planning research",
  RESEARCH_SEARCHING: "Searching sources",
  RESEARCH_READING: "Reading sources",
  RESEARCH_REFLECTING: "Reflecting on findings",
  RESEARCH_SYNTHESIZING: "Writing validation report",
  RESEARCH_READY: "Validation report ready",
  RESEARCH_FAILED: "Research needs attention",
  LANDING_GENERATING: "Generating landing page",
  LANDING_DRAFT: "Landing page ready to publish",
  LANDING_LIVE: "Live — collecting traffic",
  INSIGHT_GENERATING: "Generating insight report",
  INSIGHT_READY: "Insight report ready",
  INSIGHT_FAILED: "Insight generation failed",
  COMPLETED: "Validation complete",
  ARCHIVED: "Archived",
};

function formatCount(value: number): string {
  if (value >= 1_000_000) {
    return `${(value / 1_000_000).toFixed(1).replace(/\.0$/, "")}M`;
  }
  if (value >= 10_000) {
    return `${Math.round(value / 1000)}k`;
  }
  if (value >= 1_000) {
    return `${(value / 1000).toFixed(1).replace(/\.0$/, "")}k`;
  }
  return value.toLocaleString();
}

function formatConversion(views: number, signups: number): string {
  if (views <= 0) return "—";
  return `${((signups / views) * 100).toFixed(1)}%`;
}

interface ProjectCardProps {
  experiment: ExperimentSummary;
  onClick: () => void;
}

export function ProjectCard({ experiment, onClick }: ProjectCardProps) {
  const name = getExperimentDisplayName(experiment);
  const stats = experiment.card_stats;
  const isLive = LIVE_STATUSES.has(experiment.status);
  const showStats = isLive && stats != null;
  const showMetricsLocked = isLive && stats == null;
  const stageHint = STAGE_HINTS[experiment.status] ?? "In progress";

  return (
    <button
      type="button"
      onClick={onClick}
      className="fv-project-card group text-left"
    >
      <div className="mb-3 flex items-start justify-between gap-3">
        <h3 className="min-w-0 flex-1 truncate text-base font-semibold text-[var(--fv-text)] group-hover:text-[var(--fv-accent)]">
          {name}
        </h3>
        <StatusBadge status={experiment.status} />
      </div>

      <p className="line-clamp-2 min-h-[2.75rem] text-sm leading-relaxed text-[var(--fv-text-muted)]">
        {experiment.raw_idea?.trim() ?? ""}
      </p>

      {showStats ? (
        <div className="fv-project-card-stats">
          <div className="fv-project-stat">
            <Eye className="fv-project-stat-icon" aria-hidden />
            <span className="fv-project-stat-value">{formatCount(stats.page_views)}</span>
            <span className="fv-project-stat-label">Views</span>
          </div>
          <div className="fv-project-stat">
            <Users className="fv-project-stat-icon" aria-hidden />
            <span className="fv-project-stat-value">
              {formatCount(stats.waitlist_signups)}
            </span>
            <span className="fv-project-stat-label">Signups</span>
          </div>
          <div className="fv-project-stat">
            <MousePointerClick className="fv-project-stat-icon" aria-hidden />
            <span className="fv-project-stat-value">
              {formatConversion(stats.page_views, stats.waitlist_signups)}
            </span>
            <span className="fv-project-stat-label">Conv.</span>
          </div>
        </div>
      ) : showMetricsLocked ? (
        <div className="fv-project-metrics-locked" aria-label="Metrics locked">
          <div className="fv-project-metrics-locked-head">
            <span className="fv-project-metrics-locked-icon-wrap">
              <BarChart3 className="h-4 w-4" aria-hidden />
              <Lock className="fv-project-metrics-locked-badge" aria-hidden />
            </span>
            <div className="min-w-0">
              <p className="text-sm font-medium text-[var(--fv-text-soft)]">
                Behavioral metrics locked
              </p>
              <p className="mt-0.5 text-xs leading-relaxed text-[var(--fv-text-muted)]">
                Unlock on the Metrics tab to see views, signups, and conversion.
              </p>
            </div>
          </div>
          <p className="fv-project-metrics-locked-cost">
            <Coins className="h-3.5 w-3.5 text-[var(--fv-accent)]" aria-hidden />
            {METRICS_PAYWALL_CREDITS} Credits
          </p>
        </div>
      ) : (
        <p className="fv-project-stage-hint">{stageHint}</p>
      )}

      <div className="fv-project-card-footer">
        <span className="text-xs text-[var(--fv-text-dim)]">
          Updated {formatRelativeTime(experiment.updated_at)}
        </span>
        <ArrowRight className="h-4 w-4 text-[var(--fv-text-dim)] transition-transform group-hover:translate-x-0.5 group-hover:text-[var(--fv-accent)]" />
      </div>
    </button>
  );
}
