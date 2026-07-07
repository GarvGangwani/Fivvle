import {
  parseRiskAssessment,
  questionDisplayIndex,
  splitReadableParagraphs,
} from "./report-text";
import type {
  Citation,
  Finding,
  OverallRecommendation,
  ValidationReport,
} from "./types";
import {
  VALIDATION_REPORT_HTML_CSS,
  VALIDATION_REPORT_SCORE_HTML_CSS,
  VALIDATION_REPORT_SCORE_SCRIPT,
  VALIDATION_REPORT_THEME_SCRIPT,
} from "./validation-report-html-styles";
import { buildScorePanelHtml } from "./validation-report-score-html";
import { resolveQuestionScore, resolveReportScores } from "./validation-report-scores";

function slugifyFilename(name: string): string {
  const slug = name
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
  return slug.slice(0, 60) || "validation-report";
}

function escapeHtml(value: string): string {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function escapeAttr(value: string): string {
  return escapeHtml(value);
}

function formatRecommendation(rec: OverallRecommendation): string {
  if (rec === "too_vague_to_recommend") return "Needs clarity";
  return rec.charAt(0).toUpperCase() + rec.slice(1);
}

function recommendationBadgeClass(rec: OverallRecommendation): string {
  switch (rec) {
    case "proceed":
      return "badge-proceed";
    case "iterate":
      return "badge-iterate";
    case "pivot":
      return "badge-pivot";
    case "kill":
      return "badge-kill";
    default:
      return "badge-iterate";
  }
}

function confidenceClass(confidence: string): string {
  if (confidence === "high") return "fv-confidence-high";
  if (confidence === "medium") return "fv-confidence-medium";
  return "fv-confidence-low";
}

function findingAccentClass(confidence: string): string {
  if (confidence === "high") return "report-finding-high";
  if (confidence === "medium") return "report-finding-medium";
  return "report-finding-low";
}

function isSafeHttpUrl(url: string): boolean {
  return url.startsWith("http://") || url.startsWith("https://");
}

function collectAllCitations(report: ValidationReport): Citation[] {
  const seen = new Set<string>();
  const citations: Citation[] = [];

  const add = (citation: Citation) => {
    const key = citation.url || citation.title;
    if (!seen.has(key)) {
      seen.add(key);
      citations.push(citation);
    }
  };

  for (const qf of report.questions_and_findings) {
    for (const finding of qf.findings) {
      for (const citation of finding.citations) {
        add(citation);
      }
    }
  }
  for (const comp of report.competitors) {
    for (const citation of comp.citations) {
      add(citation);
    }
  }

  return citations;
}

function buildCitationIndexMap(citations: Citation[]): Map<string, number> {
  const map = new Map<string, number>();
  citations.forEach((citation, index) => {
    map.set(citation.url || citation.title, index + 1);
  });
  return map;
}

function countFindings(report: ValidationReport): number {
  return report.questions_and_findings.reduce(
    (total, qf) => total + qf.findings.length,
    0,
  );
}

function proseHtml(text: string, maxChars = 380): string {
  const paragraphs = splitReadableParagraphs(text, maxChars);
  if (paragraphs.length === 0) return "";
  return `<div class="report-prose">${paragraphs
    .map((paragraph) => `<p>${escapeHtml(paragraph)}</p>`)
    .join("")}</div>`;
}

function citationRefsHtml(
  citations: Citation[],
  citationIndexMap: Map<string, number>,
): string {
  return citations
    .map((citation) => {
      const key = citation.url || citation.title;
      const index = citationIndexMap.get(key);
      if (!index) return "";
      return `<a href="#citation-${index}" class="report-cite-ref" title="${escapeAttr(citation.title)}">[${index}]</a>`;
    })
    .join("");
}

function findingHtml(
  finding: Finding,
  findingIndex: number,
  citationIndexMap: Map<string, number>,
): string {
  const evidenceParagraphs = splitReadableParagraphs(
    finding.evidence_summary,
    420,
  );

  const evidenceHtml =
    evidenceParagraphs.length > 0
      ? `<div class="report-finding-evidence">${evidenceParagraphs
          .map((paragraph, index) => {
            const refs =
              index === evidenceParagraphs.length - 1
                ? citationRefsHtml(finding.citations, citationIndexMap)
                : "";
            return `<p>${escapeHtml(paragraph)}${refs}</p>`;
          })
          .join("")}</div>`
      : "";

  const rationaleHtml = finding.confidence_rationale
    ? `<p class="report-finding-rationale">${escapeHtml(finding.confidence_rationale)}</p>`
    : "";

  return `<article class="report-finding ${findingAccentClass(finding.confidence)}">
  <div class="report-finding-header">
    <span class="report-finding-index">Finding ${findingIndex}</span>
    <span class="fv-confidence-badge ${confidenceClass(finding.confidence)}">${escapeHtml(finding.confidence)} confidence</span>
  </div>
  <p class="report-finding-claim">${escapeHtml(finding.claim)}</p>
  ${evidenceHtml}
  ${rationaleHtml}
</article>`;
}

function riskSectionHtml(text: string): string {
  const parsed = parseRiskAssessment(text);
  if (!parsed.isStructured) {
    return proseHtml(text);
  }

  const preambleHtml = parsed.preamble
    ? `<div class="report-risk-preamble">${splitReadableParagraphs(parsed.preamble, 420)
        .map((paragraph) => `<p>${escapeHtml(paragraph)}</p>`)
        .join("")}</div>`
    : "";

  const itemsHtml = parsed.items
    .map(
      (risk) => `<li class="report-risk-item">
  <div class="report-risk-header">
    <span class="report-risk-num">${risk.number}</span>
    <div>
      <h3 class="report-risk-title">${escapeHtml(risk.title)}</h3>
      ${risk.verdict ? `<span class="report-risk-verdict">${escapeHtml(risk.verdict)}</span>` : ""}
    </div>
  </div>
  ${
    risk.body
      ? `<div class="report-risk-body">${splitReadableParagraphs(risk.body, 420)
          .map((paragraph) => `<p>${escapeHtml(paragraph)}</p>`)
          .join("")}</div>`
      : ""
  }
</li>`,
    )
    .join("");

  return `${preambleHtml}<ol class="report-risk-list">${itemsHtml}</ol>`;
}

const ICONS = {
  trend: `<svg viewBox="0 0 24 24" aria-hidden="true"><polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/><polyline points="17 6 23 6 23 12"/></svg>`,
  book: `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg>`,
  file: `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>`,
  building: `<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="4" y="2" width="16" height="20" rx="2"/><path d="M9 22v-4h6v4"/><path d="M8 6h.01"/><path d="M16 6h.01"/><path d="M12 6h.01"/><path d="M12 10h.01"/><path d="M12 14h.01"/><path d="M16 10h.01"/><path d="M16 14h.01"/><path d="M8 10h.01"/><path d="M8 14h.01"/></svg>`,
  alert: `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>`,
  link: `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>`,
} as const;

function sectionTitle(id: string, icon: string, label: string): string {
  return `<h2 id="${id}" class="report-block-title"><span class="report-block-icon">${icon}</span>${escapeHtml(label)}</h2>`;
}

function buildSectionNav(report: ValidationReport, citationCount: number): string {
  const links: { href: string; label: string }[] = [];

  if (
    report.overall_recommendation !== "too_vague_to_recommend" &&
    report.recommendation_rationale
  ) {
    links.push({ href: "#report-recommendation", label: "Recommendation" });
  }
  links.push(
    { href: "#report-scores", label: "Scores" },
    { href: "#report-summary", label: "Summary" },
    { href: "#report-findings", label: "Findings" },
  );
  if (report.competitors.length > 0) {
    links.push({ href: "#report-competitors", label: "Competitors" });
  }
  if (
    report.market_signals ||
    report.distribution_signals ||
    report.regulatory_signals
  ) {
    links.push({ href: "#report-market", label: "Market" });
  }
  if (report.risks_assessment) {
    links.push({ href: "#report-risks", label: "Risks" });
  }
  if (citationCount > 0) {
    links.push({ href: "#report-sources", label: "Sources" });
  }

  return `<nav class="report-section-nav" aria-label="Report sections">
  <div class="report-section-nav-inner">
    ${links
      .map(
        (link) =>
          `<a href="${link.href}" class="report-section-link">${escapeHtml(link.label)}</a>`,
      )
      .join("")}
  </div>
</nav>`;
}

export function buildValidationReportHtml(
  report: ValidationReport,
  projectName: string,
  initialTheme: "light" | "dark" = "dark",
): string {
  const citations = collectAllCitations(report);
  const citationIndexMap = buildCitationIndexMap(citations);
  const showRecommendation =
    report.overall_recommendation !== "too_vague_to_recommend";
  const questionCount = report.questions_and_findings.length;
  const findingCount = countFindings(report);
  const exportedAt = new Date().toLocaleString(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  });

  const recommendationSection =
    showRecommendation && report.recommendation_rationale
      ? `<section id="report-recommendation" class="report-block">
  ${sectionTitle("report-recommendation-heading", ICONS.trend, "Recommendation")}
  <div class="report-card report-card-accent">${proseHtml(report.recommendation_rationale)}</div>
</section>`
      : "";

  const findingsHtml = report.questions_and_findings
    .map((qf, qIndex) => {
      const displayIndex = questionDisplayIndex(qf.question_id, qIndex + 1);
      const qScore = resolveQuestionScore(qf);
      const findings = qf.findings
        .map((finding, fIndex) =>
          findingHtml(finding, fIndex + 1, citationIndexMap),
        )
        .join("");
      const evidenceGapHtml = qf.evidence_gap
        ? `<div class="report-evidence-gap"><strong>Evidence gap: </strong>${escapeHtml(qf.evidence_gap)}</div>`
        : "";

      return `<div class="report-question">
  <div class="report-question-header">
    <div class="report-question-meta">
      <span class="report-question-index">${displayIndex}</span>
      <span class="report-question-label">Research question</span>
      <span class="report-question-count">· ${qf.findings.length} finding${qf.findings.length === 1 ? "" : "s"}</span>
      <span class="report-question-score" title="Question score">${qScore}</span>
    </div>
    <p class="report-question-title">${escapeHtml(qf.question)}</p>
  </div>
  <div class="report-question-body">
    ${findings}
    ${evidenceGapHtml}
  </div>
</div>`;
    })
    .join("");

  const competitorsHtml =
    report.competitors.length > 0
      ? `<section id="report-competitors" class="report-block">
  ${sectionTitle("report-competitors-heading", ICONS.building, "Competitors")}
  <div class="report-competitor-grid">
    ${report.competitors
      .map(
        (comp) => `<div class="report-competitor-card">
      <h3 class="report-competitor-name">${escapeHtml(comp.name)}</h3>
      ${proseHtml(comp.description, 320)}
      ${
        comp.positioning_vs_idea
          ? `<p class="report-competitor-vs"><strong>vs. your idea:</strong> ${escapeHtml(comp.positioning_vs_idea)}</p>`
          : ""
      }
    </div>`,
      )
      .join("")}
  </div>
</section>`
      : "";

  const marketSignals: string[] = [];
  if (report.market_signals) {
    marketSignals.push(`<div class="report-signal-block">
  <h3 class="report-signal-label">Market overview</h3>
  ${proseHtml(report.market_signals)}
</div>`);
  }
  if (report.distribution_signals) {
    marketSignals.push(`<div class="report-signal-block">
  <h3 class="report-signal-label">Distribution</h3>
  ${proseHtml(report.distribution_signals)}
</div>`);
  }
  if (report.regulatory_signals) {
    marketSignals.push(`<div class="report-signal-block">
  <h3 class="report-signal-label">Regulatory</h3>
  ${proseHtml(report.regulatory_signals)}
</div>`);
  }

  const marketHtml =
    marketSignals.length > 0
      ? `<section id="report-market" class="report-block">
  ${sectionTitle("report-market-heading", ICONS.trend, "Market signals")}
  <div class="report-card">${marketSignals.join("")}</div>
</section>`
      : "";

  const risksHtml = report.risks_assessment
    ? `<section id="report-risks" class="report-block">
  ${sectionTitle("report-risks-heading", ICONS.alert, "Risk assessment")}
  <div class="report-card report-card-warning-border">${riskSectionHtml(report.risks_assessment)}</div>
</section>`
    : "";

  const limitationsHtml = report.research_limitations
    ? `<section class="report-block">
  ${sectionTitle("report-limitations-heading", ICONS.alert, "Research limitations")}
  <div class="report-card">${proseHtml(report.research_limitations)}</div>
</section>`
    : "";

  const sourcesHtml =
    citations.length > 0
      ? `<section id="report-sources" class="report-block">
  ${sectionTitle("report-sources-heading", ICONS.link, `Sources (${citations.length})`)}
  <ol class="report-source-list">
    ${citations
      .map((citation, index) => {
        const title = citation.title || citation.url || "Source";
        const linkHtml = isSafeHttpUrl(citation.url)
          ? `<a class="report-source-link" href="${escapeAttr(citation.url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(title)}</a>`
          : `<span>${escapeHtml(title)}</span>`;
        const domainHtml = citation.source_domain
          ? `<p class="report-source-domain">${escapeHtml(citation.source_domain)}</p>`
          : "";
        return `<li id="citation-${index + 1}" class="report-source-item">
      <span class="report-source-num">${index + 1}</span>
      <div>${linkHtml}${domainHtml}</div>
    </li>`;
      })
      .join("")}
  </ol>
