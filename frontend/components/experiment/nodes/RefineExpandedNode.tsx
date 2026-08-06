"use client";

import type { NodeProps } from "reactflow";
import { useAuth } from "@/lib/auth-context";
import type { Experiment } from "@/lib/types";
import { PanelHeader } from "@/components/ui/PanelHeader";
import { RefineChatInput, type AttachmentDraft } from "../refine/RefineChatInput";
import { RefineChatScroll } from "../refine/RefineChatScroll";
import type { RefineChatMessageModel } from "../refine/RefineChatMessage";

export type RefineExpandedData = {
  experiment: Experiment;
  onClose: () => void;
  onFullscreen: () => void;
  messages: RefineChatMessageModel[];
  loading: boolean;
  generatingOpener: boolean;
  sending: boolean;
  send: (text: string, attachments: AttachmentDraft[]) => void | Promise<void>;
  refinementCount: number;
  activeMCQFromMessageId?: string | null;
  dismissedMCQMessageIds?: Set<string>;
  onReopenMCQ?: (messageId: string) => void;
  onEditMessage?: (messageId: string, newContent: string) => void | Promise<void>;
  onRetryMessage?: (messageId: string) => void | Promise<void>;
  onSwitchBranch?: (
    messageId: string,
    direction: "prev" | "next",
  ) => void | Promise<void>;
  navigatingMessageId?: string | null;
  regeneratingMessageId?: string | null;
};

export function RefineExpandedNode({ data }: NodeProps<RefineExpandedData>) {
  const {
    onClose,
    onFullscreen,
    messages,
    loading,
    generatingOpener,
    sending,
    send,
    refinementCount,
    activeMCQFromMessageId,
    dismissedMCQMessageIds,
    onReopenMCQ,
    onEditMessage,
    onRetryMessage,
    onSwitchBranch,
    navigatingMessageId,
    regeneratingMessageId,
  } = data;
  const { user } = useAuth();

  const currentUserProfile = user
    ? {
        displayName: user.displayName ?? user.email ?? null,
        photoURL: user.photoURL ?? null,
      }
    : null;

  return (
    <div
      className="w-[560px] rounded-md bg-surface-card border-2 border-border-master shadow-brutal-lg flex flex-col overflow-hidden"
      style={{ maxHeight: "80vh", minHeight: "500px" }}
    >
      <div className="shrink-0 cursor-grab active:cursor-grabbing">
        <PanelHeader
          phaseLabel="REFINE"
          title="Expanded view"
          badge={
            refinementCount > 0 ? (
              <span className="border-2 border-border-master bg-accent px-2 py-0.5 font-mono text-mono-sm uppercase text-ink-inverse">
                TURN {refinementCount}
              </span>
            ) : null
          }
          actions={
            <div className="nodrag flex items-center gap-2">
              <button
                type="button"
                onClick={onFullscreen}
                className="p-1 text-ink-secondary transition-colors hover:bg-surface-elevated hover:text-ink-primary"
                aria-label="Enter fullscreen"
              >
                <span
                  className="material-symbols-outlined"
                  style={{ fontSize: 18 }}
                >
                  open_in_full
                </span>
              </button>
              <button
                type="button"
                onClick={onClose}
                className="p-1 text-ink-secondary transition-colors hover:bg-surface-elevated hover:text-ink-primary"
                aria-label="Close"
              >
                <span
                  className="material-symbols-outlined"
                  style={{ fontSize: 18 }}
                >
                  close
                </span>
              </button>
            </div>
          }
        />
      </div>

      <div className="flex-1 min-h-0 overflow-y-auto p-6 nodrag nowheel cursor-auto">
        <RefineChatScroll
          messages={messages}
          currentUserProfile={currentUserProfile}
          loading={loading}
          generatingOpener={generatingOpener}
          activeMCQFromMessageId={activeMCQFromMessageId}
          dismissedMCQMessageIds={dismissedMCQMessageIds}
          onReopenMCQ={onReopenMCQ}
          onEditMessage={onEditMessage}
          onRetryMessage={onRetryMessage}
          onSwitchBranch={onSwitchBranch}
          navigatingMessageId={navigatingMessageId}
          regeneratingMessageId={regeneratingMessageId}
        />
      </div>

      <div className="border-t-2 border-border-master p-3 shrink-0 nodrag nowheel cursor-auto">
        <RefineChatInput onSend={send} sending={sending} />
      </div>
    </div>
  );
}
