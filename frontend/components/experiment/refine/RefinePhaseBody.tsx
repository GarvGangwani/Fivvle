"use client";

/**
 * Refine Live Workspace body for the phase panel.
 * Chat pane removed (Universal Agent Phase 2 PR4) — master rail owns conversation.
 */
import type { Experiment } from "@/lib/types";
import { LiveWorkspacePanel } from "../refine/LiveWorkspacePanel";
import type { RefineChatMessageModel } from "../refine/RefineChatMessage";

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
    <div className="flex h-full min-h-0 flex-1 overflow-hidden">
      <div className="min-h-0 w-full flex-1 overflow-y-auto">
        <LiveWorkspacePanel
          experiment={experiment}
          messages={messages}
          onFinalized={onFinalizedOrReset}
          onReset={onFinalizedOrReset}
        />
      </div>
    </div>
  );
}