</section>`
      : "";

  const badgeHtml = showRecommendation
    ? `<div style="margin-top:1rem"><span class="report-recommendation-badge ${recommendationBadgeClass(report.overall_recommendation)}">${escapeHtml(formatRecommendation(report.overall_recommendation))}</span></div>`
    : "";

  const lightActive = initialTheme === "light";
  const themeBootScript = `(function(){try{var t=localStorage.getItem("fivvle-report-theme");if(t!=="light"&&t!=="dark"){t="${initialTheme}";}document.documentElement.setAttribute("data-theme",t==="light"?"light":"dark");}catch(e){document.documentElement.setAttribute("data-theme","${initialTheme}");}})();`;

  return `<!DOCTYPE html>
<html lang="en" data-theme="${initialTheme}">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>${escapeHtml(projectName)} — Validation Report</title>
  <script>${themeBootScript}</script>
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet" />
  <style>${VALIDATION_REPORT_HTML_CSS}${VALIDATION_REPORT_SCORE_HTML_CSS}</style>
</head>
<body>
  <div class="report-page">
    <div class="report-export-header">
      <span class="report-export-brand">Fivvle</span>
      <div class="report-export-header-actions">
        <div class="report-theme-toggle" role="group" aria-label="Report theme">
          <button type="button" class="report-theme-btn${lightActive ? " report-theme-btn-active" : ""}" data-theme-btn="light" aria-pressed="${lightActive ? "true" : "false"}">Light</button>
          <button type="button" class="report-theme-btn${lightActive ? "" : " report-theme-btn-active"}" data-theme-btn="dark" aria-pressed="${lightActive ? "false" : "true"}">Dark</button>
        </div>
        <span class="report-export-date">Exported ${escapeHtml(exportedAt)}</span>
      </div>
    </div>
    <article class="report-canvas-article">
      <header class="report-masthead">
        <p class="report-masthead-eyebrow">Validation report</p>
        <h1 class="report-masthead-title">${escapeHtml(projectName)}</h1>
        ${badgeHtml}
        <div class="report-stats">
          <span class="report-stat-pill"><strong>${questionCount}</strong> research questions</span>
          <span class="report-stat-pill"><strong>${findingCount}</strong> findings</span>
          <span class="report-stat-pill"><strong>${citations.length}</strong> sources</span>
        </div>
      </header>

      ${buildScorePanelHtml(report)}

      ${buildSectionNav(report, citations.length)}

      ${recommendationSection}

      <section id="report-summary" class="report-block">
        ${sectionTitle("report-summary-heading", ICONS.book, "Executive summary")}
        <div class="report-card">${proseHtml(report.executive_summary)}</div>
      </section>

      <section id="report-findings" class="report-block">
        ${sectionTitle("report-findings-heading", ICONS.file, "Research findings")}
        ${findingsHtml}
      </section>

      ${competitorsHtml}
      ${marketHtml}
      ${risksHtml}
      ${limitationsHtml}
      ${sourcesHtml}

      <p class="report-footer-note">Generated by Fivvle research engine · Rubric ${escapeHtml(report.rubric_version_used)}</p>
    </article>
  </div>
  <script>${VALIDATION_REPORT_THEME_SCRIPT}</script>
  <script>${VALIDATION_REPORT_SCORE_SCRIPT}</script>
