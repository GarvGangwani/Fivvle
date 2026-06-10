"use client";

import { useEffect, useState, type ReactNode } from "react";
import { ArrowLeft, X } from "lucide-react";
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

function SafeCitationLink({ citation }: { citation: Citation }) {
  if (!isSafeHttpUrl(citation.url)) {
    return (
      <span className="text-[var(--fv-text)]">{citation.title}</span>
    );
  }

  return (
    <a
      href={citation.url}
      target="_blank"
      rel="noopener noreferrer"
      className="text-[var(--fv-accent)] no-underline hover:underline"
    >
      {citation.title}
    </a>
  );
}

function CitationSuperscript({ index }: { index: number }) {
  return (
    <a
      href={`#citation-${index}`}
      className="ml-0.5 align-super text-[11px] text-[var(--fv-accent)] no-underline hover:underline"
    >
      {index}
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

function formatRiskSeverity(severity: "high" | "medium" | "low"): string {
  return `${severity.charAt(0).toUpperCase()}${severity.slice(1)} risk`;
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

function parseBulletLines(text: string): string[] {
  return text
    .split("\n")
    .map((line) => line.replace(/^[-*•]\s*/, "").trim())
    .filter(Boolean);
}

function ReportSectionHeader({ title }: { title: string }) {
  return (
    <h2 className="mb-6 text-xl font-semibold tracking-[-0.02em] text-[var(--fv-text)]">
      {title}
    </h2>
  );
}

function CollapsibleSection({
  toggleLabel,
  children,
}: {
  toggleLabel: string;
  children: ReactNode;
}) {
  const [open, setOpen] = useState(false);

  return (
    <section className="mt-16 border-t border-[var(--fv-border)] pt-16">
      <button
        type="button"
        onClick={() => setOpen((prev) => !prev)}
        className="mb-6 text-[15px] text-[var(--fv-text-soft)] hover:text-[var(--fv-text)]"
      >
        {open ? toggleLabel.replace("▾", "▴") : toggleLabel}
      </button>
      {open && children}
    </section>
  );
}

function ReportLoadingSkeleton() {
  return (
    <div className="space-y-3">
      <div className="fv-skeleton h-6 w-48 rounded" />
      <div className="fv-skeleton h-4 w-full rounded" />
      <div className="fv-skeleton h-4 w-full rounded" />
      <div className="fv-skeleton h-4 w-2/3 rounded" />
    </div>
  );
}

function FindingItem({
  finding,
  citationIndexMap,
}: {
  finding: Finding;
  citationIndexMap: Map<string, number>;
}) {
  return (
    <>
      <p className="mb-4 text-[15px] leading-[1.8] text-[var(--fv-text-soft)]">
        {finding.claim}
        <span className="ml-2 text-[12px] text-[var(--fv-text-dim)]">
          {finding.confidence}
        </span>
      </p>
      {(finding.evidence_summary || finding.citations.length > 0) && (
        <p className="mb-4 text-[14px] leading-[1.8] text-[var(--fv-text-dim)]">
          {finding.evidence_summary}
          {finding.citations.map((citation) => {
            const key = citation.url || citation.title;
            const index = citationIndexMap.get(key);
            if (!index) return null;
            return <CitationSuperscript key={key} index={index} />;
          })}
        </p>
      )}
      {finding.confidence_rationale && (
        <p className="mb-4 text-[14px] leading-[1.8] text-[var(--fv-text-dim)]">
          {finding.confidence_rationale}
        </p>
      )}
    </>
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
  const citationIndexMap = buildCitationIndexMap(citations);
  const risks = report ? parseBulletLines(report.risks_assessment) : [];
  const showRecommendation =
    report &&
    report.overall_recommendation !== "too_vague_to_recommend";

  const hasMarketSignals =
    report &&
    (report.market_signals ||
      report.distribution_signals ||
      report.regulatory_signals);

  return (
    <div className="flex h-full min-h-0 flex-col">
      <header className="sticky top-0 z-10 flex shrink-0 items-center justify-between border-b border-[var(--fv-border)] bg-[var(--fv-bg)]/95 px-8 py-3 backdrop-blur-sm">
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
          <h1 className="truncate text-[17px] font-semibold text-[var(--fv-text)]">
            Validation Report
          </h1>
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

      <div className="min-h-0 flex-1 overflow-y-auto bg-[var(--fv-bg)]">
        <div className="mx-auto max-w-[680px] px-8 py-8">
          {loading && <ReportLoadingSkeleton />}

          {error && !loading && (
            <div className="fv-error text-sm">{error}</div>
          )}

          {report && !loading && (
            <article>
              <div>
                {showRecommendation && report.recommendation_rationale && (
                  <p className="mb-4 text-[15px] leading-[1.8] text-[var(--fv-text-soft)]">
                    <span
                      className={`mr-2 inline-flex !px-1.5 !py-px !text-[10px] !font-semibold ${recommendationBadgeClass(
                        report.overall_recommendation,
                      )}`}
                    >
                      {formatRecommendation(report.overall_recommendation)}
                    </span>
                    {report.recommendation_rationale}
                  </p>
                )}
                {showRecommendation && !report.recommendation_rationale && (
                  <p className="mb-4 text-[15px] leading-[1.8] text-[var(--fv-text-soft)]">
                    <span
                      className={`inline-flex !px-1.5 !py-px !text-[10px] !font-semibold ${recommendationBadgeClass(
                        report.overall_recommendation,
                      )}`}
                    >
                      {formatRecommendation(report.overall_recommendation)}
                    </span>
                  </p>
                )}
                {!showRecommendation && report.recommendation_rationale && (
                  <p className="mb-4 text-[15px] leading-[1.8] text-[var(--fv-text-soft)]">
                    {report.recommendation_rationale}
                  </p>
                )}
                <p className="whitespace-pre-wrap text-[15px] leading-[1.8] text-[var(--fv-text-soft)]">
                  {report.executive_summary}
                </p>
              </div>

              <section className="mt-16 border-t border-[var(--fv-border)] pt-16">
                <ReportSectionHeader title="Research Questions & Findings" />
                {report.questions_and_findings.length === 0 ? (
                  <p className="text-[var(--fv-text-muted)]">
                    No research findings available.
                  </p>
                ) : (
                  <>
                    {report.questions_and_findings.map((qf, qfIndex) => (
                      <div
                        key={qf.question_id}
                        className={
                          qfIndex > 0
                            ? "mt-8 border-t border-[var(--fv-border)] pt-8"
                            : undefined
                        }
                      >
                        <h3 className="mb-4 text-[17px] font-medium text-[var(--fv-text)]">
                          {qf.question}
                        </h3>
                        {qf.findings.map((finding) => (
                          <div
                            key={`${finding.question_id}-${finding.claim}`}
                            className="mb-8"
                          >
                            <FindingItem
                              finding={finding}
                              citationIndexMap={citationIndexMap}
                            />
                          </div>
                        ))}
                        {qf.evidence_gap && (
                          <p className="mb-4 text-[14px] leading-[1.8] text-[var(--fv-text-muted)]">
                            Evidence gap: {qf.evidence_gap}
                          </p>
                        )}
                      </div>
                    ))}
                  </>
                )}
              </section>

              <section className="mt-16 border-t border-[var(--fv-border)] pt-16">
                <ReportSectionHeader title="Competitor Landscape" />
                {report.competitors.length === 0 ? (
                  <p className="text-[var(--fv-text-muted)]">
                    No competitors identified.
                  </p>
                ) : (
                  <>
                    {report.competitors.map((comp) => (
                      <p
                        key={comp.name}
                        className="mb-6 text-[15px] leading-[1.8] text-[var(--fv-text-soft)]"
                      >
                        <span className="font-medium text-[var(--fv-text)]">
                          {comp.name}
                        </span>
                        {" — "}
                        {comp.description}
                        {comp.positioning_vs_idea && (
                          <>
                            {" "}
                            {comp.positioning_vs_idea}
                          </>
                        )}
                      </p>
                    ))}
                  </>
                )}
              </section>

              <section className="mt-16 border-t border-[var(--fv-border)] pt-16">
                <ReportSectionHeader title="Risks" />
                {risks.length === 0 ? (
                  <p className="text-[var(--fv-text-muted)]">
                    No significant risks identified.
                  </p>
                ) : (
                  <>
                    {risks.map((risk, index) => {
                      const severity = inferRiskSeverity(risk, index);
                      return (
                        <p
                          key={`${index}-${risk.slice(0, 32)}`}
                          className="mb-4 text-[15px] leading-[1.8] text-[var(--fv-text-soft)] whitespace-pre-wrap"
                        >
                          <span className="font-bold">
                            {formatRiskSeverity(severity)}
                          </span>
                          {" — "}
                          {risk}
                        </p>
                      );
                    })}
                  </>
                )}
              </section>

              <section className="mt-16 border-t border-[var(--fv-border)] pt-16">
                <ReportSectionHeader title="Citations" />
                {citations.length === 0 ? (
                  <p className="text-[var(--fv-text-muted)]">
                    No citations available.
                  </p>
                ) : (
                  <ol className="list-none">
                    {citations.map((citation, index) => (
                      <li
                        key={`${citation.url}-${index}`}
                        id={`citation-${index + 1}`}
                        className="mb-1 text-[13px] leading-[1.6]"
                      >
                        <span className="text-[var(--fv-text-muted)]">
                          {index + 1}.{" "}
                        </span>
                        <SafeCitationLink citation={citation} />
                        {citation.source_domain && (
                          <span className="text-[var(--fv-text-muted)]">
                            {" "}
                            {citation.source_domain}
                          </span>
                        )}
                      </li>
                    ))}
                  </ol>
                )}
              </section>

              {hasMarketSignals && (
                <CollapsibleSection toggleLabel="Show market signals ▾">
                  <div>
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
                        <div key={label} className="mb-8">
                          <h3 className="mb-4 text-[15px] font-medium text-[var(--fv-text)]">
                            {label}
                          </h3>
                          {items.map((item, index) => (
                            <p
                              key={`${label}-${index}`}
                              className="mb-4 text-[15px] leading-[1.8] text-[var(--fv-text-soft)] whitespace-pre-wrap"
                            >
                              {item}
                            </p>
                          ))}
                        </div>
                      );
                    })}
                  </div>
                </CollapsibleSection>
              )}

              {report.research_limitations && (
                <CollapsibleSection toggleLabel="Show limitations ▾">
                  <p className="whitespace-pre-wrap text-[15px] leading-[1.8] text-[var(--fv-text-muted)]">
                    {report.research_limitations}
                  </p>
                </CollapsibleSection>
              )}
            </article>
          )}
        </div>
      </div>
    </div>
  );
}
