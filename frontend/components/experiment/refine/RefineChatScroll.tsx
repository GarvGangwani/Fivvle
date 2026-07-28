"use client";

import { useEffect, useRef } from "react";
import { BrutalistSkeleton } from "@/components/ui/BrutalistSkeleton";
import { EmptyState } from "@/components/ui/EmptyState";
import {
  RefineChatMessage,
  type RefineChatMessageModel,
} from "./RefineChatMessage";

type Profile = {
  displayName: string | null;
  photoURL: string | null;
} | null;

type Props = {
  messages: RefineChatMessageModel[];
  currentUserProfile: Profile;
  loading?: boolean;
  generatingOpener?: boolean;
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

export function RefineChatScroll({
  messages,
  currentUserProfile,
  loading = false,
  generatingOpener = false,
  activeMCQFromMessageId,
  dismissedMCQMessageIds,
  onReopenMCQ,
  onEditMessage,
  onRetryMessage,
  onSwitchBranch,
  navigatingMessageId,
  regeneratingMessageId,
}: Props) {
  const scrollAnchorRef = useRef<HTMLDivElement>(null);
  const latestMessageId =
    messages.length > 0 ? messages[messages.length - 1].id : null;

  useEffect(() => {
    scrollAnchorRef.current?.scrollIntoView({
      behavior: "smooth",
      block: "end",
    });
  }, [messages, generatingOpener]);

  if (loading) {
    return (
      <div
        className="space-y-4 py-4"
        role="status"
        aria-label="Loading conversation"
      >
        <BrutalistSkeleton variant="block" width="w-[75%] ml-auto" height="h-16" />
        <BrutalistSkeleton variant="block" width="w-[85%]" height="h-20" />
        <BrutalistSkeleton variant="block" width="w-[70%] ml-auto" height="h-14" />
        <BrutalistSkeleton variant="block" width="w-[80%]" height="h-24" />
      </div>
    );
  }

  if (messages.length === 0 && generatingOpener) {
    return (
      <div className="flex min-h-[280px] flex-col items-center justify-center px-8 text-center">
        <span
          className="material-symbols-outlined mb-4 animate-pulse text-brand-primary"
          style={{ fontSize: 48 }}
          aria-hidden="true"
        >
          bolt
        </span>
        <div className="mb-2 font-mono text-mono-md uppercase text-brand-primary">
          REFINER IS READING YOUR IDEA
        </div>
        <p className="font-body text-body-md text-ink-secondary">
          Just a moment...
        </p>
      </div>
    );
  }

  if (messages.length === 0) {
    return (
      <EmptyState
        icon={
          <span
            className="material-symbols-outlined text-brand-primary"
            style={{ fontSize: 28 }}
            aria-hidden="true"
          >
            bolt
          </span>
        }
        title="Ready to refine"
        description="Ask me anything about your concept. I've read your Spark and I'm ready to help you find the sharpest version."
      />
    );
  }

  return (
    <div>
      {messages.map((msg) => (
        <RefineChatMessage
          key={msg.id}
          message={msg}
          currentUserProfile={currentUserProfile}
          activeMCQFromMessageId={activeMCQFromMessageId}
          dismissedMCQMessageIds={dismissedMCQMessageIds}
          isLatest={msg.id === latestMessageId}
          onReopenMCQ={onReopenMCQ}
          onEditMessage={onEditMessage}
          onRetryMessage={onRetryMessage}
          onSwitchBranch={onSwitchBranch}
          navigatingMessageId={navigatingMessageId}
          regeneratingMessageId={regeneratingMessageId}
        />
      ))}
      <div ref={scrollAnchorRef} />
    </div>
  );
}