</body>
</html>`;
}

function downloadHtmlFile(html: string, filename: string): void {
  const blob = new Blob([html], { type: "text/html;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

function resolveDownloadTheme(): "light" | "dark" {
  if (typeof document === "undefined") return "dark";
  const theme = document.documentElement.getAttribute("data-theme");
  return theme === "light" ? "light" : "dark";
}

export function downloadValidationReportHtml(
  report: ValidationReport,
  projectName = "validation-report",
): void {
  const html = buildValidationReportHtml(
    report,
    projectName,
    resolveDownloadTheme(),
  );
  downloadHtmlFile(
    html,
    `${slugifyFilename(projectName)}-validation-report.html`,
  );
}

function escapeMarkdownInline(value: string): string {
  return value.replace(/\\/g, "\\\\").replace(/`/g, "\\`").replace(/\[/g, "\\[");
}

function markdownCitationLink(citation: Citation): string {
  const label = citation.title || citation.url || "Source";
  if (isSafeHttpUrl(citation.url)) {
    return `[${escapeMarkdownInline(label)}](${citation.url})`;
  }
  return escapeMarkdownInline(label);
}

function markdownParagraphs(text: string, maxChars = 380): string {
  const paragraphs = splitReadableParagraphs(text, maxChars);
  if (paragraphs.length === 0) return "";
  return paragraphs.map((paragraph) => `${paragraph}\n`).join("\n");
}

