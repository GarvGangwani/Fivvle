"use client";

import { useEffect, useRef, useState } from "react";
import {
  ArrowLeft,
  ExternalLink,
  FileText,
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
  compact = false,
}: {
  citation: Citation;
  index?: number;
  compact?: boolean;
}) {
  const label = index != null ? `[${index}] ` : "";
  const className = compact
    ? "inline-flex items-center gap-1 text-[13px] text-[var(--fv-accent)] no-underline hover:underline"
    : "inline-flex items-center gap-1 text-[var(--fv-accent)] no-underline hover:text-[var(--fv-accent-hover)]";

  if (!isSafeHttpUrl(citation.url)) {
    return (
      <span className={compact ? "text-[13px] text-[var(--fv-text-muted)]" : "text-[var(--fv-text-muted)]"}>
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
      className={className}
    >
      {label}
      {citation.title}
      {!compact && <ExternalLink className="h-3.5 w-3.5 shrink-0" />}
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
      return "bg-white/10 text-[var(--fv-text-soft)] ring-white/10";
  }
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

function riskCardClass(severity: "high" | "medium" | "low"): string {
  switch (severity) {
    case "high":
      return "border-l-4 border-[var(--fv-danger)] bg-[var(--fv-danger)]/5";
    case "medium":
      return "border-l-4 border-[var(--fv-warning)] bg-[var(--fv-warning)]/5";
    case "low":
      return "border-l-4 border-[var(--fv-success)] bg-[var(--fv-success)]/5";
  }
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

function inferSignalStrength(text: string): "positive" | "neutral" | "negative" {
  const lower = text.toLowerCase();
  if (
    /declin|risk|crowded|saturat|barrier|restrict|uncertain|weak|challeng|difficult|limited/.test(
      lower,
    )
  ) {
    return "negative";
  }
  if (
    /grow|strong|demand|opportun|momentum|increas|expand|favorable|positive|emerging/.test(
      lower,
    )
  ) {
    return "positive";
  }
  return "neutral";
}

function signalDotClass(strength: "positive" | "neutral" | "negative"): string {
  switch (strength) {
    case "positive":
      return "bg-[var(--fv-success)]";
    case "negative":
      return "bg-[var(--fv-danger)]";
    case "neutral":
      return "bg-[var(--fv-warning)]";
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

function parseBulletLines(text: string): string[] {
  return text
    .split("\n")
    .map((line) => line.replace(/^[-*•]\s*/, "").trim())
    .filter(Boolean);
}

function ReportSectionHeader({
  number,
  title,
}: {
  number: string;
  title: string;
}) {
  return (
    <header>
      <p className="mb-2 text-[12px] font-semibold uppercase tracking-[0.1em] text-[var(--fv-accent)]">
        Section {number}
      </p>
      <h2 className="text-2xl font-semibold tracking-[-0.02em] text-[var(--fv-text)]">
        {title}
      </h2>
      <div className="mb-8 mt-4 h-px bg-[var(--fv-border)]" />
    </header>
  );
}

function ReportLoadingSkeleton() {
  return (
    <div className="mx-auto max-w-[800px] space-y-16 rounded-2xl border border-[var(--fv-border)] bg-[var(--fv-surface)] px-10 py-12 shadow-[0_1px_2px_rgba(0,0,0,0.12)]">
      <div className="space-y-4">
        <div className="fv-skeleton h-3 w-24 rounded" />
        <div className="fv-skeleton h-8 w-64 rounded-lg" />
        <div className="fv-skeleton h-px w-full rounded" />
        <div className="fv-skeleton h-28 w-full rounded-xl" />
        <div className="space-y-2 pt-2">
          <div className="fv-skeleton h-4 w-full rounded" />
          <div className="fv-skeleton h-4 w-full rounded" />
          <div className="fv-skeleton h-4 w-5/6 rounded" />
        </div>
      </div>
      <div className="space-y-4">
        <div className="fv-skeleton h-3 w-24 rounded" />
        <div className="fv-skeleton h-8 w-72 rounded-lg" />
        <div className="fv-skeleton h-px w-full rounded" />
        <div className="fv-skeleton h-48 w-full rounded-xl" />
        <div className="fv-skeleton h-48 w-full rounded-xl" />
      </div>
      <div className="space-y-4">
        <div className="fv-skeleton h-3 w-24 rounded" />
        <div className="fv-skeleton h-8 w-56 rounded-lg" />
        <div className="fv-skeleton h-px w-full rounded" />
        <div className="fv-skeleton h-40 w-full rounded-xl" />
      </div>
    </div>
  );
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
  const [headerScrolled, setHeaderScrolled] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

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

  function handleScroll() {
    const el = scrollRef.current;
    if (!el) return;
    setHeaderScrolled(el.scrollTop > 4);
  }

  const citations = report ? collectAllCitations(report) : [];
  const risks = report ? parseBulletLines(report.risks_assessment) : [];
  const showRecommendation =
    report &&
    report.overall_recommendation !== "too_vague_to_recommend";

  return (
    <div className="flex h-full min-h-0 flex-col">
      <header
        className={`sticky top-0 z-10 flex shrink-0 items-center justify-between border-b border-[var(--fv-border)] bg-[var(--fv-bg)] px-8 py-4 transition-shadow ${
          headerScrolled ? "shadow-[0_1px_3px_rgba(0,0,0,0.3)]" : ""
        }`}
      >
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
          <div className="flex min-w-0 items-center gap-3">
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-[var(--fv-border)] bg-[var(--fv-surface)] text-[var(--fv-accent)]">
              <FileText className="h-4 w-4" />
            </div>
            <h1 className="truncate text-[17px] font-semibold text-[var(--fv-text)]">
              Validation Report
            </h1>
          </div>
        </div>
        <div className="flex shrink-0 items-center gap-3">
          {report && showRecommendation && (
            <span
              className={`hidden sm:inline-flex ${recommendationBadgeClass(
                report.overall_recommendation,
              )}`}
            >
              {formatRecommendation(report.overall_recommendation)}
            </span>
          )}
          <button
            type="button"
            onClick={onClose}
            className="icon-btn shrink-0"
            aria-label="Close report"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      </header>

      <div
        ref={scrollRef}
        onScroll={handleScroll}
        className="min-h-0 flex-1 overflow-y-auto bg-[var(--fv-bg)]"
      >
        <div className="px-8 py-8">
          {loading && <ReportLoadingSkeleton />}

          {error && !loading && (
            <div className="fv-error mx-auto max-w-[800px] text-sm">{error}</div>
          )}

          {report && !loading && (
            <article className="mx-auto max-w-[800px] space-y-16 rounded-2xl border border-[var(--fv-border)] bg-[var(--fv-surface)] px-10 py-12 shadow-[0_1px_2px_rgba(0,0,0,0.12)]">
              <section>
                <ReportSectionHeader number="01" title="Executive Summary" />
                {showRecommendation && (
                  <div className="mb-8 rounded-xl border border-[var(--fv-border-strong)] bg-[var(--fv-surface)] p-6">
                    <span
                      className={recommendationBadgeClass(
                        report.overall_recommendation,
                      )}
                    >
                      {formatRecommendation(report.overall_recommendation)}
                    </span>
                    {report.recommendation_rationale && (
                      <p className="mt-3 text-[15px] leading-[1.7] text-[var(--fv-text)]">
                        {report.recommendation_rationale}
                      </p>
                    )}
                  </div>
                )}
                {!showRecommendation && report.recommendation_rationale && (
                  <div className="mb-8 rounded-xl border border-[var(--fv-border-strong)] bg-[var(--fv-surface)] p-6">
                    <p className="text-[15px] leading-[1.7] text-[var(--fv-text)]">
                      {report.recommendation_rationale}
                    </p>
                  </div>
                )}
                <p className="whitespace-pre-wrap text-[16px] leading-[1.8] text-[var(--fv-text-soft)]">
                  {report.executive_summary}
                </p>
              </section>

              <section>
                <ReportSectionHeader
                  number="02"
                  title="Research Questions & Findings"
                />
                {report.questions_and_findings.length === 0 ? (
                  <p className="text-[var(--fv-text-muted)]">
                    No research findings available.
                  </p>
                ) : (
                  <div className="space-y-6">
                    {report.questions_and_findings.map((qf) => (
                      <div
                        key={qf.question_id}
                        className="space-y-4 rounded-xl border border-[var(--fv-border)] bg-[var(--fv-surface-2)] p-6"
                      >
                        <h3 className="text-[16px] font-semibold text-[var(--fv-text)]">
                          {qf.question}
                        </h3>
                        <div className="space-y-5">
                          {qf.findings.map((finding) => (
                            <div
                              key={`${finding.question_id}-${finding.claim}`}
                              className="space-y-2 border-l-2 border-[var(--fv-accent)]/30 pl-4"
                            >
                              <p className="text-[15px] leading-[1.7] text-[var(--fv-text)]">
                                {finding.claim}
                              </p>
                              <div>
                                <span
                                  className={`inline-flex rounded-full px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide ring-1 ring-inset ${confidenceClass(finding.confidence)}`}
                                >
                                  {finding.confidence}
                                </span>
                              </div>
                              <p className="text-[14px] italic leading-[1.6] text-[var(--fv-text-muted)]">
                                {finding.evidence_summary}
                              </p>
                              {finding.confidence_rationale && (
                                <p className="text-[13px] text-[var(--fv-text-muted)]">
                                  {finding.confidence_rationale}
                                </p>
                              )}
                              {finding.citations.length > 0 && (
                                <ul className="space-y-1 pt-1">
                                  {finding.citations.map((citation) => (
                                    <li key={citation.url || citation.title}>
                                      <SafeCitationLink
                                        citation={citation}
                                        compact
                                      />
                                    </li>
                                  ))}
                                </ul>
                              )}
                            </div>
                          ))}
                          {qf.evidence_gap && (
                            <p className="rounded-lg border border-[var(--fv-warning)]/20 bg-[var(--fv-warning)]/5 px-4 py-3 text-[14px] text-[var(--fv-warning)]">
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
                <ReportSectionHeader number="03" title="Competitor Landscape" />
                {report.competitors.length === 0 ? (
                  <p className="text-[var(--fv-text-muted)]">
                    No competitors identified.
                  </p>
                ) : (
                  <>
                    <div className="hidden overflow-hidden rounded-xl border border-[var(--fv-border)] lg:block">
                      <table className="w-full border-collapse text-left text-[15px]">
                        <thead>
                          <tr className="border-b border-[var(--fv-border)] bg-[var(--fv-surface)]">
                            <th className="px-5 py-3.5 text-[13px] font-semibold uppercase tracking-wide text-[var(--fv-text-muted)]">
                              Competitor
                            </th>
                            <th className="px-5 py-3.5 text-[13px] font-semibold uppercase tracking-wide text-[var(--fv-text-muted)]">
                              Description
                            </th>
                            <th className="px-5 py-3.5 text-[13px] font-semibold uppercase tracking-wide text-[var(--fv-text-muted)]">
                              Gap vs. your idea
                            </th>
                          </tr>
                        </thead>
                        <tbody>
                          {report.competitors.map((comp, index) => (
                            <tr
                              key={comp.name}
                              className={`border-b border-[var(--fv-border)] last:border-b-0 ${
                                index % 2 === 1
                                  ? "bg-[var(--fv-surface-2)]/40"
                                  : "bg-transparent"
                              }`}
                            >
                              <td className="align-top px-5 py-4 font-semibold text-[var(--fv-text)]">
                                {comp.name}
                              </td>
                              <td className="align-top px-5 py-4 leading-[1.6] text-[var(--fv-text-soft)] whitespace-pre-wrap">
                                {comp.description}
                              </td>
                              <td className="align-top px-5 py-4 leading-[1.6] text-[var(--fv-text-soft)] whitespace-pre-wrap">
                                {comp.positioning_vs_idea}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                    <div className="grid grid-cols-1 gap-4 lg:hidden">
                      {report.competitors.map((comp) => (
                        <div
                          key={comp.name}
                          className="rounded-xl border border-[var(--fv-border)] p-5"
                        >
                          <p className="font-semibold text-[var(--fv-text)]">
                            {comp.name}
                          </p>
                          <p className="mt-2 text-[14px] leading-[1.6] text-[var(--fv-text-soft)] whitespace-pre-wrap">
                            {comp.description}
                          </p>
                          <p className="mt-3 text-[12px] font-semibold uppercase tracking-wide text-[var(--fv-text-muted)]">
                            Gap vs. your idea
                          </p>
                          <p className="mt-1 text-[14px] leading-[1.6] text-[var(--fv-text-soft)] whitespace-pre-wrap">
                            {comp.positioning_vs_idea}
                          </p>
                        </div>
                      ))}
                    </div>
                  </>
                )}
              </section>

              <section>
                <ReportSectionHeader number="04" title="Market Signals" />
                <div className="space-y-8">
                  {(
                    [
                      ["Market overview", report.market_signals],
                      ["Distribution", report.distribution_signals],
                      ["Regulatory", report.regulatory_signals],
                    ] as const
                  ).map(([label, text]) => {
                    if (!text) return null;
                    const lines = parseBulletLines(text);
                    const items = lines.length > 1 ? lines : [text];

                    return (
                      <div key={label}>
                        <h3 className="mb-4 text-[15px] font-semibold text-[var(--fv-text)]">
                          {label}
                        </h3>
                        <ul className="space-y-3">
                          {items.map((item, index) => {
                            const strength = inferSignalStrength(item);
                            return (
                              <li
                                key={`${label}-${index}`}
                                className="flex items-start gap-3"
                              >
                                <span
                                  className={`mt-2 h-2.5 w-2.5 shrink-0 rounded-full ${signalDotClass(strength)}`}
                                  aria-hidden
                                />
                                <p className="text-[15px] leading-[1.7] text-[var(--fv-text-soft)] whitespace-pre-wrap">
                                  {item}
                                </p>
                              </li>
                            );
                          })}
                        </ul>
                      </div>
                    );
                  })}
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
                <ReportSectionHeader number="05" title="Risks" />
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
                          className={`rounded-r-xl py-4 pl-5 pr-5 ${riskCardClass(severity)}`}
                        >
                          <div className="flex items-start gap-3">
                            <span
                              className={`mt-0.5 shrink-0 ${severityBadgeClass(severity)}`}
                            >
                              {severity}
                            </span>
                            <p className="text-[15px] leading-[1.7] text-[var(--fv-text-soft)] whitespace-pre-wrap">
                              {risk}
                            </p>
                          </div>
                        </li>
                      );
                    })}
                  </ul>
                )}
              </section>

              <section>
                <ReportSectionHeader number="06" title="Citations" />
                {citations.length === 0 ? (
                  <p className="text-[var(--fv-text-muted)]">
                    No citations available.
                  </p>
                ) : (
                  <ol className="space-y-4">
                    {citations.map((citation, index) => (
                      <li
                        key={`${citation.url}-${index}`}
                        className="flex items-start gap-3"
                      >
                        <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-[var(--fv-surface-2)] text-center text-[12px] font-medium text-[var(--fv-text-muted)] ring-1 ring-[var(--fv-border)]">
                          {index + 1}
                        </span>
                        <div className="min-w-0 flex-1 pt-0.5">
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
                  <ReportSectionHeader
                    number="07"
                    title="Research Limitations"
                  />
                  <p className="whitespace-pre-wrap text-[15px] leading-[1.7] text-[var(--fv-text-muted)]">
                    {report.research_limitations}
                  </p>
                </section>
              )}
            </article>
          )}
        </div>
      </div>
    </div>
  );
}
