"use client";

import { useEffect, useState } from "react";
import {
  ChevronDown,
  ChevronRight,
  ExternalLink,
  Loader2,
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

function SafeCitationLink({ citation }: { citation: Citation }) {
  if (!isSafeHttpUrl(citation.url)) {
    return (
      <span className="text-sm text-[var(--fv-text-muted)]">
        {citation.title} ({citation.source_domain})
      </span>
    );
  }

  return (
    <a
      href={citation.url}
      target="_blank"
      rel="noopener noreferrer"
      className="inline-flex items-center gap-1 text-sm text-[var(--fv-accent)] hover:text-[var(--fv-accent-hover)] hover:underline"
    >
      {citation.title}
      <ExternalLink className="h-3.5 w-3.5 shrink-0" />
      <span className="text-[var(--fv-text-muted)]">({citation.source_domain})</span>
    </a>
  );
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

function recommendationClass(rec: OverallRecommendation): string {
  switch (rec) {
    case "proceed":
      return "bg-[rgba(16,185,129,0.15)] text-[var(--fv-success)] ring-[rgba(16,185,129,0.3)]";
    case "iterate":
      return "bg-[var(--fv-accent-muted)] text-[var(--fv-accent)] ring-[color-mix(in_srgb,var(--fv-accent)_30%,transparent)]";
    case "pivot":
      return "bg-[rgba(245,158,11,0.15)] text-[var(--fv-warning)] ring-[rgba(245,158,11,0.3)]";
    case "kill":
      return "bg-[rgba(239,68,68,0.15)] text-red-300 ring-[rgba(239,68,68,0.3)]";
    case "too_vague_to_recommend":
      return "bg-[var(--fv-hover-overlay)] text-[var(--fv-text-soft)] ring-[var(--fv-border)]";
  }
}

function formatRecommendation(rec: OverallRecommendation): string {
  return rec
    .split("_")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
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
      <p className="whitespace-pre-wrap text-sm font-medium text-[var(--fv-text)]">
        {finding.claim}
      </p>
      <p className="mt-2 whitespace-pre-wrap text-sm text-[var(--fv-text-soft)]">
        {finding.evidence_summary}
      </p>
      <p className="mt-2 whitespace-pre-wrap text-xs text-[var(--fv-text-muted)]">
        {finding.confidence_rationale}
      </p>
      {finding.citations.length > 0 && (
        <ul className="mt-3 space-y-1.5 border-t border-[var(--fv-border)] pt-3">
          {finding.citations.map((citation) => (
            <li key={`${citation.url}-${citation.title}`}>
              <SafeCitationLink citation={citation} />
            </li>
          ))}
        </ul>
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
        <span className="text-sm font-semibold text-[var(--fv-text)]">
          {question.question}
        </span>
      </button>
      {open && (
        <div className="space-y-3 pb-4 pl-7">
          {question.findings.map((finding) => (
            <FindingCard key={`${finding.question_id}-${finding.claim}`} finding={finding} />
          ))}
          {question.evidence_gap && (
            <p className="whitespace-pre-wrap text-xs text-[var(--fv-warning)]">
              Evidence gap: {question.evidence_gap}
            </p>
          )}
        </div>
      )}
    </div>
  );
}

interface ValidationReportViewerProps {
  experimentId: string;
  onGenerateLandingPage?: () => void;
  generatingLandingPage?: boolean;
}

export function ValidationReportViewer({
  experimentId,
  onGenerateLandingPage,
  generatingLandingPage = false,
}: ValidationReportViewerProps) {
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

    load();
    return () => {
      cancelled = true;
    };
  }, [experimentId]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="h-6 w-6 animate-spin text-[var(--fv-accent)]" />
      </div>
    );
  }

  if (error || !report) {
    return (
      <div className="fv-error px-6 py-8 text-center">
        <p className="text-sm">
          {error ?? "Validation report not available."}
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <section className="fv-card p-6">
        <h2 className="text-lg font-semibold text-[var(--fv-text)]">
          Executive summary
        </h2>
        <p className="mt-3 whitespace-pre-wrap text-sm leading-relaxed text-[var(--fv-text-soft)]">
          {report.executive_summary}
        </p>
        {report.market_signals && (
          <>
            <h3 className="mt-6 text-sm font-semibold text-[var(--fv-text)]">
              Market signals
            </h3>
            <p className="mt-2 whitespace-pre-wrap text-sm leading-relaxed text-[var(--fv-text-muted)]">
              {report.market_signals}
            </p>
          </>
        )}
      </section>

      <section className="fv-card px-6">
        <h2 className="border-b border-[var(--fv-border)] py-4 text-lg font-semibold text-[var(--fv-text)]">
          Research questions & findings
        </h2>
        {report.questions_and_findings.map((qf, i) => (
          <QuestionSection key={qf.question_id} question={qf} defaultOpen={i === 0} />
        ))}
      </section>

      {report.competitors.length > 0 && (
        <section className="fv-card p-6">
          <h2 className="text-lg font-semibold text-[var(--fv-text)]">Competitors</h2>
          <ul className="mt-4 space-y-4">
            {report.competitors.map((comp) => (
              <li
                key={comp.name}
                className="fv-card p-4"
              >
                <p className="font-medium text-[var(--fv-text)]">{comp.name}</p>
                <p className="mt-1 whitespace-pre-wrap text-sm text-[var(--fv-text-soft)]">
                  {comp.description}
                </p>
                <p className="mt-2 whitespace-pre-wrap text-sm text-[var(--fv-text-soft)]">
                  {comp.positioning_vs_idea}
                </p>
                {comp.citations.length > 0 && (
                  <ul className="mt-3 space-y-1">
                    {comp.citations.map((citation) => (
                      <li key={`${comp.name}-${citation.url}`}>
                        <SafeCitationLink citation={citation} />
                      </li>
                    ))}
                  </ul>
                )}
              </li>
            ))}
          </ul>
        </section>
      )}

      <section className="fv-card p-6">
        <h2 className="text-lg font-semibold text-[var(--fv-text)]">Risks</h2>
        <p className="mt-3 whitespace-pre-wrap text-sm leading-relaxed text-[var(--fv-text-soft)]">
          {report.risks_assessment}
        </p>
      </section>

      <section className="fv-card p-6">
        <h2 className="text-lg font-semibold text-[var(--fv-text)]">Recommendation</h2>
        <span
          className={`mt-3 inline-flex rounded-full px-3 py-1 text-sm font-semibold ring-1 ring-inset ${recommendationClass(report.overall_recommendation)}`}
        >
          {formatRecommendation(report.overall_recommendation)}
        </span>
        <p className="mt-4 whitespace-pre-wrap text-sm leading-relaxed text-[var(--fv-text-soft)]">
          {report.recommendation_rationale}
        </p>
        {report.research_limitations && (
          <p className="mt-4 whitespace-pre-wrap text-xs text-[var(--fv-text-muted)]">
            Limitations: {report.research_limitations}
          </p>
        )}
      </section>

      {onGenerateLandingPage && (
        <div className="flex justify-end">
          <button
            type="button"
            onClick={onGenerateLandingPage}
            disabled={generatingLandingPage}
            className="fv-btn-primary px-5 py-2.5 text-sm disabled:cursor-not-allowed"
          >
            {generatingLandingPage && (
              <Loader2 className="h-4 w-4 animate-spin" />
            )}
            Generate Landing Page
          </button>
        </div>
      )}
    </div>
  );
}
