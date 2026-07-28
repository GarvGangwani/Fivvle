"use client";

import { useMemo, useState } from "react";
import { ChevronRight, X } from "lucide-react";
import type { SectionScore, ValidationReport } from "@/lib/types";
import {
  buildOverallScoreDetail,
  buildSectionScoreDetails,
  type OverallScoreDetail,
  type ScoreSelectionId,
  type SectionScoreDetail,
} from "@/lib/validation-report-score-details";
import { scoreTone } from "@/lib/validation-report-scores";

interface ReportScoreSectionProps {
  report: ValidationReport;
  sections: SectionScore[];
  overall: number;
  derived?: boolean;
}

function scoreFillClass(tone: "strong" | "mixed" | "weak"): string {
  switch (tone) {
    case "strong":
      return "bg-status-success";
    case "mixed":
      return "bg-status-warning";
    case "weak":
      return "bg-status-critical";
  }
}

function scoreTextClass(tone: "strong" | "mixed" | "weak"): string {
  switch (tone) {
    case "strong":
      return "text-status-success";
    case "mixed":
      return "text-status-warning";
    case "weak":
      return "text-status-critical";
  }
}

function ScoreBar({
  score,
  size = "md",
  label,
}: {
  score: number;
  size?: "md" | "lg";
  label: string;
}) {
  const tone = scoreTone(score);
  const trackHeight = size === "lg" ? "h-3" : "h-2";
  return (
    <div className="mt-2 w-full">
      <div
        className={`w-full overflow-hidden border-2 border-border-master bg-surface-elevated ${trackHeight}`}
        role="progressbar"
        aria-valuenow={score}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={`${label}: ${score} out of 100`}
      >
        <div
          className={`h-full ${scoreFillClass(tone)}`}
          style={{ width: `${score}%` }}
        />
      </div>
    </div>
  );
}

function BulletList({
  items,
  variant,
}: {
  items: string[];
  variant: "pro" | "con";
}) {
  if (items.length === 0) {
    return (
      <p className="font-mono text-mono-sm uppercase text-ink-tertiary">
        {variant === "pro"
          ? "No clear positives surfaced."
          : "No major caveats noted."}
      </p>
    );
  }
  return (
    <ul
      className={`list-disc space-y-1 pl-4 font-body text-body-sm text-ink-primary ${
        variant === "pro" ? "marker:text-status-success" : "marker:text-status-critical"
      }`}
    >
      {items.map((item) => (
        <li key={item}>{item}</li>
      ))}
    </ul>
  );
}

function ScoreDetailPanel({
  detail,
  onClose,
}: {
  detail: SectionScoreDetail | OverallScoreDetail;
  onClose: () => void;
}) {
  const id = "id" in detail ? detail.id : detail.section_id;
  const tone = scoreTone(detail.score);

  return (
    <div
      className="mt-3 border-2 border-border-master bg-surface-elevated p-4 shadow-brutal-sm"
      role="region"
      aria-labelledby={`score-detail-title-${id}`}
    >
      <div className="mb-3 flex items-start gap-3">
        <div className="min-w-0 flex-1">
          <p className="font-mono text-mono-sm uppercase text-ink-tertiary">
            Score breakdown
          </p>
          <h3
            id={`score-detail-title-${id}`}
            className="mt-1 font-headline text-headline-md uppercase tracking-tighter text-ink-primary"
          >
            {detail.label}
          </h3>
        </div>
        <span
          className={`font-mono text-mono-md font-bold tabular-nums ${scoreTextClass(tone)}`}
        >
          {detail.score}
        </span>
        <button
          type="button"
          onClick={onClose}
          className="border-2 border-border-master bg-surface-card p-1 text-ink-tertiary transition-colors hover:text-ink-primary"
          aria-label="Close score details"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      <ScoreBar score={detail.score} label={detail.label} />

      <div className="mt-4 space-y-4">
        <div>
          <p className="mb-1 font-mono text-mono-sm uppercase text-ink-tertiary">
            Why this score
          </p>
          <p className="font-body text-body-sm leading-relaxed text-ink-primary">
            {detail.rationale}
          </p>
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <p className="mb-1 font-mono text-mono-sm uppercase text-status-success">
              Supporting signals
            </p>
            <BulletList items={detail.pros} variant="pro" />
          </div>
          <div>
            <p className="mb-1 font-mono text-mono-sm uppercase text-status-critical">
              Caveats & gaps
            </p>
            <BulletList items={detail.cons} variant="con" />
          </div>
        </div>

        <div>
          <p className="mb-1 font-mono text-mono-sm uppercase text-ink-tertiary">
            Context from report
          </p>
          <p className="border-2 border-border-master bg-surface-card p-3 font-body text-body-sm leading-relaxed text-ink-secondary">
            {detail.context}
          </p>
        </div>
      </div>
    </div>
  );
}

