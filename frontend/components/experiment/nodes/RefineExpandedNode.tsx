"use client";

import type { NodeProps } from "reactflow";
import { useAuth } from "@/lib/auth-context";
import type { Experiment } from "@/lib/types";
import { RefineChatInput } from "../refine/RefineChatInput";
import { RefineChatScroll } from "../refine/RefineChatScroll";
import { useRefineChat } from "../refine/useRefineChat";

export type RefineExpandedData = {
  experiment: Experiment;
  onClose: () => void;
  onFullscreen: () => void;
};

export function RefineExpandedNode({ data }: NodeProps<RefineExpandedData>) {
  const { experiment, onClose, onFullscreen } = data;
  // Same auth source as AppSideRail — Firebase user via AuthProvider.
  const { user } = useAuth();
  const { messages, loading, sending, send } = useRefineChat(experiment.id);

  // Match AppSideRail: fall back to email when displayName is unset so
  // ProfileAvatar can render initials instead of an empty/black tile.
  const currentUserProfile = user
    ? {
        displayName: user.displayName ?? user.email ?? null,
        photoURL: user.photoURL ?? null,
      }
    : null;

  return (
    <div
      className="w-[560px] bg-surface-card border-2 border-border-master shadow-brutal-lg flex flex-col overflow-hidden"
      style={{ maxHeight: "80vh", minHeight: "500px" }}
    >
      <div className="bg-ink-primary text-ink-inverse flex items-center justify-between px-4 py-3 shrink-0 cursor-grab active:cursor-grabbing">
        <div className="flex items-center gap-3">
          <span
            className="material-symbols-outlined text-brand-primary"
            style={{ fontSize: 20 }}
            aria-hidden="true"
          >
            bolt
          </span>
          <span className="font-mono text-mono-md uppercase tracking-wider">
            PHASE 02: REFINE // EXPANDED_VIEW
          </span>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={onFullscreen}
            className="p-1 hover:bg-ink-inverse/10"
            aria-label="Enter fullscreen"
          >
            <span className="material-symbols-outlined" style={{ fontSize: 18 }}>
              open_in_full
            </span>
          </button>
          <button
            type="button"
            onClick={onClose}
            className="p-1 hover:bg-ink-inverse/10"
            aria-label="Close"
          >
            <span className="material-symbols-outlined" style={{ fontSize: 18 }}>
              close
            </span>
          </button>
        </div>
      </div>

      <div className="flex-1 min-h-0 overflow-y-auto p-6 nodrag nowheel cursor-auto">
        <RefineChatScroll
          messages={messages}
          currentUserProfile={currentUserProfile}
          loading={loading}
        />
      </div>

      <div className="border-t-2 border-border-master p-3 shrink-0 nodrag nowheel cursor-auto">
        <RefineChatInput onSend={send} sending={sending} />
      </div>
    </div>
  );
}
