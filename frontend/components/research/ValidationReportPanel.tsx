"use client";

import { useEffect, useState } from "react";
import {
  AlertTriangle,
  ChevronDown,
  ChevronRight,
  ExternalLink,
  Loader2,
  X,
} from "lucide-react";
import { getValidationReport, ApiError } from "@/lib/api";
import type {
  Citation,
  Finding,
  OverallRecommendation,
  ValidationReport,
} from "@/lib/types";
import { ReportScoreSection } from "@/components/research/ReportScoreSection";
import { resolveReportScores } from "@/lib/validation-report-scores";

const REPORT_TABS = [
  "Summary",
  "Findings",
  "Competitors",
  "Signals",
  "Risks",
  "Citations",
] as const;

type ReportTab = (typeof REPORT_TABS)[number];

function isSafeHttpUrl(url: string): boolean {
  return url.startsWith("http://") || url.startsWith("https://");
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
  if (rec === "too_vague_to_recommend") return "UNCLEAR";
  return rec.toUpperCase();
}

function confidenceClass(confidence: Finding["confidence"]): string {
  switch (confidence) {
    case "high":
      return "bg-[rgba(16,185,129,0.15)] text-[var(--fv-success)] ring-[rgba(16,185,129,0.3)]";
    case "medium":
      return "bg-[rgba(245,158,11,0.15)] text-[var(--fv-warning)] ring-[rgba(245,158,11,0.3)]";
    case "low":
      return "bg-[var(--fv-hover-overlay)] text-[var(--fv-text-soft)] ring-[var(--fv-border)]";
  }
}

function SafeCitationLink({ citation }: { citation: Citation }) {
  if (!isSafeHttpUrl(citation.url)) {
    return (
      <span className="text-sm text-[var(--fv-text-muted)]">
        {citation.title}
      </span>
    );
  }

  return (
    <a
      href={citation.url}
      target="_blank"
      rel="noopener noreferrer"
      className="inline-flex items-center gap-1 text-sm text-[var(--fv-accent)] hover:text-[var(--fv-accent-hover)] no-underline"
    >
      {citation.title}
      <ExternalLink className="h-3.5 w-3.5 shrink-0" />
    </a>
  );
}