function SectionScoreCard({
  detail,
  selected,
  onSelect,
}: {
  detail: SectionScoreDetail;
  selected: boolean;
  onSelect: () => void;
}) {
  const tone = scoreTone(detail.score);
  return (
    <button
      type="button"
      onClick={onSelect}
      aria-expanded={selected}
      aria-controls={`score-detail-${detail.section_id}`}
      className={`w-full border-2 border-border-master p-3 text-left transition-all ${
        selected
          ? "bg-brand-primary text-ink-inverse shadow-brutal-md"
          : "bg-surface-elevated text-ink-primary shadow-brutal-sm hover:-translate-y-0.5 hover:shadow-brutal-md"
      }`}
    >
      <div className="flex items-center justify-between gap-2">
        <p
          className={`font-mono text-mono-sm uppercase ${
            selected ? "text-ink-inverse/80" : "text-ink-tertiary"
          }`}
        >
          {detail.label}
        </p>
        <span className="flex items-center gap-1">
          <span
            className={`font-mono text-mono-md font-bold tabular-nums ${
              selected ? "text-ink-inverse" : scoreTextClass(tone)
            }`}
          >
            {detail.score}
          </span>
          <ChevronRight
            className={`h-4 w-4 transition-transform ${
              selected ? "rotate-90 text-ink-inverse" : "text-ink-tertiary"
            }`}
            aria-hidden
          />
        </span>
      </div>
      <div className={selected ? "[&_.border-border-master]:border-ink-inverse/40" : ""}>
        <ScoreBar score={detail.score} label={detail.label} />
      </div>
    </button>
  );
}

export function ReportScoreSection({
  report,
  sections,
  overall,
  derived = false,
}: ReportScoreSectionProps) {
  const [selectedId, setSelectedId] = useState<ScoreSelectionId | null>(null);

  const sectionDetails = useMemo(
    () => buildSectionScoreDetails(report, sections),
    [report, sections],
  );

  const overallDetail = useMemo(
    () => buildOverallScoreDetail(report, overall),
    [report, overall],
  );

  const activeDetail: SectionScoreDetail | OverallScoreDetail | null =
    selectedId === "overall"
      ? overallDetail
      : selectedId
        ? (sectionDetails.find((d) => d.section_id === selectedId) ?? null)
        : null;

  function toggleSelection(id: ScoreSelectionId) {
    setSelectedId((current) => (current === id ? null : id));
  }

  const overallSelected = selectedId === "overall";
  const overallTone = scoreTone(overall);

  return (
    <section
      id="report-scores"
      className="mt-5 border-2 border-border-master bg-surface-card p-4 shadow-brutal-sm"
      aria-labelledby="report-scores-heading"
    >
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2 border-b-2 border-border-master pb-3">
        <h2
          id="report-scores-heading"
          className="font-mono text-mono-sm uppercase tracking-wider text-ink-secondary"
        >
          Validation scores
        </h2>
        <span className="font-mono text-mono-sm uppercase text-ink-tertiary">
          {derived ? "Estimated from evidence · " : ""}
          Tap a score for details
        </span>
      </div>

      <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
        {sectionDetails.map((detail) => (
          <SectionScoreCard
            key={detail.section_id}
            detail={detail}
            selected={selectedId === detail.section_id}
            onSelect={() => toggleSelection(detail.section_id)}
          />
        ))}
      </div>

      <button
        type="button"
        onClick={() => toggleSelection("overall")}
        aria-expanded={overallSelected}
        className={`mt-3 w-full border-2 border-border-master p-4 text-left transition-all ${
          overallSelected
            ? "bg-brand-primary text-ink-inverse shadow-brutal-md"
            : "bg-surface-elevated text-ink-primary shadow-brutal-sm hover:-translate-y-0.5 hover:shadow-brutal-md"
        }`}
      >
        <div className="flex items-center justify-between gap-2">
          <p
            className={`font-mono text-mono-sm uppercase ${
              overallSelected ? "text-ink-inverse/80" : "text-ink-tertiary"
            }`}
          >
            Overall score
          </p>
          <span className="flex items-center gap-1">
            <span
              className={`font-mono text-headline-md font-bold tabular-nums ${
                overallSelected
                  ? "text-ink-inverse"
                  : scoreTextClass(overallTone)
              }`}
            >
              {overall}
            </span>
            <ChevronRight
              className={`h-5 w-5 transition-transform ${
                overallSelected
                  ? "rotate-90 text-ink-inverse"
                  : "text-ink-tertiary"
              }`}
              aria-hidden
            />
          </span>
        </div>
        <ScoreBar score={overall} size="lg" label="Overall validation score" />
      </button>

      {activeDetail && (
        <div id={`score-detail-${selectedId}`}>
          <ScoreDetailPanel
            detail={activeDetail}
            onClose={() => setSelectedId(null)}
          />
        </div>
      )}
    </section>
  );
}
