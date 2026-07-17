"use client";

import { useEffect, useState } from "react";
import type { OverallRecommendation, ValidationReport } from "@/lib/types";
import { getValidationReport } from "@/lib/api";
import {
  EvidenceReportEditor,
  type EvidenceSelection,
} from "@/components/research/EvidenceReportEditor";
import { EvidenceChatPane } from "@/components/research/EvidenceChatPane";
import { EvidenceSourcesBook } from "@/components/research/EvidenceSourcesBook";
import { StalenessBanner } from "@/components/research/StalenessBanner";

function formatRecommendation(rec: OverallRecommendation): string {
  if (rec === "too_vague_to_recommend") return "Needs clarity";
  return rec.charAt(0).toUpperCase() + rec.slice(1);
}

function recommendationBadgeClass(rec: OverallRecommendation): string {
  switch (rec) {
    case "proceed":
      return "bg-status-success text-ink-inverse";
    case "iterate":
      return "bg-brutalist-yellow text-ink-primary";
    case "pivot":
      return "bg-status-warning text-ink-primary";
    case "kill":
      return "bg-status-critical text-ink-inverse";
    default:
      return "bg-surface-muted text-ink-secondary";
  }
}

export function EvidenceStagePanel({ experimentId }: { experimentId: string }) {
  const [report, setReport] = useState<ValidationReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [stale, setStale] = useState(false);
  const [selection, setSelection] = useState<EvidenceSelection | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    (async () => {
      try {
        const data = await getValidationReport(experimentId);
        if (cancelled) return;
        setReport(data);
        setLoading(false);
      } catch {
        if (cancelled) return;
        setError("Could not load the validation report.");
        setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [experimentId]);

  if (loading) {
    return (
      <div className="h-full overflow-hidden p-4">
        <div className="fv-skeleton h-full min-h-[400px] w-full" />
      </div>
    );
  }

  if (error || !report) {
    return (
      <div className="h-full overflow-hidden p-4">
        <div className="border-2 border-border-master bg-surface-card p-4 font-mono text-mono-sm uppercase text-status-critical shadow-brutal-sm">
          {error ?? "Validation report unavailable."}
        </div>
      </div>
    );
  }

  const showRecommendation =
    report.overall_recommendation !== "too_vague_to_recommend";

  return (
    <div className="h-full overflow-hidden p-4">
      <div className="grid h-full min-h-0 gap-4 lg:grid-cols-[35%_65%]">
        <EvidenceChatPane
          experimentId={experimentId}
          report={report}
          selection={selection}
          onClearSelection={() => setSelection(null)}
        />

        {/* Report pane: pinned header (recommendation only) + independently
            scrolling body. Own flex column so it scrolls apart from the chat. */}
        <div className="flex h-full min-h-0 flex-col">
          {showRecommendation && (
            <div className="shrink-0 pb-3">
              <span
                className={`inline-block border-2 border-border-master px-3 py-1 font-mono text-mono-sm uppercase shadow-brutal-sm ${recommendationBadgeClass(
                  report.overall_recommendation,
                )}`}
              >
                {formatRecommendation(report.overall_recommendation)}
              </span>
            </div>
          )}

          <div className="min-h-0 flex-1 space-y-4 overflow-y-auto pr-1">
            {stale && <StalenessBanner />}

            <EvidenceReportEditor
              experimentId={experimentId}
              onStaleChange={setStale}
              onSelectionChange={setSelection}
            />

            <EvidenceSourcesBook report={report} />
          </div>
        </div>
      </div>
    </div>
  );
}
