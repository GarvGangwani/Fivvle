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
      <span className="text-sm text-gray-500">
        {citation.title} ({citation.source_domain})
      </span>
    );
  }

  return (
    <a
      href={citation.url}
      target="_blank"
      rel="noopener noreferrer"
      className="inline-flex items-center gap-1 text-sm text-blue-700 hover:text-blue-900 hover:underline"
    >
      {citation.title}
      <ExternalLink className="h-3.5 w-3.5 shrink-0" />
      <span className="text-gray-400">({citation.source_domain})</span>
    </a>
  );
}

function confidenceClass(confidence: Finding["confidence"]): string {
  switch (confidence) {
    case "high":
      return "bg-green-100 text-green-800 ring-green-200";
    case "medium":
      return "bg-yellow-100 text-yellow-800 ring-yellow-200";
    case "low":
      return "bg-gray-100 text-gray-700 ring-gray-200";
  }
}

function recommendationClass(rec: OverallRecommendation): string {
  switch (rec) {
    case "proceed":
      return "bg-green-100 text-green-800 ring-green-200";
    case "iterate":
      return "bg-blue-100 text-blue-800 ring-blue-200";
    case "pivot":
      return "bg-yellow-100 text-yellow-800 ring-yellow-200";
    case "kill":
      return "bg-red-100 text-red-800 ring-red-200";
    case "too_vague_to_recommend":
      return "bg-gray-100 text-gray-700 ring-gray-200";
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
    <div className="rounded-lg border border-gray-100 bg-gray-50 p-4">
      <div className="mb-2 flex flex-wrap items-center gap-2">
        <span
          className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset ${confidenceClass(finding.confidence)}`}
        >
          {finding.confidence} confidence
        </span>
      </div>
      <p className="text-sm font-medium text-gray-900 whitespace-pre-wrap">
        {finding.claim}
      </p>
      <p className="mt-2 text-sm text-gray-600 whitespace-pre-wrap">
        {finding.evidence_summary}
      </p>
      <p className="mt-2 text-xs text-gray-400 whitespace-pre-wrap">
        {finding.confidence_rationale}
      </p>
      {finding.citations.length > 0 && (
        <ul className="mt-3 space-y-1.5 border-t border-gray-200 pt-3">
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
    <div className="border-b border-gray-200 last:border-b-0">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-start gap-2 py-4 text-left"
      >
        {open ? (
          <ChevronDown className="mt-0.5 h-5 w-5 shrink-0 text-gray-400" />
        ) : (
          <ChevronRight className="mt-0.5 h-5 w-5 shrink-0 text-gray-400" />
        )}
        <span className="text-sm font-semibold text-gray-900">
          {question.question}
        </span>
      </button>
      {open && (
        <div className="space-y-3 pb-4 pl-7">
          {question.findings.map((finding) => (
            <FindingCard key={`${finding.question_id}-${finding.claim}`} finding={finding} />
          ))}
          {question.evidence_gap && (
            <p className="text-xs text-amber-700 whitespace-pre-wrap">
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
        <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
      </div>
    );
  }

  if (error || !report) {
    return (
      <div className="rounded-xl border border-red-200 bg-red-50 px-6 py-8 text-center">
        <p className="text-sm text-red-700">
          {error ?? "Validation report not available."}
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <section className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
        <h2 className="text-lg font-semibold text-gray-900">
          Executive summary
        </h2>
        <p className="mt-3 text-sm leading-relaxed text-gray-700 whitespace-pre-wrap">
          {report.executive_summary}
        </p>
        {report.market_signals && (
          <>
            <h3 className="mt-6 text-sm font-semibold text-gray-900">
              Market signals
            </h3>
            <p className="mt-2 text-sm leading-relaxed text-gray-600 whitespace-pre-wrap">
              {report.market_signals}
            </p>
          </>
        )}
      </section>

      <section className="rounded-xl border border-gray-200 bg-white px-6 shadow-sm">
        <h2 className="border-b border-gray-200 py-4 text-lg font-semibold text-gray-900">
          Research questions & findings
        </h2>
        {report.questions_and_findings.map((qf, i) => (
          <QuestionSection key={qf.question_id} question={qf} defaultOpen={i === 0} />
        ))}
      </section>

      {report.competitors.length > 0 && (
        <section className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-gray-900">Competitors</h2>
          <ul className="mt-4 space-y-4">
            {report.competitors.map((comp) => (
              <li
                key={comp.name}
                className="rounded-lg border border-gray-100 bg-gray-50 p-4"
              >
                <p className="font-medium text-gray-900">{comp.name}</p>
                <p className="mt-1 text-sm text-gray-600 whitespace-pre-wrap">
                  {comp.description}
                </p>
                <p className="mt-2 text-sm text-gray-700 whitespace-pre-wrap">
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

      <section className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
        <h2 className="text-lg font-semibold text-gray-900">Risks</h2>
        <p className="mt-3 text-sm leading-relaxed text-gray-700 whitespace-pre-wrap">
          {report.risks_assessment}
        </p>
      </section>

      <section className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
        <h2 className="text-lg font-semibold text-gray-900">Recommendation</h2>
        <span
          className={`mt-3 inline-flex rounded-full px-3 py-1 text-sm font-semibold ring-1 ring-inset ${recommendationClass(report.overall_recommendation)}`}
        >
          {formatRecommendation(report.overall_recommendation)}
        </span>
        <p className="mt-4 text-sm leading-relaxed text-gray-700 whitespace-pre-wrap">
          {report.recommendation_rationale}
        </p>
        {report.research_limitations && (
          <p className="mt-4 text-xs text-gray-500 whitespace-pre-wrap">
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
            className="inline-flex items-center gap-2 rounded-lg bg-gray-900 px-5 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-gray-700 disabled:cursor-not-allowed disabled:opacity-50"
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
