"use client";

import { ChatInterface } from "@/components/chat/ChatInterface";

interface RefineStagePanelProps {
  experimentId?: string;
  onExperimentChange?: () => void;
  onRefinementFinalized?: (finalized: boolean) => void;
}

/** Refine tab — chat-based idea refinement and validation. */
export function RefineStagePanel({
  experimentId,
  onExperimentChange,
  onRefinementFinalized,
}: RefineStagePanelProps) {
  return (
    <div className="flex h-full min-h-0 flex-1 flex-col overflow-hidden rounded-xl border border-[var(--fv-border)] bg-[var(--fv-surface)]">
      <ChatInterface
        experimentId={experimentId}
        onExperimentChange={onExperimentChange}
        onRefinementFinalized={onRefinementFinalized}
      />
    </div>
  );
}
