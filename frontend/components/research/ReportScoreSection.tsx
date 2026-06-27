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
import "./report-score-section.css";

interface ReportScoreSectionProps {
  report: ValidationReport;
  sections: SectionScore[];
  overall: number;
  derived?: boolean;
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
  return (
    <div className="report-score-bar-wrap">
      <div
        className={`report-score-bar-track report-score-bar-${size}`}
        role="progressbar"
        aria-valuenow={score}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={`${label}: ${score} out of 100`}
      >
        <div
          className={`report-score-bar-fill report-score-fill-${tone}`}
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
      <p className="report-score-detail-empty">
        {variant === "pro" ? "No clear positives surfaced." : "No major caveats noted."}
      </p>
    );
  }
  return (
    <ul className={`report-score-detail-list report-score-detail-${variant}`}>
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
      className="report-score-detail"
      role="region"
      aria-labelledby={`score-detail-title-${id}`}
    >
      <div className="report-score-detail-header">
        <div className="min-w-0 flex-1">
          <p className="report-score-detail-eyebrow">Score breakdown</p>
          <h3
            id={`score-detail-title-${id}`}
            className="report-score-detail-title"
          >
            {detail.label}
          </h3>
        </div>
        <span className={`report-score-detail-value report-score-tone-${tone}`}>
          {detail.score}
        </span>
        <button
          type="button"
          onClick={onClose}
          className="report-score-detail-close"
          aria-label="Close score details"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      <ScoreBar score={detail.score} label={detail.label} />

      <div className="report-score-detail-body">
        <div className="report-score-detail-block">
          <p className="report-score-detail-label">Why this score</p>
          <p className="report-score-detail-text">{detail.rationale}</p>
        </div>

        <div className="report-score-detail-columns">
          <div className="report-score-detail-block">
            <p className="report-score-detail-label report-score-detail-label-pro">
              Supporting signals
            </p>
            <BulletList items={detail.pros} variant="pro" />
          </div>
          <div className="report-score-detail-block">
            <p className="report-score-detail-label report-score-detail-label-con">
              Caveats & gaps
            </p>
            <BulletList items={detail.cons} variant="con" />
          </div>
        </div>

        <div className="report-score-detail-block">
          <p className="report-score-detail-label">Context from report</p>
          <p className="report-score-detail-context">{detail.context}</p>
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
  return (
    <button
      type="button"
      onClick={onSelect}
      aria-expanded={selected}
      aria-controls={`score-detail-${detail.section_id}`}
      className={`report-score-card report-score-card-btn${selected ? " report-score-card-selected" : ""}`}
    >
      <div className="report-score-card-header">
        <p className="report-score-card-label">{detail.label}</p>
        <span className="report-score-card-meta">
          <span
            className={`report-score-value report-score-tone-${scoreTone(detail.score)}`}
          >
            {detail.score}
          </span>
          <ChevronRight
            className={`report-score-chevron${selected ? " report-score-chevron-open" : ""}`}
            aria-hidden
          />
        </span>
      </div>
      <ScoreBar score={detail.score} label={detail.label} />
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
        ? sectionDetails.find((d) => d.section_id === selectedId) ?? null
        : null;

  function toggleSelection(id: ScoreSelectionId) {
    setSelectedId((current) => (current === id ? null : id));
  }

  return (
    <section
      id="report-scores"
      className="report-score-panel"
      aria-labelledby="report-scores-heading"
    >
      <div className="report-score-panel-header">
        <h2 id="report-scores-heading" className="report-score-panel-title">
          Validation scores
        </h2>
        <span className="report-score-derived-note">
          {derived ? "Estimated from evidence · " : ""}
          Tap a score for details
        </span>
      </div>

      <div className="report-score-grid">
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
        aria-expanded={selectedId === "overall"}
        className={`report-score-overall report-score-overall-btn${
          selectedId === "overall" ? " report-score-card-selected" : ""
        }`}
      >
        <div className="report-score-overall-header">
          <p className="report-score-overall-label">Overall score</p>
          <span className="report-score-card-meta">
            <span
              className={`report-score-overall-value report-score-tone-${scoreTone(overall)}`}
            >
              {overall}
            </span>
            <ChevronRight
              className={`report-score-chevron${selectedId === "overall" ? " report-score-chevron-open" : ""}`}
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
