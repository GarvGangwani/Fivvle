"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type {
  OverallRecommendation,
  RefCitation,
  ValidationReport,
} from "@/lib/types";
import { getValidationReport } from "@/lib/api";
import { takePendingEvidenceFocus } from "@/lib/pending-evidence-focus";
import {
  EvidenceReportEditor,
  type EvidenceReportEditorHandle,
  type EvidenceSelection,
} from "@/components/research/EvidenceReportEditor";
import { EvidenceChatPane } from "@/components/research/EvidenceChatPane";
import { EvidenceSourcesBook } from "@/components/research/EvidenceSourcesBook";
import { EditedDocOutdatedBanner } from "@/components/research/EditedDocOutdatedBanner";

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
  const [editedDocBehind, setEditedDocBehind] = useState(false);
  const [selection, setSelection] = useState<EvidenceSelection | null>(null);
  const editorRef = useRef<EvidenceReportEditorHandle>(null);

  const handleFocusReference = useCallback((anchor: RefCitation) => {
    editorRef.current?.focusReference(anchor);
  }, []);

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

  // Apply pending focus from master-rail citation / navigate once the editor is ready.
  useEffect(() => {
    if (loading || error || !report) return;
    const pending = takePendingEvidenceFocus();
    if (!pending) return;
    const t = window.setTimeout(() => {
      editorRef.current?.focusReference(pending);
    }, 80);
    return () => window.clearTimeout(t);
  }, [loading, error, report]);

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
          onFocusReference={handleFocusReference}
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
            {editedDocBehind && <EditedDocOutdatedBanner />}

            <EvidenceReportEditor
              ref={editorRef}
              experimentId={experimentId}
              onEditedDocBehindChange={setEditedDocBehind}
              onSelectionChange={setSelection}
            />

            <EvidenceSourcesBook report={report} />
          </div>
        </div>
      </div>
    </div>
  );
}