function FindingCard({ finding }: { finding: Finding }) {
  return (
    <div className="fv-card p-4">
      <div className="mb-2 flex flex-wrap items-center gap-2">
        <span
          className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset ${confidenceClass(finding.confidence)}`}
        >
          {finding.confidence} confidence
        </span>
      </div>
      <p className="whitespace-pre-wrap text-[13px] font-medium text-[var(--fv-text)]">
        {finding.claim}
      </p>
      <p className="mt-2 whitespace-pre-wrap text-[13px] text-[var(--fv-text-soft)]">
        {finding.evidence_summary}
      </p>
      <p className="mt-2 whitespace-pre-wrap text-[12px] text-[var(--fv-text-muted)]">
        {finding.confidence_rationale}
      </p>
      {finding.citations.length > 0 && (
        <div className="mt-3 space-y-1 border-t border-[var(--fv-border)] pt-2">
          {finding.citations.map((c) => (
            <SafeCitationLink key={c.url} citation={c} />
          ))}
        </div>
      )}
    </div>
  );
}

function QuestionSection({
  question,
  defaultOpen,
}: {
  question: ValidationReport["questions_and_findings"][number];
  defaultOpen: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <div className="border-b border-[var(--fv-border)] last:border-b-0">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-start gap-2 py-4 text-left"
      >
        {open ? (
          <ChevronDown className="mt-0.5 h-5 w-5 shrink-0 text-[var(--fv-text-muted)]" />
        ) : (
          <ChevronRight className="mt-0.5 h-5 w-5 shrink-0 text-[var(--fv-text-muted)]" />
        )}
        <span className="text-[13px] font-semibold text-[var(--fv-text)]">
          {question.question}
        </span>
      </button>
      {open && (
        <div className="space-y-3 pb-4 pl-7">
          {question.findings.map((finding) => (
            <FindingCard key={`${finding.question_id}-${finding.claim}`} finding={finding} />
          ))}
          {question.evidence_gap && (
            <p className="whitespace-pre-wrap text-[12px] text-[var(--fv-warning)]">
              Evidence gap: {question.evidence_gap}
            </p>
          )}
        </div>
      )}
    </div>
  );
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

interface ValidationReportPanelProps {
  experimentId: string;
  open: boolean;
  onClose: () => void;
}

export function ValidationReportPanel({
  experimentId,
  open,
  onClose,
}: ValidationReportPanelProps) {
  const [report, setReport] = useState<ValidationReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<ReportTab>("Summary");

  useEffect(() => {
    if (!open) return;

    let cancelled = false;

    async function load() {
      setLoading(true);
      setError(null);
      try {
        const data = await getValidationReport(experimentId);
        if (!cancelled) setReport(data);
      } catch (err) {
        if (cancelled) return;
        setError(
          err instanceof ApiError
            ? "Could not load the validation report."
            : "Could not load the validation report.",
        );
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, [experimentId, open]);

  useEffect(() => {
    if (!open) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  const citations = report ? collectAllCitations(report) : [];
  const reportScores = report ? resolveReportScores(report) : null;

  if (!open) return null;

  return (
    <div
      className="flex h-full min-h-0 flex-col bg-[var(--fv-surface)]"
      role="region"
      aria-label="Validation Report"
    >
        <div
          className="flex items-center justify-between border-b px-5 py-4"
          style={{ borderColor: "rgba(255,255,255,0.07)" }}
        >
          <div className="flex items-center gap-3">
            <h2 className="text-[15px] font-bold text-[var(--fv-text)]">
              Validation Report
            </h2>
            {report && (
              <span
                className={recommendationBadgeClass(report.overall_recommendation)}
              >
                {formatRecommendation(report.overall_recommendation)}
              </span>
            )}
          </div>
          <button
            type="button"
            onClick={onClose}
            className="icon-btn"
            aria-label="Close report"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <div
          className="flex gap-1 border-b px-4 py-3"
          style={{ borderColor: "rgba(255,255,255,0.07)" }}
        >
          {REPORT_TABS.map((tab) => (
            <button
              key={tab}
              type="button"
              onClick={() => setActiveTab(tab)}
              className={`report-tab ${activeTab === tab ? "active" : ""}`}
            >
              {tab}
            </button>
          ))}
        </div>

        <div className="px-6 py-5">
          {loading && (
            <div className="flex items-center justify-center py-16">
              <Loader2 className="h-6 w-6 animate-spin text-[var(--fv-accent)]" />
            </div>
          )}

          {error && (
            <div className="fv-error text-sm">{error}</div>
          )}

          {report && !loading && activeTab === "Summary" && reportScores && (
            <div className="space-y-5">
              <ReportScoreSection
                report={report}
                sections={reportScores.sections}
                overall={reportScores.overall}
                derived={reportScores.derived}
              />

              <div>
                <h3 className="fv-panel-label mb-3">Executive Summary</h3>
                <p className="whitespace-pre-wrap text-[14px] leading-relaxed text-[var(--fv-text-soft)]">
                  {report.executive_summary}
                </p>
              </div>

              <div
                className="rounded-xl p-4"
                style={{
                  background: "rgba(16,185,129,0.08)",
                  border: "1px solid rgba(16,185,129,0.2)",
                }}
              >
                <p className="text-[13px] font-semibold text-fv-success">
                  Recommendation: {formatRecommendation(report.overall_recommendation)}
                </p>
                <p className="mt-2 whitespace-pre-wrap text-[13px] leading-relaxed text-[var(--fv-text-soft)]">
                  {report.recommendation_rationale}
                </p>
              </div>

              <div>
                <h3 className="fv-panel-label mb-3">Market Signals</h3>
                {report.market_signals ? (
                  <p className="whitespace-pre-wrap text-[13px] leading-relaxed text-[var(--fv-text-soft)]">
                    {report.market_signals}
                  </p>
                ) : (
                  <span className="unavailable-badge">Data unavailable</span>
                )}
              </div>

              {report.research_limitations && (
                <div>
                  <h3 className="fv-panel-label mb-3">Research Limitations</h3>
                  <p className="whitespace-pre-wrap text-[13px] leading-relaxed text-[var(--fv-text-muted)]">
                    {report.research_limitations}
                  </p>
                </div>
              )}
            </div>
          )}

          {report && !loading && activeTab === "Findings" && (
            <div>
              {report.questions_and_findings.length === 0 ? (
                <p className="text-sm text-[var(--fv-text-muted)]">
                  No research findings available.
                </p>
              ) : (
                report.questions_and_findings.map((qf, i) => (
                  <QuestionSection key={qf.question_id} question={qf} defaultOpen={i === 0} />
                ))
              )}
            </div>
          )}

          {report && !loading && activeTab === "Competitors" && (
            <div className="space-y-3">
              {report.competitors.length === 0 ? (
                <p className="text-sm text-[var(--fv-text-muted)]">
                  No competitors identified.
                </p>
              ) : (
                report.competitors.map((comp) => (
                  <div key={comp.name} className="fv-card p-4">
                    <div className="mb-2 flex items-center justify-between gap-2">
                      <p className="text-[14px] font-semibold text-[var(--fv-text)]">
                        {comp.name}
                      </p>
                      <span className="severity-medium">Competitor</span>
                    </div>
                    <p className="text-[13px] text-[var(--fv-text-soft)]">
                      {comp.description}
                    </p>
                    <p className="mt-2 text-[12px] text-[var(--fv-text-muted)]">
                      Gap: {comp.positioning_vs_idea}
                    </p>
                    {comp.citations.length > 0 && (
                      <div className="mt-3 space-y-1 border-t border-[var(--fv-border)] pt-2">
                        {comp.citations.map((c) => (
                          <SafeCitationLink key={c.url} citation={c} />
                        ))}
                      </div>
                    )}
                  </div>
                ))
              )}
            </div>
          )}

          {report && !loading && activeTab === "Signals" && (
            <div className="space-y-6">
              {(
                [
                  ["Market", report.market_signals],
                  ["Distribution", report.distribution_signals],
                  ["Regulatory", report.regulatory_signals],
                ] as const
              ).map(([group, text]) => (
                <div key={group}>
                  <h3 className="fv-panel-label mb-3">{group}</h3>
                  {text ? (
                    <p className="whitespace-pre-wrap text-[13px] leading-relaxed text-[var(--fv-text-soft)]">
                      {text}
                    </p>
                  ) : (
                    <span className="unavailable-badge">Data unavailable</span>
                  )}
                </div>
              ))}
            </div>
          )}

          {report && !loading && activeTab === "Risks" && (
            <div className="space-y-3">
              {report.risks_assessment ? (
                report.risks_assessment
                  .split("\n")
                  .map((line) => line.trim())
                  .filter(Boolean)
                  .map((risk, i) => (
                    <div key={i} className="fv-card p-4">
                      <div className="mb-2 flex items-center gap-2">
                        <AlertTriangle className="h-4 w-4 text-[var(--fv-warning)]" />
                        <span className="severity-high">Risk</span>
                      </div>
                      <p className="text-[13px] leading-relaxed text-[var(--fv-text-soft)]">
                        {risk}
                      </p>
                    </div>
                  ))
              ) : (
                <p className="text-sm text-[var(--fv-text-muted)]">
                  No significant risks identified.
                </p>
              )}
            </div>
          )}

          {report && !loading && activeTab === "Citations" && (
            <div className="space-y-3">
              {citations.length === 0 ? (
                <p className="text-sm text-[var(--fv-text-muted)]">
                  No citations available.
                </p>
              ) : (
                citations.map((citation, i) => (
                  <div key={`${citation.url}-${i}`} className="flex items-start gap-3">
                    <span
                      className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-[11px] font-bold text-fv-bg"
                      style={{ background: "var(--fv-accent)" }}
                    >
                      {i + 1}
                    </span>
                    <div className="min-w-0 flex-1">
                      <SafeCitationLink citation={citation} />
                      <p className="mt-0.5 text-[11px] text-[var(--fv-text-muted)]">
                        {citation.source_domain}
                      </p>
                    </div>
                  </div>
                ))
              )}
            </div>
          )}
        </div>
    </div>
  );
}
