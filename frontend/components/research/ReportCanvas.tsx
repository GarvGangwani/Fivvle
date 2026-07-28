"use client";

import { useEffect, useMemo, useState, type ReactNode } from "react";
import {
  AlertTriangle,
  ArrowLeft,
  BookOpen,
  Building2,
  ChevronDown,
  ExternalLink,
  FileText,
  Maximize2,
  Minimize2,
  TrendingUp,
  X,
} from "lucide-react";
import { getValidationReport } from "@/lib/api";
import {
  confidenceBadgeClass,
  recommendationBadgeClass,
} from "@/lib/report-badges";
import {
  parseRiskAssessment,
  questionDisplayIndex,
  splitReadableParagraphs,
} from "@/lib/report-text";
import {
  resolveQuestionScore,
  resolveReportScores,
} from "@/lib/validation-report-scores";
import { ValidationReportExportMenu } from "@/components/research/ValidationReportExportMenu";
import type {
  Citation,
  Finding,
  OverallRecommendation,
  ValidationReport,
} from "@/lib/types";
import { BrutalistSkeleton } from "@/components/ui/BrutalistSkeleton";
import { PanelHeader } from "@/components/ui/PanelHeader";
import { ReportScoreSection } from "@/components/research/ReportScoreSection";

function isSafeHttpUrl(url: string): boolean {
  return url.startsWith("http://") || url.startsWith("https://");
}

function SafeCitationLink({ citation }: { citation: Citation }) {
  if (!isSafeHttpUrl(citation.url)) {
    return <span className="text-ink-primary">{citation.title}</span>;
  }
  return (
    <a
      href={citation.url}
      target="_blank"
      rel="noopener noreferrer"
      className="inline-flex items-center gap-1 text-ink-primary underline decoration-2 underline-offset-2 hover:text-brand-primary"
      title={citation.title}
    >
      {citation.title}
      <ExternalLink className="h-3 w-3 opacity-60" />
    </a>
  );
}

function formatRecommendation(rec: OverallRecommendation): string {
  if (rec === "too_vague_to_recommend") return "Needs clarity";
  return rec.charAt(0).toUpperCase() + rec.slice(1);
}

function findingAccentBorder(confidence: string): string {
  switch (confidence) {
    case "high":
      return "border-l-status-success";
    case "medium":
      return "border-l-status-warning";
    default:
      return "border-l-border-master";
  }
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
    <div className="space-y-3 font-body text-body-md leading-relaxed text-ink-primary">
      {paragraphs.map((paragraph, index) => (
        <p key={index}>{paragraph}</p>
      ))}
    </div>
  );
}

function SectionHeading({
  id,
  icon,
  children,
}: {
  id?: string;
  icon: ReactNode;
  children: ReactNode;
}) {
  return (
    <h2
      id={id}
      className="mb-3 flex items-center gap-2 font-mono text-mono-sm uppercase tracking-wider text-ink-secondary"
    >
      <span className="text-ink-tertiary" aria-hidden="true">
        {icon}
      </span>
      {children}
    </h2>
  );
}

