"use client";

import { useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  ArrowLeft,
  BookOpen,
  Building2,
  ChevronDown,
  Download,
  ExternalLink,
  FileText,
  Maximize2,
  Minimize2,
  TrendingUp,
  X,
} from "lucide-react";
import { getValidationReport } from "@/lib/api";
import {
  parseRiskAssessment,
  questionDisplayIndex,
  splitReadableParagraphs,
} from "@/lib/report-text";
import { downloadValidationReportHtml } from "@/lib/validation-report-export";
import {
  resolveQuestionScore,
  resolveReportScores,
} from "@/lib/validation-report-scores";
import type {
  Citation,
  Finding,
  OverallRecommendation,
  ValidationReport,
} from "@/lib/types";
import { ErrorBanner } from "@/components/ui/ErrorBanner";
import { LoadingState } from "@/components/ui/LoadingState";
import { ReportScoreSection } from "@/components/research/ReportScoreSection";
import "./report-canvas.css";

function isSafeHttpUrl(url: string): boolean {
  return url.startsWith("http://") || url.startsWith("https://");
}

function SafeCitationLink({ citation }: { citation: Citation }) {
  if (!isSafeHttpUrl(citation.url)) {
    return <span className="text-[var(--fv-text)]">{citation.title}</span>;
  }
  return (
    <a
      href={citation.url}
      target="_blank"
      rel="noopener noreferrer"
      className="inline-flex items-center gap-1 text-[var(--fv-accent)] no-underline hover:underline"
    >
      {citation.title}
      <ExternalLink className="h-3 w-3 opacity-60" />
    </a>
  );
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
      return "unavailable-badge";
  }
}

