"use client";

import { useEffect, useRef } from "react";
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
      <div className="flex items-center justify-center py-16">
        <p className="font-mono text-mono-md uppercase text-ink-tertiary">
          Loading conversation...
        </p>
      </div>
    );
  }

  if (messages.length === 0 && generatingOpener) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[280px] text-center px-8">
        <span
          className="material-symbols-outlined text-brand-primary animate-pulse mb-4"
          style={{ fontSize: 48 }}
          aria-hidden="true"
        >
          bolt
        </span>
        <div className="font-mono text-mono-md uppercase text-brand-primary mb-2">
          REFINER IS READING YOUR IDEA
        </div>
        <p className="font-body text-body-md text-ink-secondary">
          Just a moment...
        </p>
      </div>
    );
  }

  if (messages.length === 0) {
    return <EmptyChatState />;
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

function EmptyChatState() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[280px] text-center px-8">
      <span
        className="material-symbols-outlined text-brand-primary mb-4"
        style={{ fontSize: 48 }}
        aria-hidden="true"
      >
        bolt
      </span>
      <div className="font-mono text-mono-md uppercase text-brand-primary mb-2">
        READY TO REFINE
      </div>
      <h3 className="font-headline text-headline-md text-ink-primary mb-2">
        Let&apos;s sharpen your idea.
      </h3>
      <p className="font-body text-body-md text-ink-secondary max-w-md">
        Ask me anything about your concept. I&apos;ve read your Spark and I&apos;m
        ready to help you find the sharpest version.
      </p>
    </div>
  );
}