function markdownFinding(
  finding: Finding,
  findingIndex: number,
  citationIndexMap: Map<string, number>,
): string {
  const lines: string[] = [
    `#### Finding ${findingIndex} (${finding.confidence} confidence)`,
    "",
    finding.claim,
    "",
  ];

  const evidenceParagraphs = splitReadableParagraphs(finding.evidence_summary, 420);
  if (evidenceParagraphs.length > 0) {
    lines.push("**Evidence**", "");
    for (const paragraph of evidenceParagraphs) {
      lines.push(paragraph, "");
    }
  }

  if (finding.citations.length > 0) {
    const refs = finding.citations
      .map((citation) => {
        const key = citation.url || citation.title;
        const index = citationIndexMap.get(key);
        if (index) return `[${index}]`;
        return null;
      })
      .filter((ref): ref is string => ref !== null);
    if (refs.length > 0) {
      lines.push(`Sources: ${refs.join(", ")}`, "");
    }
  }

  if (finding.confidence_rationale) {
    lines.push(`*${finding.confidence_rationale}*`, "");
  }

  return lines.join("\n");
}

function markdownRiskSection(text: string): string {
  const parsed = parseRiskAssessment(text);
  if (!parsed.isStructured) {
    return markdownParagraphs(text);
  }

  const lines: string[] = [];
  if (parsed.preamble) {
    lines.push(markdownParagraphs(parsed.preamble), "");
  }

  for (const risk of parsed.items) {
    lines.push(`### Risk ${risk.number}: ${risk.title}`);
    if (risk.verdict) {
      lines.push(`**${risk.verdict}**`, "");
    }
    if (risk.body) {
      lines.push(markdownParagraphs(risk.body), "");
    }
  }

  return lines.join("\n");
}