function RiskAssessmentContent({ text }: { text: string }) {
  const parsed = parseRiskAssessment(text);

  if (!parsed.isStructured) {
    return <ReadableProse text={text} />;
  }

  return (
    <div className="space-y-3">
      {parsed.preamble && (
        <div className="space-y-2 font-body text-body-sm leading-relaxed text-ink-secondary">
          {splitReadableParagraphs(parsed.preamble, 420).map(
            (paragraph, index) => (
              <p key={index}>{paragraph}</p>
            ),
          )}
        </div>
      )}
      <ol className="space-y-3">
        {parsed.items.map((risk) => (
          <li
            key={risk.number}
            className="border-2 border-border-master border-l-4 border-l-status-warning bg-surface-elevated p-3 shadow-brutal-sm"
          >
            <div className="flex items-start gap-3">
              <span
                className="flex h-7 w-7 shrink-0 items-center justify-center border-2 border-border-master bg-surface-card font-mono text-mono-sm font-bold text-ink-primary"
                aria-hidden="true"
              >
                {risk.number}
              </span>
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-baseline gap-2">
                  <h3 className="font-headline text-headline-md uppercase tracking-tighter text-ink-primary">
                    {risk.title}
                  </h3>
                  {risk.verdict && (
                    <span className="font-mono text-mono-sm uppercase text-status-warning">
                      {risk.verdict}
                    </span>
                  )}
                </div>
                {risk.body && (
                  <div className="mt-2 space-y-2 font-body text-body-sm leading-relaxed text-ink-secondary">
                    {splitReadableParagraphs(risk.body, 420).map(
                      (paragraph, index) => (
                        <p key={index}>{paragraph}</p>
                      ),
                    )}
                  </div>
                )}
              </div>
            </div>
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
            className="ml-1 font-mono text-mono-sm text-brand-primary no-underline hover:underline"
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
      className={`border-2 border-border-master border-l-4 bg-surface-card p-4 shadow-brutal-sm ${findingAccentBorder(finding.confidence)}`}
    >
      <div className="mb-2 flex flex-wrap items-center gap-2">
        <span className="font-mono text-mono-sm uppercase text-ink-tertiary">
          Finding {findingIndex}
        </span>
        <span
          className={`border-2 px-2 py-0.5 font-label-md text-label-sm uppercase tracking-wider ${confidenceBadgeClass(finding.confidence)}`}
        >
          {finding.confidence} confidence
        </span>
      </div>
      <p className="font-body text-body-md font-semibold leading-relaxed text-ink-primary">
        {finding.claim}
      </p>
      {evidenceParagraphs.length > 0 && (
        <div className="mt-2 space-y-2 font-body text-body-sm leading-relaxed text-ink-secondary">
          {evidenceParagraphs.map((paragraph, index) => (
            <p key={index}>
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
        <p className="mt-2 font-mono text-mono-sm leading-relaxed text-ink-tertiary">
          {finding.confidence_rationale}
        </p>
      )}
    </article>
  );
}

function ReportLoadingSkeleton() {
  return (
    <div className="space-y-4" aria-busy="true" aria-label="Loading report">
      <BrutalistSkeleton variant="block" height="h-28" />
      <BrutalistSkeleton variant="card" height="h-40" />
      <BrutalistSkeleton variant="line" width="w-2/3" />
      <BrutalistSkeleton variant="card" height="h-32" />
      <BrutalistSkeleton variant="card" height="h-32" />
    </div>
  );
}

const chromeBtnClass =
  "inline-flex items-center gap-1.5 border-2 border-border-master bg-surface-card px-2.5 py-1.5 font-label-md text-label-sm uppercase tracking-wider text-ink-primary shadow-brutal-sm transition-all hover:-translate-x-0.5 hover:-translate-y-0.5 hover:shadow-brutal-md";

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

  const headerActions = (
    <div className="flex shrink-0 flex-wrap items-center gap-2">
      {report ? (
        <ValidationReportExportMenu
          report={report}
          projectName={projectName}
          variant="ghost"
        />
      ) : null}
      {fullscreen ? (
        <button
          type="button"
          onClick={() => setFullscreen(false)}
          className={chromeBtnClass}
          aria-label="Exit full screen"
        >
          <Minimize2 className="h-3.5 w-3.5" />
          <span className="hidden sm:inline">Exit full screen</span>
        </button>
      ) : embedded ? null : (
        <button
          type="button"
          onClick={() => setFullscreen(true)}
          className={chromeBtnClass}
          aria-label="View full screen"
          title="View full screen"
        >
          <Maximize2 className="h-3.5 w-3.5" />
        </button>
      )}
      {onClose && !fullscreen ? (
        <button
          type="button"
          onClick={onClose}
          className={chromeBtnClass}
          aria-label="Close report"
        >
          <X className="h-3.5 w-3.5" />
        </button>
      ) : null}
    </div>
  );

  return (
    <div
      className={`flex min-h-0 flex-col bg-canvas-bg ${
        fullscreen ? "fixed inset-0 z-[80] h-dvh max-h-dvh" : "h-full"
      }`}
    >
      {showEmbeddedToolbar && (
        <div className="flex shrink-0 items-center justify-end gap-2 border-b-2 border-border-master bg-surface-card px-4 py-2">
          <ValidationReportExportMenu
            report={report}
            projectName={projectName}
            variant="ghost"
          />
          <button
            type="button"
            onClick={() => setFullscreen(true)}
            className={chromeBtnClass}
          >
            <Maximize2 className="h-3.5 w-3.5" />
            Full screen
          </button>
        </div>
      )}

      {showOverlayHeader && (
        <PanelHeader
          sticky
          phaseLabel="VALIDATION REPORT"
          title={projectName}
          breadcrumb={
            mobile && onClose && !fullscreen ? (
              <button
                type="button"
                onClick={onClose}
                className={`${chromeBtnClass} lg:hidden`}
                aria-label="Back"
              >
                <ArrowLeft className="h-4 w-4" />
              </button>
            ) : undefined
          }
          actions={headerActions}
        />
      )}

      <div className="min-h-0 flex-1 overflow-y-auto">
        <div className="mx-auto max-w-3xl px-3 py-4 sm:px-5 sm:py-6">
          {loading && <ReportLoadingSkeleton />}

          {error && !loading && (
            <div
              role="alert"
              className="border-2 border-status-critical bg-surface-card p-4 font-mono text-mono-sm uppercase text-status-critical shadow-brutal-sm"
            >
              {error}
            </div>
          )}

          {report && !loading && (
            <article>
              <header className="border-b-2 border-border-master pb-5">
                <p className="font-mono text-mono-sm uppercase tracking-wider text-ink-tertiary">
                  Validation report
                </p>
                <h1 className="mt-1 font-headline text-headline-lg uppercase tracking-tighter text-ink-primary">
                  {projectName}
                </h1>
                {showRecommendation && (
                  <div className="mt-4">
                    <span
                      className={`inline-flex border-2 px-3 py-1 font-label-md text-label-sm uppercase tracking-wider ${recommendationBadgeClass(
                        report.overall_recommendation,
                      )}`}
                    >
                      {formatRecommendation(report.overall_recommendation)}
                    </span>
                  </div>
                )}
                <div className="mt-4 flex flex-wrap gap-2">
                  <span className="inline-flex items-center gap-1 border-2 border-border-master bg-surface-elevated px-2.5 py-1 font-mono text-mono-sm uppercase text-ink-secondary">
                    <strong className="text-ink-primary">{questionCount}</strong>{" "}
                    research questions
                  </span>
                  <span className="inline-flex items-center gap-1 border-2 border-border-master bg-surface-elevated px-2.5 py-1 font-mono text-mono-sm uppercase text-ink-secondary">
                    <strong className="text-ink-primary">{findingCount}</strong>{" "}
                    findings
                  </span>
                  <span className="inline-flex items-center gap-1 border-2 border-border-master bg-surface-elevated px-2.5 py-1 font-mono text-mono-sm uppercase text-ink-secondary">
                    <strong className="text-ink-primary">
                      {citations.length}
                    </strong>{" "}
                    sources
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
                  className="sticky top-0 z-5 mb-5 mt-4 border-b-2 border-border-master bg-canvas-bg/95 py-2 backdrop-blur-sm"
                  aria-label="Report sections"
                >
                  <div className="flex gap-2 overflow-x-auto pb-1">
                    {sectionLinks.map((link) => (
                      <a
                        key={link.href}
                        href={link.href}
                        className="shrink-0 border-2 border-border-master bg-surface-card px-2.5 py-1 font-mono text-mono-sm uppercase text-ink-primary no-underline transition-colors hover:bg-surface-elevated"
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
                  className="mb-5 border-2 border-border-master bg-surface-card p-4 shadow-brutal-sm"
                  aria-labelledby="report-recommendation-heading"
                >
                  <SectionHeading
                    id="report-recommendation-heading"
                    icon={<TrendingUp className="h-4 w-4" />}
                  >
                    Recommendation
                  </SectionHeading>
                  <ReadableProse text={report.recommendation_rationale} />
                </section>
              )}

              <section
                id="report-summary"
                className="mb-5 border-2 border-border-master bg-surface-card p-4 shadow-brutal-sm"
                aria-labelledby="report-summary-heading"
              >
                <SectionHeading
                  id="report-summary-heading"
                  icon={<BookOpen className="h-4 w-4" />}
                >
                  Executive summary
                </SectionHeading>
                <ReadableProse text={report.executive_summary} />
              </section>

              <section
                id="report-findings"
                className="mb-5"
                aria-labelledby="report-findings-heading"
              >
                <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                  <SectionHeading
                    id="report-findings-heading"
                    icon={<FileText className="h-4 w-4" />}
                  >
                    Research findings
                  </SectionHeading>
                  {questionCount > 1 && (
                    <button
                      type="button"
                      onClick={toggleAllQuestions}
                      className={chromeBtnClass}
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
                      <div
                        key={qf.question_id}
                        className="border-2 border-border-master bg-surface-card shadow-brutal-sm"
                      >
                        <button
                          type="button"
                          onClick={() => toggleQuestion(qf.question_id)}
                          className="flex w-full items-start gap-3 p-4 text-left transition-colors hover:bg-surface-elevated"
                          aria-expanded={expanded}
                        >
                          <div className="min-w-0 flex-1">
                            <div className="flex flex-wrap items-center gap-2">
                              <span className="flex h-6 min-w-6 items-center justify-center border-2 border-border-master bg-surface-elevated px-1.5 font-mono text-mono-sm font-bold text-ink-primary">
                                {displayIndex}
                              </span>
                              <span className="font-mono text-mono-sm uppercase text-ink-tertiary">
                                Research question
                              </span>
                              <span className="font-mono text-mono-sm text-ink-tertiary">
                                · {qf.findings.length} finding
                                {qf.findings.length === 1 ? "" : "s"}
                              </span>
                              <span
                                className="border-2 border-border-master bg-surface-elevated px-2 py-0.5 font-mono text-mono-sm font-bold tabular-nums text-ink-primary"
                                title="Question score"
                              >
                                {resolveQuestionScore(qf)}
                              </span>
                            </div>
                            <p className="mt-2 font-body text-body-md font-semibold text-ink-primary">
                              {qf.question}
                            </p>
                          </div>
                          <ChevronDown
                            className={`h-5 w-5 shrink-0 text-ink-tertiary transition-transform ${
                              expanded ? "rotate-180" : ""
                            }`}
                          />
                        </button>
                        {expanded && (
                          <div className="space-y-3 border-t-2 border-border-master p-4">
                            {qf.findings.map((finding, fIndex) => (
                              <FindingCard
                                key={`${finding.question_id}-${finding.claim.slice(0, 40)}`}
                                finding={finding}
                                findingIndex={fIndex + 1}
                                citationIndexMap={citationIndexMap}
                              />
                            ))}
                            {qf.evidence_gap && (
                              <div className="border-2 border-status-warning bg-surface-elevated p-3 font-body text-body-sm text-ink-primary">
                                <strong className="font-mono text-mono-sm uppercase text-status-warning">
                                  Evidence gap:{" "}
                                </strong>
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
                  className="mb-5"
                  aria-labelledby="report-competitors-heading"
                >
                  <SectionHeading
                    id="report-competitors-heading"
                    icon={<Building2 className="h-4 w-4" />}
                  >
                    Competitors
                  </SectionHeading>
                  <div className="grid gap-3 sm:grid-cols-2">
                    {report.competitors.map((comp) => (
                      <div
                        key={comp.name}
                        className="border-2 border-border-master bg-surface-card p-4 shadow-brutal-sm"
                      >
                        <h3 className="font-headline text-headline-md uppercase tracking-tighter text-ink-primary">
                          {comp.name}
                        </h3>
                        <div className="mt-2 space-y-2 font-body text-body-sm leading-relaxed text-ink-secondary">
                          {splitReadableParagraphs(comp.description, 320).map(
                            (paragraph, index) => (
                              <p key={index}>{paragraph}</p>
                            ),
                          )}
                        </div>
                        {comp.positioning_vs_idea && (
                          <p className="mt-3 font-mono text-mono-sm leading-relaxed text-ink-tertiary">
                            <span className="uppercase text-ink-secondary">
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
                  className="mb-5 border-2 border-border-master bg-surface-card p-4 shadow-brutal-sm"
                  aria-labelledby="report-market-heading"
                >
                  <SectionHeading
                    id="report-market-heading"
                    icon={<TrendingUp className="h-4 w-4" />}
                  >
                    Market signals
                  </SectionHeading>
                  <div className="space-y-4">
                    {report.market_signals && (
                      <div className="border-t-2 border-border-master pt-3 first:border-t-0 first:pt-0">
                        <h3 className="font-mono text-mono-sm uppercase text-ink-tertiary">
                          Market overview
                        </h3>
                        <div className="mt-2 space-y-2 font-body text-body-sm leading-relaxed text-ink-secondary">
                          {splitReadableParagraphs(report.market_signals).map(
                            (paragraph, index) => (
                              <p key={index}>{paragraph}</p>
                            ),
                          )}
                        </div>
                      </div>
                    )}
                    {report.distribution_signals && (
                      <div className="border-t-2 border-border-master pt-3">
                        <h3 className="font-mono text-mono-sm uppercase text-ink-tertiary">
                          Distribution
                        </h3>
                        <div className="mt-2 space-y-2 font-body text-body-sm leading-relaxed text-ink-secondary">
                          {splitReadableParagraphs(
                            report.distribution_signals,
                          ).map((paragraph, index) => (
                            <p key={index}>{paragraph}</p>
                          ))}
                        </div>
                      </div>
                    )}
                    {report.regulatory_signals && (
                      <div className="border-t-2 border-border-master pt-3">
                        <h3 className="font-mono text-mono-sm uppercase text-ink-tertiary">
                          Regulatory
                        </h3>
                        <div className="mt-2 space-y-2 font-body text-body-sm leading-relaxed text-ink-secondary">
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
                  className="mb-5 border-2 border-border-master border-l-4 border-l-status-warning bg-surface-card p-4 shadow-brutal-sm"
                  aria-labelledby="report-risks-heading"
                >
                  <SectionHeading
                    id="report-risks-heading"
                    icon={<AlertTriangle className="h-4 w-4" />}
                  >
                    Risk assessment
                  </SectionHeading>
                  <RiskAssessmentContent text={report.risks_assessment} />
                </section>
              )}

              {report.research_limitations && (
                <section className="mb-5 border-2 border-border-master bg-surface-card p-4 shadow-brutal-sm">
                  <SectionHeading
                    icon={<AlertTriangle className="h-4 w-4" />}
                  >
                    Research limitations
                  </SectionHeading>
                  <ReadableProse text={report.research_limitations} />
                </section>
              )}

              {citations.length > 0 && (
                <section
                  id="report-sources"
                  className="mb-5 border-2 border-border-master bg-surface-card p-4 shadow-brutal-sm"
                  aria-labelledby="report-sources-heading"
                >
                  <SectionHeading
                    id="report-sources-heading"
                    icon={<ExternalLink className="h-4 w-4" />}
                  >
                    Sources ({citations.length})
                  </SectionHeading>
                  <ol className="space-y-3">
                    {citations.map((citation, index) => (
                      <li
                        key={`${citation.url}-${index}`}
                        id={`citation-${index + 1}`}
                        className="flex gap-3 border-t-2 border-border-master pt-3 first:border-t-0 first:pt-0"
                      >
                        <span className="flex h-7 w-7 shrink-0 items-center justify-center border-2 border-border-master bg-surface-elevated font-mono text-mono-sm font-bold text-ink-primary">
                          {index + 1}
                        </span>
                        <div className="min-w-0">
                          <SafeCitationLink citation={citation} />
                          {citation.source_domain && (
                            <p className="mt-0.5 font-mono text-mono-sm text-ink-tertiary">
                              {citation.source_domain}
                            </p>
                          )}
                        </div>
                      </li>
                    ))}
                  </ol>
                </section>
              )}

              <p className="font-mono text-mono-sm uppercase text-ink-tertiary">
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
