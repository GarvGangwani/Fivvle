import type { ValidationReport } from "./types";
import {
  buildOverallScoreDetail,
  buildSectionScoreDetails,
  type OverallScoreDetail,
  type SectionScoreDetail,
} from "./validation-report-score-details";
import { resolveReportScores, scoreTone } from "./validation-report-scores";

function escapeHtml(value: string): string {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function scoreBarHtml(score: number, size: "md" | "lg", label: string): string {
  const tone = scoreTone(score);
  return `<div class="report-score-bar-wrap" role="img" aria-label="${escapeHtml(`${label}: ${score} out of 100`)}">
  <div class="report-score-bar-track report-score-bar-${size}">
    <div class="report-score-bar-fill report-score-fill-${tone}" style="width:${score}%"></div>
  </div>
</div>`;
}

function chevronSvg(): string {
  return `<svg class="report-score-chevron" xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m9 18 6-6-6-6"/></svg>`;
}

function closeSvg(): string {
  return `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg>`;
}

function bulletListHtml(items: string[], variant: "pro" | "con"): string {
  if (items.length === 0) {
    const empty =
      variant === "pro" ? "No clear positives surfaced." : "No major caveats noted.";
    return `<p class="report-score-detail-empty">${escapeHtml(empty)}</p>`;
  }
  return `<ul class="report-score-detail-list report-score-detail-${variant}">${items
    .map((item) => `<li>${escapeHtml(item)}</li>`)
    .join("")}</ul>`;
}

function scoreDetailBodyHtml(
  detail: SectionScoreDetail | OverallScoreDetail,
): string {
  return `<div class="report-score-detail-body">
  <div class="report-score-detail-block">
    <p class="report-score-detail-label">Why this score</p>
    <p class="report-score-detail-text">${escapeHtml(detail.rationale)}</p>
  </div>
  <div class="report-score-detail-columns">
    <div class="report-score-detail-block">
      <p class="report-score-detail-label report-score-detail-label-pro">Supporting signals</p>
      ${bulletListHtml(detail.pros, "pro")}
    </div>
    <div class="report-score-detail-block">
      <p class="report-score-detail-label report-score-detail-label-con">Caveats &amp; gaps</p>
      ${bulletListHtml(detail.cons, "con")}
    </div>
  </div>
  <div class="report-score-detail-block">
    <p class="report-score-detail-label">Context from report</p>
    <p class="report-score-detail-context">${escapeHtml(detail.context)}</p>
  </div>
</div>`;
}

function scoreDetailPanelHtml(
  detail: SectionScoreDetail | OverallScoreDetail,
  scoreId: string,
): string {
  const tone = scoreTone(detail.score);
  const titleId = `score-detail-title-${scoreId}`;
  return `<div class="report-score-detail" role="region" aria-labelledby="${titleId}">
  <div class="report-score-detail-header">
    <div class="report-score-detail-heading">
      <p class="report-score-detail-eyebrow">Score breakdown</p>
      <h3 id="${titleId}" class="report-score-detail-title">${escapeHtml(detail.label)}</h3>
    </div>
    <span class="report-score-detail-value report-score-tone-${tone}">${detail.score}</span>
    <button type="button" class="report-score-detail-close" data-score-close aria-label="Close score details">
      ${closeSvg()}
    </button>
  </div>
  ${scoreBarHtml(detail.score, "md", detail.label)}
  ${scoreDetailBodyHtml(detail)}
</div>`;
}

function scoreCardHtml(detail: SectionScoreDetail): string {
  const tone = scoreTone(detail.score);
  const id = escapeHtml(detail.section_id);
  return `<button type="button" class="report-score-card report-score-card-btn" data-score-select="${id}" aria-expanded="false" aria-controls="score-detail-${id}">
  <div class="report-score-card-header">
    <p class="report-score-card-label">${escapeHtml(detail.label)}</p>
    <span class="report-score-card-meta">
      <span class="report-score-value report-score-tone-${tone}">${detail.score}</span>
      ${chevronSvg()}
    </span>
  </div>
  ${scoreBarHtml(detail.score, "md", detail.label)}
</button>`;
}

function overallScoreButtonHtml(detail: OverallScoreDetail): string {
  const tone = scoreTone(detail.score);
  return `<button type="button" class="report-score-overall report-score-overall-btn" data-score-select="overall" aria-expanded="false" aria-controls="score-detail-overall">
  <div class="report-score-overall-header">
    <p class="report-score-overall-label">${escapeHtml(detail.label)}</p>
    <span class="report-score-card-meta">
      <span class="report-score-overall-value report-score-tone-${tone}">${detail.score}</span>
      ${chevronSvg()}
    </span>
  </div>
  ${scoreBarHtml(detail.score, "lg", detail.label)}
</button>`;
}

function detailMountHtml(
  scoreId: string,
  detail: SectionScoreDetail | OverallScoreDetail,
): string {
  const safeId = escapeHtml(scoreId);
  return `<div id="score-detail-${safeId}" data-score-detail="${safeId}" class="report-score-detail-mount" hidden>
  ${scoreDetailPanelHtml(detail, safeId)}
</div>`;
}

/** Validation score panel HTML for standalone report downloads. */
export function buildScorePanelHtml(report: ValidationReport): string {
  const resolved = resolveReportScores(report);
  const sectionDetails = buildSectionScoreDetails(report, resolved.sections);
  const overallDetail = buildOverallScoreDetail(report, resolved.overall);

  const derivedNote = resolved.derived
    ? "Estimated from evidence · Tap a score for details"
    : "Tap a score for details";

  return `<section id="report-scores" class="report-score-panel" data-report-score-panel aria-labelledby="report-scores-heading">
  <div class="report-score-panel-header">
    <h2 id="report-scores-heading" class="report-score-panel-title">Validation scores</h2>
    <span class="report-score-derived-note">${escapeHtml(derivedNote)}</span>
  </div>
  <div class="report-score-grid">
    ${sectionDetails.map(scoreCardHtml).join("")}
  </div>
  ${overallScoreButtonHtml(overallDetail)}
  <div class="report-score-detail-slot">
    ${sectionDetails.map((detail) => detailMountHtml(detail.section_id, detail)).join("")}
    ${detailMountHtml("overall", overallDetail)}
  </div>
</section>`;
}
