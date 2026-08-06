"use client";

/**
 * Refine Live Workspace body for the phase panel.
 * Chat pane removed (Universal Agent Phase 2 PR4) — master rail owns conversation.
 */
import type { Experiment } from "@/lib/types";
import { LiveWorkspacePanel } from "../refine/LiveWorkspacePanel";
import type { RefineChatMessageModel } from "../refine/RefineChatMessage";
import { RefineCompleteBar } from "../refine/RefineCompleteBar";

type Props = {
  experiment: Experiment;
  messages: RefineChatMessageModel[];
  onFinalizedOrReset: () => Promise<void>;
};

export function RefinePhaseBody({
  experiment,
  messages,
  onFinalizedOrReset,
}: Props) {
  return (
    <div className="flex h-full min-h-0 flex-1 flex-col overflow-hidden">
      <div className="min-h-0 flex-1 overflow-y-auto">
        <LiveWorkspacePanel
          experiment={experiment}
          messages={messages}
          onFinalized={onFinalizedOrReset}
          onReset={onFinalizedOrReset}
        />
      </div>
      {/* Pinned so advancing the experiment is always reachable, and visibly
          separate from the idea-level FINALIZE control inside the workspace. */}
      <RefineCompleteBar
        experiment={experiment}
        onCompleted={onFinalizedOrReset}
      />
    </div>
  );
}
