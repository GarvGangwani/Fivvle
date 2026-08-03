"use client";

/**
 * Refine chat + Live Workspace body for the phase panel.
 * Same layout as RefineFullscreenModal without portal / PanelHeader chrome.
 */
import { useAuth } from "@/lib/auth-context";
import type { Experiment } from "@/lib/types";
import { LiveWorkspacePanel } from "../refine/LiveWorkspacePanel";
import {
  RefineChatInput,
  type AttachmentDraft,
} from "../refine/RefineChatInput";
import { RefineChatScroll } from "../refine/RefineChatScroll";
import type { RefineChatMessageModel } from "../refine/RefineChatMessage";

type Props = {
  experiment: Experiment;
  messages: RefineChatMessageModel[];
  loading: boolean;
  generatingOpener: boolean;
  sending: boolean;
  send: (text: string, attachments: AttachmentDraft[]) => void | Promise<void>;
  activeMCQFromMessageId?: string | null;
  dismissedMCQMessageIds?: Set<string>;
  onReopenMCQ?: (messageId: string) => void;
  onEditMessage?: (
    messageId: string,
    newContent: string,
  ) => void | Promise<void>;
  onRetryMessage?: (messageId: string) => void | Promise<void>;
  onSwitchBranch?: (
    messageId: string,
    direction: "prev" | "next",
  ) => void | Promise<void>;
  navigatingMessageId?: string | null;
  regeneratingMessageId?: string | null;
  onFinalizedOrReset: () => Promise<void>;
};

export function RefinePhaseBody({
  experiment,
  messages,
  loading,
  generatingOpener,
  sending,
  send,
  activeMCQFromMessageId,
  dismissedMCQMessageIds,
  onReopenMCQ,
  onEditMessage,
  onRetryMessage,
  onSwitchBranch,
  navigatingMessageId,
  regeneratingMessageId,
  onFinalizedOrReset,
}: Props) {
  const { user } = useAuth();

  const currentUserProfile = user
    ? {
        displayName: user.displayName ?? user.email ?? null,
        photoURL: user.photoURL ?? null,
      }
    : null;

  return (
    <div className="flex h-full min-h-0 flex-1 overflow-hidden">
      <div className="flex min-w-0 flex-1 flex-col border-r-2 border-border-master">
        <div className="min-h-0 flex-1 overflow-y-auto p-6 lg:p-8">
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
        <div className="shrink-0 border-t-2 border-border-master p-4">
          <RefineChatInput onSend={send} sending={sending} />
        </div>
      </div>

      <div className="w-full max-w-[400px] shrink-0 overflow-y-auto sm:w-[400px]">
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
