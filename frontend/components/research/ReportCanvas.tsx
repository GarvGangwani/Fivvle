"use client";

import { useEffect, useState } from "react";
import {
  ArrowLeft,
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

function isSafeHttpUrl(url: string): boolean {
  return url.startsWith("http://") || url.startsWith("https://");
}

function SafeCitationLink({
  citation,
  index,
}: {
  citation: Citation;
  index?: number;
}) {
  const label = index != null ? `[${index}] ` : "";

  if (!isSafeHttpUrl(citation.url)) {
    return (
      <span className="text-[var(--fv-text-muted)]">
        {label}
        {citation.title}
      </span>
    );
  }

  return (
    <a
      href={citation.url}
      target="_blank"
      rel="noopener noreferrer"
      className="inline-flex items-center gap-1 text-[var(--fv-accent)] no-underline hover:text-[var(--fv-accent-hover)]"
    >
      {label}
      {citation.title}
      <ExternalLink className="h-3.5 w-3.5 shrink-0" />
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
  if (rec === "too_vague_to_recommend") return "Unclear";
  return rec.charAt(0).toUpperCase() + rec.slice(1);
}

function confidenceLabel(confidence: Finding["confidence"]): string {
  return `${confidence.charAt(0).toUpperCase()}${confidence.slice(1)} confidence`;
}

function inferRiskSeverity(
  risk: string,
  index: number,
): "high" | "medium" | "low" {
  const lower = risk.toLowerCase();
  if (
    /critical|severe|major|significant|high risk|fundamental|fatal/.test(lower)
  ) {
    return "high";
  }
  if (/moderate|medium|uncertain|dependency|competition/.test(lower)) {
    return "medium";
  }
  if (index % 3 === 2) return "low";
  if (index % 3 === 1) return "medium";
  return "high";
}

function severityBadgeClass(severity: "high" | "medium" | "low"): string {
  switch (severity) {
    case "high":
      return "severity-high";
    case "medium":
      return "severity-medium";
    case "low":
      return "severity-low";
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

function parseRiskLines(risksAssessment: string): string[] {
  return risksAssessment
    .split("\n")
    .map((line) => line.replace(/^[-*•]\s*/, "").trim())
    .filter(Boolean);
}

export interface ReportCanvasProps {
  experimentId: string;
  onClose: () => void;
  /** When true, show a back affordance instead of only the close icon. */
  mobile?: boolean;
}

export function ReportCanvas({
  experimentId,
  onClose,
  mobile = false,
}: ReportCanvasProps) {
  const [report, setReport] = useState<ValidationReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
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

    void load();
    return () => {
      cancelled = true;
    };
  }, [experimentId]);

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const citations = report ? collectAllCitations(report) : [];
  const risks = report ? parseRiskLines(report.risks_assessment) : [];

  return (
    <div className="flex h-full min-h-0 flex-col">
      <header className="sticky top-0 z-10 flex shrink-0 items-center justify-between border-b border-[var(--fv-border)] bg-[var(--fv-bg)] px-4 py-4 lg:px-8">
        <div className="flex min-w-0 items-center gap-3">
          {mobile && (
            <button
              type="button"
              onClick={onClose}
              className="fv-icon-btn shrink-0 lg:hidden"
              aria-label="Back to chat"
            >
              <ArrowLeft className="h-4 w-4" />
            </button>
          )}
          <div className="min-w-0">
            <h1 className="truncate text-[17px] font-semibold text-[var(--fv-text)]">
              Validation Report
            </h1>
            {report && (
              <div className="mt-1 flex flex-wrap items-center gap-2">
                <span
                  className={recommendationBadgeClass(
                    report.overall_recommendation,
                  )}
                >
                  {formatRecommendation(report.overall_recommendation)}
                </span>
              </div>
            )}
          </div>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="icon-btn shrink-0"
          aria-label="Close report"
        >
          <X className="h-4 w-4" />
        </button>
      </header>

      <div className="flex-1 overflow-y-auto px-8 py-6">
        {loading && (
          <div className="flex items-center justify-center py-24">
            <Loader2 className="h-6 w-6 animate-spin text-[var(--fv-accent)]" />
          </div>
        )}

        {error && !loading && (
          <div className="fv-error text-sm">{error}</div>
        )}

        {report && !loading && (
          <article className="mx-auto max-w-3xl space-y-12 text-[16px] leading-[1.75] text-[var(--fv-text-soft)]">
            <section>
              <h2 className="mb-4 text-[22px] font-semibold leading-tight text-[var(--fv-text)]">
                Executive Summary
              </h2>
              <p className="whitespace-pre-wrap">{report.executive_summary}</p>
              {report.recommendation_rationale && (
                <div className="mt-6 rounded-xl border border-[var(--fv-border)] bg-[var(--fv-surface)] p-5">
                  <p className="text-[15px] font-medium text-[var(--fv-text)]">
                    Recommendation rationale
                  </p>
                  <p className="mt-2 whitespace-pre-wrap text-[15px] leading-[1.75]">
                    {report.recommendation_rationale}
                  </p>
                </div>
              )}
            </section>

            <section>
              <h2 className="mb-6 text-[22px] font-semibold leading-tight text-[var(--fv-text)]">
                Research Questions &amp; Findings
              </h2>
              {report.questions_and_findings.length === 0 ? (
                <p className="text-[var(--fv-text-muted)]">
                  No research findings available.
                </p>
              ) : (
                <div className="space-y-10">
                  {report.questions_and_findings.map((qf) => (
                    <div key={qf.question_id}>
                      <h3 className="mb-4 text-[18px] font-semibold leading-snug text-[var(--fv-text)]">
                        {qf.question}
                      </h3>
                      <div className="space-y-6">
                        {qf.findings.map((finding) => (
                          <div
                            key={`${finding.question_id}-${finding.claim}`}
                            className="border-l-2 border-[var(--fv-accent)]/30 pl-5"
                          >
                            <p className="font-medium text-[var(--fv-text)]">
                              {finding.claim}
                            </p>
                            <p className="mt-2 whitespace-pre-wrap">
                              {finding.evidence_summary}
                            </p>
                            <p className="mt-2 text-[14px] text-[var(--fv-text-muted)]">
                              {confidenceLabel(finding.confidence)} —{" "}
                              {finding.confidence_rationale}
                            </p>
                            {finding.citations.length > 0 && (
                              <ul className="mt-3 space-y-1 text-[14px]">
                                {finding.citations.map((citation) => (
                                  <li key={citation.url || citation.title}>
                                    <SafeCitationLink citation={citation} />
                                  </li>
                                ))}
                              </ul>
                            )}
                          </div>
                        ))}
                        {qf.evidence_gap && (
                          <p className="text-[14px] text-[var(--fv-warning)]">
                            Evidence gap: {qf.evidence_gap}
                          </p>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </section>

            <section>
              <h2 className="mb-4 text-[22px] font-semibold leading-tight text-[var(--fv-text)]">
                Competitor Landscape
              </h2>
              {report.competitors.length === 0 ? (
                <p className="text-[var(--fv-text-muted)]">
                  No competitors identified.
                </p>
              ) : (
                <div className="overflow-hidden rounded-xl border border-[var(--fv-border)]">
                  <table className="w-full border-collapse text-left text-[15px]">
                    <thead>
                      <tr className="border-b border-[var(--fv-border)] bg-[var(--fv-surface)]">
                        <th className="px-4 py-3 font-semibold text-[var(--fv-text)]">
                          Competitor
                        </th>
                        <th className="px-4 py-3 font-semibold text-[var(--fv-text)]">
                          Description
                        </th>
                        <th className="hidden px-4 py-3 font-semibold text-[var(--fv-text)] sm:table-cell">
                          Gap vs. your idea
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {report.competitors.map((comp) => (
                        <tr
                          key={comp.name}
                          className="border-b border-[var(--fv-border)] last:border-b-0"
                        >
                          <td className="align-top px-4 py-4 font-medium text-[var(--fv-text)]">
                            {comp.name}
                          </td>
                          <td className="align-top px-4 py-4 whitespace-pre-wrap">
                            {comp.description}
                          </td>
                          <td className="hidden align-top px-4 py-4 whitespace-pre-wrap sm:table-cell">
                            {comp.positioning_vs_idea}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </section>

            <section>
              <h2 className="mb-4 text-[22px] font-semibold leading-tight text-[var(--fv-text)]">
                Market Signals
              </h2>
              <div className="space-y-6">
                {(
                  [
                    ["Market overview", report.market_signals],
                    ["Distribution", report.distribution_signals],
                    ["Regulatory", report.regulatory_signals],
                  ] as const
                ).map(([label, text]) =>
                  text ? (
                    <div key={label}>
                      <h3 className="mb-2 text-[17px] font-medium text-[var(--fv-text)]">
                        {label}
                      </h3>
                      <p className="whitespace-pre-wrap">{text}</p>
                    </div>
                  ) : null,
                )}
                {!report.market_signals &&
                  !report.distribution_signals &&
                  !report.regulatory_signals && (
                    <p className="text-[var(--fv-text-muted)]">
                      No market signals available.
                    </p>
                  )}
              </div>
            </section>

            <section>
              <h2 className="mb-4 text-[22px] font-semibold leading-tight text-[var(--fv-text)]">
                Risks
              </h2>
              {risks.length === 0 ? (
                <p className="text-[var(--fv-text-muted)]">
                  No significant risks identified.
                </p>
              ) : (
                <ul className="space-y-4">
                  {risks.map((risk, index) => {
                    const severity = inferRiskSeverity(risk, index);
                    return (
                      <li
                        key={`${index}-${risk.slice(0, 32)}`}
                        className="flex items-start gap-3"
                      >
                        <span
                          className={`mt-1 shrink-0 ${severityBadgeClass(severity)}`}
                        >
                          {severity}
                        </span>
                        <p className="whitespace-pre-wrap">{risk}</p>
                      </li>
                    );
                  })}
                </ul>
              )}
            </section>

            <section>
              <h2 className="mb-4 text-[22px] font-semibold leading-tight text-[var(--fv-text)]">
                Citations
              </h2>
              {citations.length === 0 ? (
                <p className="text-[var(--fv-text-muted)]">
                  No citations available.
                </p>
              ) : (
                <ol className="space-y-3">
                  {citations.map((citation, index) => (
                    <li
                      key={`${citation.url}-${index}`}
                      className="flex items-start gap-3 text-[15px]"
                    >
                      <span className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-[var(--fv-accent)] text-[11px] font-bold text-[var(--fv-on-accent)]">
                        {index + 1}
                      </span>
                      <div className="min-w-0 flex-1">
                        <SafeCitationLink citation={citation} />
                        {citation.source_domain && (
                          <p className="mt-0.5 text-[13px] text-[var(--fv-text-muted)]">
                            {citation.source_domain}
                          </p>
                        )}
                      </div>
                    </li>
                  ))}
                </ol>
              )}
            </section>

            {report.research_limitations && (
              <section>
                <h2 className="mb-4 text-[22px] font-semibold leading-tight text-[var(--fv-text)]">
                  Research Limitations
                </h2>
                <p className="whitespace-pre-wrap text-[15px] text-[var(--fv-text-muted)]">
                  {report.research_limitations}
                </p>
              </section>
            )}
          </article>
        )}
      </div>
    </div>
  );
}