function markdownScoresSection(report: ValidationReport): string {
  const { sections, overall } = resolveReportScores(report);
  const lines = [
    "## Scores",
    "",
    `**Overall score:** ${overall}/100`,
    "",
    "| Section | Score |",
    "| --- | ---: |",
    ...sections.map((section) => `| ${section.label} | ${section.score} |`),
    "",
  ];
  return lines.join("\n");
}

export function buildValidationReportMarkdown(
  report: ValidationReport,
  projectName: string,
): string {
  const citations = collectAllCitations(report);
  const citationIndexMap = buildCitationIndexMap(citations);
  const showRecommendation =
    report.overall_recommendation !== "too_vague_to_recommend";
  const questionCount = report.questions_and_findings.length;
  const findingCount = countFindings(report);
  const exportedAt = new Date().toLocaleString(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  });

  const lines: string[] = [
    `# ${projectName} — Validation Report`,
    "",
    `*Exported ${exportedAt} · Generated by Fivvle research engine · Rubric ${report.rubric_version_used}*`,
    "",
  ];

  if (showRecommendation) {
    lines.push(
      `**Recommendation:** ${formatRecommendation(report.overall_recommendation)}`,
      "",
    );
  }

  lines.push(
    `- **${questionCount}** research questions`,
    `- **${findingCount}** findings`,
    `- **${citations.length}** sources`,
    "",
  );

  lines.push(markdownScoresSection(report));

  if (showRecommendation && report.recommendation_rationale) {
    lines.push("## Recommendation", "", markdownParagraphs(report.recommendation_rationale), "");
  }

  lines.push("## Executive summary", "", markdownParagraphs(report.executive_summary), "");

  lines.push("## Research findings", "");

  for (const [qIndex, qf] of report.questions_and_findings.entries()) {
    const displayIndex = questionDisplayIndex(qf.question_id, qIndex + 1);
    const qScore = resolveQuestionScore(qf);
    lines.push(
      `### ${displayIndex}: ${qf.question}`,
      "",
      `*Score: ${qScore}/100 · ${qf.findings.length} finding${qf.findings.length === 1 ? "" : "s"}*`,
      "",
    );

    for (const [fIndex, finding] of qf.findings.entries()) {
      lines.push(markdownFinding(finding, fIndex + 1, citationIndexMap));
    }

    if (qf.evidence_gap) {
      lines.push(`> **Evidence gap:** ${qf.evidence_gap}`, "");
    }
  }

  if (report.competitors.length > 0) {
    lines.push("## Competitors", "");
    for (const comp of report.competitors) {
      lines.push(`### ${comp.name}`, "", markdownParagraphs(comp.description, 320));
      if (comp.positioning_vs_idea) {
        lines.push("", `**vs. your idea:** ${comp.positioning_vs_idea}`, "");
      }
      if (comp.citations.length > 0) {
        lines.push(
          "Sources:",
          ...comp.citations.map((citation) => `- ${markdownCitationLink(citation)}`),
          "",
        );
      }
    }
  }

  const marketBlocks: string[] = [];
  if (report.market_signals) {
    marketBlocks.push("### Market overview", "", markdownParagraphs(report.market_signals), "");
  }
  if (report.distribution_signals) {
    marketBlocks.push("### Distribution", "", markdownParagraphs(report.distribution_signals), "");
  }
  if (report.regulatory_signals) {
    marketBlocks.push("### Regulatory", "", markdownParagraphs(report.regulatory_signals), "");
  }
  if (marketBlocks.length > 0) {
    lines.push("## Market signals", "", ...marketBlocks);
  }

  if (report.risks_assessment) {
    lines.push("## Risk assessment", "", markdownRiskSection(report.risks_assessment), "");
  }

  if (report.research_limitations) {
    lines.push(
      "## Research limitations",
      "",
      markdownParagraphs(report.research_limitations),
      "",
    );
  }

  if (citations.length > 0) {
    lines.push(`## Sources (${citations.length})`, "");
    for (const [index, citation] of citations.entries()) {
      const link = markdownCitationLink(citation);
      const domain = citation.source_domain ? ` — ${citation.source_domain}` : "";
      lines.push(`${index + 1}. ${link}${domain}`);
    }
    lines.push("");
  }

  return lines.join("\n").trimEnd() + "\n";
}

function downloadMarkdownFile(markdown: string, filename: string): void {
  const blob = new Blob([markdown], { type: "text/markdown;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

export function downloadValidationReportMarkdown(
  report: ValidationReport,
  projectName = "validation-report",
): void {
  const markdown = buildValidationReportMarkdown(report, projectName);
  downloadMarkdownFile(
    markdown,
    `${slugifyFilename(projectName)}-validation-report.md`,
  );
}
