"use client";

import { useEffect, useState } from "react";
import {
  AlertTriangle,
  ExternalLink,
  Loader2,
  X,
} from "lucide-react";
import { getValidationReport, ApiError } from "@/lib/api";
import type {
  Citation,
  OverallRecommendation,
  ValidationReport,
} from "@/lib/types";

const REPORT_TABS = [
  "Summary",
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

function parseSignalLines(text: string | null): { label: string; value: string }[] {
  if (!text?.trim()) return [];
  return text
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => {
      const colonIdx = line.indexOf(":");
      if (colonIdx > 0) {
        return {
          label: line.slice(0, colonIdx).trim(),
          value: line.slice(colonIdx + 1).trim(),
        };
      }
      return { label: line, value: "" };
    });
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

  return (
    <>
      <div
        className={`report-panel-backdrop ${open ? "open" : ""}`}
        onClick={onClose}
        aria-hidden={!open}
      />

      <aside
        className={`report-panel ${open ? "open" : ""}`}
        role="dialog"
        aria-modal="true"
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

          {report && !loading && activeTab === "Summary" && (
            <div className="space-y-5">
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
                <p className="text-[13px] font-semibold text-[#34D399]">
                  Recommendation: {formatRecommendation(report.overall_recommendation)}
                </p>
                <p className="mt-2 whitespace-pre-wrap text-[13px] leading-relaxed text-[var(--fv-text-soft)]">
                  {report.recommendation_rationale}
                </p>
              </div>

              {report.market_signals && (
                <div>
                  <h3 className="fv-panel-label mb-3">Market Signals</h3>
                  <div className="grid grid-cols-2 gap-3">
                    {parseSignalLines(report.market_signals)
                      .slice(0, 4)
                      .map((signal) => (
                        <div key={signal.label} className="analytics-card">
                          <p className="text-2xl font-bold text-[var(--fv-accent)]">
                            {signal.value || "—"}
                          </p>
                          <p className="mt-1 text-[12px] text-[var(--fv-text-muted)]">
                            {signal.label}
                          </p>
                        </div>
                      ))}
                  </div>
                </div>
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
              ).map(([group, text]) => {
                const lines = parseSignalLines(text);
                return (
                  <div key={group}>
                    <h3 className="fv-panel-label mb-3">{group}</h3>
                    {lines.length === 0 ? (
                      <span className="unavailable-badge">Data unavailable</span>
                    ) : (
                      <div className="space-y-2">
                        {lines.map((line) => (
                          <div
                            key={`${group}-${line.label}`}
                            className="flex items-start justify-between gap-3 rounded-lg px-3 py-2"
                            style={{ background: "rgba(255,255,255,0.02)" }}
                          >
                            <span className="text-[13px] text-[var(--fv-text-soft)]">
                              {line.label}
                            </span>
                            <span className="text-[13px] font-medium text-[var(--fv-text)]">
                              {line.value || "—"}
                            </span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                );
              })}
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
                      className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-[11px] font-bold text-[#080C14]"
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
      </aside>
    </>
  );
}