function formatRecommendation(rec: OverallRecommendation): string {
  if (rec === "too_vague_to_recommend") return "Needs clarity";
  return rec.charAt(0).toUpperCase() + rec.slice(1);
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

function collectAllCitations(report: ValidationReport): Citation[] {
  const seen = new Set<string>();
  const citations: Citation[] = [];
  for (const qf of report.questions_and_findings) {
    for (const finding of qf.findings) {
      for (const c of finding.citations) {
        const key = c.url || c.title;
        if (!seen.has(key)) {
          seen.add(key);
          citations.push(c);
        }
      }
    }
  }
  for (const comp of report.competitors) {
    for (const c of comp.citations) {
      const key = c.url || c.title;
      if (!seen.has(key)) {
        seen.add(key);
        citations.push(c);
      }
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

function ReadableProse({ text }: { text: string }) {
  const paragraphs = splitReadableParagraphs(text);
  return (
    <div className="report-prose">
      {paragraphs.map((paragraph, index) => (
        <p key={index}>{paragraph}</p>
      ))}
    </div>
  );
}

function RiskAssessmentContent({ text }: { text: string }) {
  const parsed = parseRiskAssessment(text);

  if (!parsed.isStructured) {
    return <ReadableProse text={text} />;
  }

  return (
    <div>
      {parsed.preamble && (
        <div className="report-risk-preamble">
          {splitReadableParagraphs(parsed.preamble, 420).map((paragraph, index) => (
            <p key={index} className={index > 0 ? "mt-2" : undefined}>
              {paragraph}
            </p>
          ))}
        </div>
      )}
      <ol className="report-risk-list">
        {parsed.items.map((risk) => (
          <li key={risk.number} className="report-risk-item">
            <div className="report-risk-header">
              <span className="report-risk-num" aria-hidden="true">
                {risk.number}
              </span>
              <div className="report-risk-heading">
                <h3 className="report-risk-title">{risk.title}</h3>
                {risk.verdict && (
                  <span className="report-risk-verdict">{risk.verdict}</span>
                )}
              </div>
            </div>
            {risk.body && (
              <div className="report-risk-body">
                {splitReadableParagraphs(risk.body, 420).map((paragraph, index) => (
                  <p key={index}>{paragraph}</p>
                ))}
              </div>
            )}
          </li>
        ))}
      </ol>
    </div>
  );
}

function CitationRefs({
  citations,
  citationIndexMap,
}: {
  citations: Citation[];
  citationIndexMap: Map<string, number>;
}) {
  if (citations.length === 0) return null;
  return (
    <>
      {citations.map((citation) => {
        const key = citation.url || citation.title;
        const index = citationIndexMap.get(key);
        if (!index) return null;
        return (
          <a
            key={key}
            href={`#citation-${index}`}
            className="report-cite-ref"
            title={citation.title}
          >
            [{index}]
          </a>
        );
      })}
    </>
  );
}

function FindingCard({
  finding,
  findingIndex,
  citationIndexMap,
}: {
  finding: Finding;
  findingIndex: number;
  citationIndexMap: Map<string, number>;
}) {
  const evidenceParagraphs = splitReadableParagraphs(
    finding.evidence_summary,
    420,
  );

  return (
    <article
      className={`report-finding ${findingAccentClass(finding.confidence)}`}
    >
      <div className="report-finding-header">
        <span className="report-finding-index">Finding {findingIndex}</span>
        <span
          className={`fv-confidence-badge ${confidenceClass(finding.confidence)}`}
        >
          {finding.confidence} confidence
        </span>
      </div>
      <p className="report-finding-claim">{finding.claim}</p>
      {evidenceParagraphs.length > 0 && (
        <div className="report-finding-evidence">
          {evidenceParagraphs.map((paragraph, index) => (
            <p key={index} className={index > 0 ? "mt-2" : undefined}>
              {paragraph}
              {index === evidenceParagraphs.length - 1 && (
                <CitationRefs
                  citations={finding.citations}
                  citationIndexMap={citationIndexMap}
                />
              )}
            </p>
          ))}
        </div>
      )}
      {finding.confidence_rationale && (
        <p className="mt-2 text-xs leading-relaxed text-[var(--fv-text-muted)]">
          {finding.confidence_rationale}
        </p>
      )}
    </article>
  );
}

export interface ReportCanvasProps {
  experimentId: string;
  projectName?: string;
  onClose?: () => void;
  /** Embedded in experiment page — no chrome header with close. */
  embedded?: boolean;
  mobile?: boolean;
}

export function ReportCanvas({
  experimentId,
  projectName = "Validation report",
  onClose,
  embedded = false,
  mobile = false,
}: ReportCanvasProps) {
  const [report, setReport] = useState<ValidationReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [fullscreen, setFullscreen] = useState(false);
  const [expandedQuestions, setExpandedQuestions] = useState<Set<string>>(
    new Set(),
  );

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const data = await getValidationReport(experimentId);
        if (!cancelled) {
          setReport(data);
          const firstQuestionId = data.questions_and_findings[0]?.question_id;
          setExpandedQuestions(
            firstQuestionId ? new Set([firstQuestionId]) : new Set(),
          );
        }
      } catch {
        if (!cancelled) {
          setError("Could not load the validation report.");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, [experimentId]);

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key !== "Escape") return;
      if (fullscreen) {
        setFullscreen(false);
        return;
      }
      onClose?.();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose, fullscreen]);

  useEffect(() => {
    if (!fullscreen) return;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = previousOverflow;
    };
  }, [fullscreen]);

  const citations = report ? collectAllCitations(report) : [];
  const citationIndexMap = buildCitationIndexMap(citations);
  const reportScores = report ? resolveReportScores(report) : null;
  const showRecommendation =
    report && report.overall_recommendation !== "too_vague_to_recommend";

  const sectionLinks = useMemo(() => {
    if (!report) return [];
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
    if (citations.length > 0) {
      links.push({ href: "#report-sources", label: "Sources" });
    }
    return links;
  }, [report, citations.length]);

  const allQuestionsExpanded =
    report !== null &&
    report.questions_and_findings.length > 0 &&
    report.questions_and_findings.every((qf) =>
      expandedQuestions.has(qf.question_id),
    );

  function handleDownload() {
    if (!report) return;
    downloadValidationReportHtml(report, projectName);
  }

  function toggleQuestion(qid: string) {
    setExpandedQuestions((prev) => {
      const next = new Set(prev);
      if (next.has(qid)) next.delete(qid);
      else next.add(qid);
      return next;
    });
  }

  function toggleAllQuestions() {
    if (!report) return;
    if (allQuestionsExpanded) {
      setExpandedQuestions(new Set());
      return;
    }
    setExpandedQuestions(
      new Set(report.questions_and_findings.map((qf) => qf.question_id)),
    );
  }

  const showOverlayHeader = !embedded || fullscreen;
  const showEmbeddedToolbar = embedded && !fullscreen && report && !loading;
  const findingCount = report ? countFindings(report) : 0;
  const questionCount = report?.questions_and_findings.length ?? 0;

  return (
    <div
      className={`flex min-h-0 flex-col bg-[var(--fv-bg)] ${
        fullscreen ? "fixed inset-0 z-[80] h-dvh max-h-dvh" : "h-full"
      }`}
    >
      {showEmbeddedToolbar && (
        <div className="flex shrink-0 items-center justify-end gap-2 border-b border-[var(--fv-border)] bg-[var(--fv-surface)]/80 px-4 py-2 backdrop-blur-sm">
          <button
            type="button"
            onClick={handleDownload}
            className="fv-btn-ghost inline-flex items-center gap-1.5 px-3 py-1.5 text-[12px]"
          >
            <Download className="h-3.5 w-3.5" />
            Download
          </button>
          <button
            type="button"
            onClick={() => setFullscreen(true)}
            className="fv-btn-ghost inline-flex items-center gap-1.5 px-3 py-1.5 text-[12px]"
          >
            <Maximize2 className="h-3.5 w-3.5" />
            Full screen
          </button>
        </div>
      )}

      {showOverlayHeader && (
        <header className="sticky top-0 z-10 flex shrink-0 items-center justify-between gap-3 border-b border-[var(--fv-border)] bg-[var(--fv-bg)]/95 px-4 py-3 backdrop-blur-sm sm:px-6">
          <div className="flex min-w-0 items-center gap-3">
            {mobile && onClose && !fullscreen && (
              <button
                type="button"
                onClick={onClose}
                className="fv-icon-btn shrink-0 lg:hidden"
                aria-label="Back"
              >
                <ArrowLeft className="h-4 w-4" />
              </button>
            )}
            <FileText className="h-5 w-5 shrink-0 text-[var(--fv-accent)]" />
            <h1 className="truncate text-base font-semibold text-[var(--fv-text)]">
              Validation Report
            </h1>
          </div>
          <div className="flex shrink-0 items-center gap-1">
            {report && (
              <button
                type="button"
                onClick={handleDownload}
                className="fv-btn-ghost inline-flex items-center gap-1.5 px-2.5 py-1.5 text-[12px] sm:px-3"
                aria-label="Download report"
              >
                <Download className="h-3.5 w-3.5" />
                <span className="hidden sm:inline">Download</span>
              </button>
            )}
            {fullscreen ? (
              <button
                type="button"
                onClick={() => setFullscreen(false)}
                className="fv-btn-ghost inline-flex items-center gap-1.5 px-2.5 py-1.5 text-[12px] sm:px-3"
                aria-label="Exit full screen"
              >
                <Minimize2 className="h-3.5 w-3.5" />
                <span className="hidden sm:inline">Exit full screen</span>
              </button>
            ) : embedded ? null : (
              <button
                type="button"
                onClick={() => setFullscreen(true)}
                className="fv-icon-btn"
                aria-label="View full screen"
                title="View full screen"
              >
                <Maximize2 className="h-4 w-4" />
              </button>
            )}
            {onClose && !fullscreen && (
              <button
                type="button"
                onClick={onClose}
                className="fv-icon-btn shrink-0"
                aria-label="Close report"
              >
                <X className="h-4 w-4" />
              </button>
            )}
          </div>
        </header>
      )}

      <div className="min-h-0 flex-1 overflow-y-auto">
        <div className="mx-auto max-w-3xl px-3 py-4 sm:px-5 sm:py-6">
          {loading && <LoadingState label="Loading validation report…" />}

          {error && !loading && <ErrorBanner message={error} />}

          {report && !loading && (
            <article className="report-canvas-article">
              <header className="report-masthead">
                <p className="report-masthead-eyebrow">Validation report</p>
                <h1 className="report-masthead-title">{projectName}</h1>
                {showRecommendation && (
                  <div className="mt-4">
                    <span
                      className={`report-recommendation-badge ${recommendationBadgeClass(
                        report.overall_recommendation,
                      )}`}
                    >
                      {formatRecommendation(report.overall_recommendation)}
                    </span>
                  </div>
                )}
                <div className="report-stats">
                  <span className="report-stat-pill">
                    <strong>{questionCount}</strong> research questions
                  </span>
                  <span className="report-stat-pill">
                    <strong>{findingCount}</strong> findings
                  </span>
                  <span className="report-stat-pill">
                    <strong>{citations.length}</strong> sources
                  </span>
                </div>
              </header>

              {reportScores && report && (
                <ReportScoreSection
                  report={report}
                  sections={reportScores.sections}
                  overall={reportScores.overall}
                  derived={reportScores.derived}
                />
              )}

              {sectionLinks.length > 0 && (
                <nav
                  className="report-section-nav"
                  aria-label="Report sections"
                >
                  <div className="report-section-nav-inner">
                    {sectionLinks.map((link) => (
                      <a
                        key={link.href}
                        href={link.href}
                        className="report-section-link"
                      >
                        {link.label}
                      </a>
                    ))}
                  </div>
                </nav>
              )}

              {showRecommendation && report.recommendation_rationale && (
                <section
                  id="report-recommendation"
                  className="report-block"
                  aria-labelledby="report-recommendation-heading"
                >
                  <h2
                    id="report-recommendation-heading"
                    className="report-block-title"
                  >
                    <span className="report-block-icon">
                      <TrendingUp className="h-4 w-4" />
                    </span>
                    Recommendation
                  </h2>
                  <div className="report-card report-card-accent">
                    <ReadableProse text={report.recommendation_rationale} />
                  </div>
                </section>
              )}

              <section
                id="report-summary"
                className="report-block"
                aria-labelledby="report-summary-heading"
              >
                <h2 id="report-summary-heading" className="report-block-title">
                  <span className="report-block-icon">
                    <BookOpen className="h-4 w-4" />
                  </span>
                  Executive summary
                </h2>
                <div className="report-card">
                  <ReadableProse text={report.executive_summary} />
                </div>
              </section>

              <section
                id="report-findings"
                className="report-block"
                aria-labelledby="report-findings-heading"
              >
                <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                  <h2
                    id="report-findings-heading"
                    className="report-block-title !mb-0"
                  >
                    <span className="report-block-icon">
                      <FileText className="h-4 w-4" />
                    </span>
                    Research findings
                  </h2>
                  {questionCount > 1 && (
                    <button
                      type="button"
                      onClick={toggleAllQuestions}
                      className="fv-btn-ghost px-2.5 py-1 text-[11px]"
                    >
                      {allQuestionsExpanded ? "Collapse all" : "Expand all"}
                    </button>
                  )}
                </div>

                <div className="space-y-3">
                  {report.questions_and_findings.map((qf, qIndex) => {
                    const expanded = expandedQuestions.has(qf.question_id);
                    const displayIndex = questionDisplayIndex(
                      qf.question_id,
                      qIndex + 1,
                    );
                    return (
                      <div key={qf.question_id} className="report-question">
                        <button
                          type="button"
                          onClick={() => toggleQuestion(qf.question_id)}
                          className="report-question-trigger"
                          aria-expanded={expanded}
                        >
                          <div className="min-w-0 flex-1">
                            <div className="flex flex-wrap items-center gap-2">
                              <span className="report-question-index">
                                {displayIndex}
                              </span>
                              <span className="text-[11px] font-medium uppercase tracking-wide text-[var(--fv-text-muted)]">
                                Research question
                              </span>
                              <span className="text-[11px] text-[var(--fv-text-dim)]">
                                · {qf.findings.length} finding
                                {qf.findings.length === 1 ? "" : "s"}
                              </span>
                              <span className="report-question-score" title="Question score">
                                {resolveQuestionScore(qf)}
                              </span>
                            </div>
                            <p className="report-question-title">{qf.question}</p>
                          </div>
                          <ChevronDown
                            className={`h-5 w-5 shrink-0 text-[var(--fv-text-muted)] transition-transform ${
                              expanded ? "rotate-180" : ""
                            }`}
                          />
                        </button>
                        {expanded && (
                          <div className="report-question-body space-y-3">
                            {qf.findings.map((finding, fIndex) => (
                              <FindingCard
                                key={`${finding.question_id}-${finding.claim.slice(0, 40)}`}
                                finding={finding}
                                findingIndex={fIndex + 1}
                                citationIndexMap={citationIndexMap}
                              />
                            ))}
                            {qf.evidence_gap && (
                              <div className="report-evidence-gap">
                                <strong>Evidence gap: </strong>
                                {qf.evidence_gap}
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </section>

              {report.competitors.length > 0 && (
                <section
                  id="report-competitors"
                  className="report-block"
                  aria-labelledby="report-competitors-heading"
                >
                  <h2
                    id="report-competitors-heading"
                    className="report-block-title"
                  >
                    <span className="report-block-icon">
                      <Building2 className="h-4 w-4" />
                    </span>
                    Competitors
                  </h2>
                  <div className="report-competitor-grid">
                    {report.competitors.map((comp) => (
                      <div key={comp.name} className="report-competitor-card">
                        <h3 className="report-competitor-name">{comp.name}</h3>
                        <div className="report-prose mt-2 text-sm">
                          {splitReadableParagraphs(comp.description, 320).map(
                            (paragraph, index) => (
                              <p key={index}>{paragraph}</p>
                            ),
                          )}
                        </div>
                        {comp.positioning_vs_idea && (
                          <p className="mt-3 text-xs leading-relaxed text-[var(--fv-text-muted)]">
                            <span className="font-medium text-[var(--fv-text-soft)]">
                              vs. your idea:{" "}
                            </span>
                            {comp.positioning_vs_idea}
                          </p>
                        )}
                      </div>
                    ))}
                  </div>
                </section>
              )}

              {(report.market_signals ||
                report.distribution_signals ||
                report.regulatory_signals) && (
                <section
                  id="report-market"
                  className="report-block"
                  aria-labelledby="report-market-heading"
                >
                  <h2 id="report-market-heading" className="report-block-title">
                    <span className="report-block-icon">
                      <TrendingUp className="h-4 w-4" />
                    </span>
                    Market signals
                  </h2>
                  <div className="report-card">
                    {report.market_signals && (
                      <div className="report-signal-block">
                        <h3 className="report-signal-label">Market overview</h3>
                        <div className="report-prose mt-2 text-sm">
                          {splitReadableParagraphs(report.market_signals).map(
                            (paragraph, index) => (
                              <p key={index}>{paragraph}</p>
                            ),
                          )}
                        </div>
                      </div>
                    )}
                    {report.distribution_signals && (
                      <div className="report-signal-block">
                        <h3 className="report-signal-label">Distribution</h3>
                        <div className="report-prose mt-2 text-sm">
                          {splitReadableParagraphs(
                            report.distribution_signals,
                          ).map((paragraph, index) => (
                            <p key={index}>{paragraph}</p>
                          ))}
                        </div>
                      </div>
                    )}
                    {report.regulatory_signals && (
                      <div className="report-signal-block">
                        <h3 className="report-signal-label">Regulatory</h3>
                        <div className="report-prose mt-2 text-sm">
                          {splitReadableParagraphs(
                            report.regulatory_signals,
                          ).map((paragraph, index) => (
                            <p key={index}>{paragraph}</p>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </section>
              )}

              {report.risks_assessment && (
                <section
                  id="report-risks"
                  className="report-block"
                  aria-labelledby="report-risks-heading"
                >
                  <h2 id="report-risks-heading" className="report-block-title">
                    <span className="report-block-icon">
                      <AlertTriangle className="h-4 w-4" />
                    </span>
                    Risk assessment
                  </h2>
                  <div className="report-card border-[color-mix(in_srgb,var(--fv-warning)_22%,transparent)]">
                    <RiskAssessmentContent text={report.risks_assessment} />
                  </div>
                </section>
              )}

              {report.research_limitations && (
                <section className="report-block">
                  <h2 className="report-block-title">
                    <span className="report-block-icon">
                      <AlertTriangle className="h-4 w-4" />
                    </span>
                    Research limitations
                  </h2>
                  <div className="report-card">
                    <ReadableProse text={report.research_limitations} />
                  </div>
                </section>
              )}

              {citations.length > 0 && (
                <section
                  id="report-sources"
                  className="report-block"
                  aria-labelledby="report-sources-heading"
                >
                  <h2 id="report-sources-heading" className="report-block-title">
                    <span className="report-block-icon">
                      <ExternalLink className="h-4 w-4" />
                    </span>
                    Sources ({citations.length})
                  </h2>
                  <ol className="report-source-list">
                    {citations.map((citation, index) => (
                      <li
                        key={`${citation.url}-${index}`}
                        id={`citation-${index + 1}`}
                        className="report-source-item"
                      >
                        <span className="report-source-num">{index + 1}</span>
                        <div className="min-w-0">
                          <SafeCitationLink citation={citation} />
                          {citation.source_domain && (
                            <p className="mt-0.5 text-xs text-[var(--fv-text-muted)]">
                              {citation.source_domain}
                            </p>
                          )}
                        </div>
                      </li>
                    ))}
                  </ol>
                </section>
              )}

              <p className="report-footer-note">
                Generated by Fivvle research engine · Rubric{" "}
                {report.rubric_version_used}
              </p>
            </article>
          )}
        </div>
      </div>
    </div>
  );
}
