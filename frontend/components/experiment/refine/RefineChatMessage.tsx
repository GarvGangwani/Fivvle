"use client";

import type { Components } from "react-markdown";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { ProfileAvatar } from "@/components/dashboard/ProfileAvatar";
import type { ChatHistoryMessage, ClarifyingQuestion } from "@/lib/types";
import {
  MessageAttachments,
  type RefineMessageAttachment,
} from "./MessageAttachments";
import { MessageActions } from "./MessageActions";

export type RefineChatMessageModel = {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  attachments: RefineMessageAttachment[];
  created_at: string;
  is_streaming?: boolean;
  error?: boolean;
  clarifying_questions?: ClarifyingQuestion[];
  metadata?: ChatHistoryMessage["metadata"];
};

type Profile = {
  displayName: string | null;
  photoURL: string | null;
} | null;

type Props = {
  message: RefineChatMessageModel;
  currentUserProfile: Profile;
  activeMCQFromMessageId?: string | null;
  dismissedMCQMessageIds?: Set<string>;
  isLatest: boolean;
  onReopenMCQ?: (messageId: string) => void;
  onEditMessage?: (messageId: string, newContent: string) => void | Promise<void>;
  onRetryMessage?: (messageId: string) => void | Promise<void>;
};

const DISALLOWED_ELEMENTS = [
  "script",
  "style",
  "iframe",
  "object",
  "embed",
  "form",
  "input",
  "textarea",
  "button",
];

function isSafeHref(href: string | undefined): href is string {
  if (!href) return false;
  try {
    const url = new URL(href);
    return url.protocol === "http:" || url.protocol === "https:";
  } catch {
    return false;
  }
}

const BRUTALIST_MARKDOWN_COMPONENTS: Components = {
  a: ({ href, children }) => {
    if (!isSafeHref(href)) {
      return <span>{children}</span>;
    }
    return (
      <a
        href={href}
        target="_blank"
        rel="noopener noreferrer"
        className="text-brand-primary underline hover:no-underline"
      >
        {children}
      </a>
    );
  },
  code: ({ className, children, ...props }) => {
    const isBlock = Boolean(className?.includes("language-"));
    if (isBlock) {
      return (
        <code className={className} {...props}>
          {children}
        </code>
      );
    }
    return (
      <code
        className="bg-ink-primary text-ink-inverse px-1 font-mono text-mono-md"
        {...props}
      >
        {children}
      </code>
    );
  },
  pre: ({ children }) => (
    <pre className="bg-ink-primary text-ink-inverse p-4 font-mono text-mono-md overflow-x-auto border-2 border-border-master my-3">
      {children}
    </pre>
  ),
  ul: ({ children }) => (
    <ul className="list-disc pl-5 my-2 space-y-1 font-body text-body-md">
      {children}
    </ul>
  ),
  ol: ({ children }) => (
    <ol className="list-decimal pl-5 my-2 space-y-1 font-body text-body-md">
      {children}
    </ol>
  ),
  blockquote: ({ children }) => (
    <blockquote className="border-l-4 border-brand-primary pl-4 italic my-2 text-ink-secondary">
      {children}
    </blockquote>
  ),
  p: ({ children }) => (
    <p className="font-body text-body-md whitespace-pre-wrap mb-2 last:mb-0">
      {children}
    </p>
  ),
};

export function RefineChatMessage({
  message,
  currentUserProfile,
  activeMCQFromMessageId,
  dismissedMCQMessageIds,
  isLatest,
  onReopenMCQ,
  onEditMessage,
  onRetryMessage,
}: Props) {
  if (message.role === "user") {
    return (
      <UserMessage
        message={message}
        profile={currentUserProfile}
        isLatest={isLatest}
        onEditMessage={onEditMessage}
      />
    );
  }
  if (message.role === "assistant") {
    return (
      <AssistantMessage
        message={message}
        activeMCQFromMessageId={activeMCQFromMessageId}
        dismissedMCQMessageIds={dismissedMCQMessageIds}
        isLatest={isLatest}
        onReopenMCQ={onReopenMCQ}
        onRetryMessage={onRetryMessage}
      />
    );
  }
  return null;
}

function UserMessage({
  message,
  profile,
  isLatest,
  onEditMessage,
}: {
  message: RefineChatMessageModel;
  profile: Profile;
  isLatest: boolean;
  onEditMessage?: (messageId: string, newContent: string) => void | Promise<void>;
}) {
  const handleEdit = () => {
    if (!onEditMessage) return;
    const next = window.prompt("Edit your message:", message.content);
    if (next && next.trim() && next.trim() !== message.content) {
      void onEditMessage(message.id, next.trim());
    }
  };

  return (
    <div className="flex justify-end gap-3 mb-6">
      <div className="max-w-[75%] flex flex-col items-end">
        <div className="border-2 border-border-master bg-surface-card shadow-brutal-sm p-4">
          {message.content ? (
            <p className="font-body text-body-md whitespace-pre-wrap">
              {message.content}
            </p>
          ) : null}
          {message.attachments.length > 0 ? (
            <MessageAttachments attachments={message.attachments} />
          ) : null}
        </div>
        <MessageActions
          content={message.content}
          createdAt={message.created_at}
          role="user"
          isLatest={isLatest}
          onEdit={onEditMessage ? handleEdit : undefined}
        />
      </div>
      <ProfileAvatar
        photoURL={profile?.photoURL ?? null}
        displayName={profile?.displayName ?? null}
        size="sm"
      />
    </div>
  );
}

function AssistantMessage({
  message,
  activeMCQFromMessageId,
  dismissedMCQMessageIds,
  isLatest,
  onReopenMCQ,
  onRetryMessage,
}: {
  message: RefineChatMessageModel;
  activeMCQFromMessageId?: string | null;
  dismissedMCQMessageIds?: Set<string>;
  isLatest: boolean;
  onReopenMCQ?: (messageId: string) => void;
  onRetryMessage?: (messageId: string) => void | Promise<void>;
}) {
  const questions = message.clarifying_questions ?? [];
  const hasMCQOptions = questions.some((q) => q.options.length >= 2);
  const isMCQActive = activeMCQFromMessageId === message.id;
  const isDismissed = dismissedMCQMessageIds?.has(message.id) ?? false;

  return (
    <div className="flex justify-start mb-6">
      <div className="max-w-[85%]">
        <p className="font-mono text-mono-sm uppercase text-brand-primary mb-2">
          REFINER
        </p>
        <div
          className={[
            "border-2 border-border-master border-l-4 border-l-brand-primary bg-brand-primary-soft shadow-brutal-sm p-4",
            message.error ? "opacity-80" : "",
          ]
            .filter(Boolean)
            .join(" ")}
        >
          {message.content ? (
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              disallowedElements={DISALLOWED_ELEMENTS}
              unwrapDisallowed
              components={BRUTALIST_MARKDOWN_COMPONENTS}
            >
              {message.content}
            </ReactMarkdown>
          ) : null}
          {message.is_streaming ? (
            <span
              className="animate-pulse text-brand-primary"
              aria-hidden="true"
            >
              ▊
            </span>
          ) : null}

          {hasMCQOptions && isLatest ? (
            <>
              {isDismissed || (!isMCQActive && !isDismissed) ? (
                <button
                  type="button"
                  onClick={() => onReopenMCQ?.(message.id)}
                  className="mt-4 w-full border-2 border-dashed border-brand-primary bg-surface-card hover:bg-brand-primary hover:text-ink-inverse px-4 py-3 font-label-md text-label-md uppercase tracking-wider text-brand-primary transition-all flex items-center justify-center gap-2"
                >
                  <span
                    className="material-symbols-outlined"
                    style={{ fontSize: 18 }}
                    aria-hidden="true"
                  >
                    quiz
                  </span>
                  {isDismissed ? "REOPEN QUESTION" : "OPEN QUESTION"}
                </button>
              ) : null}
            </>
          ) : null}

          {!hasMCQOptions && questions.length > 0 && !isMCQActive ? (
            <ClarifyingQuestionsInline questions={questions} />
          ) : null}
        </div>
        <MessageActions
          content={message.content}
          createdAt={message.created_at}
          role="assistant"
          isLatest={isLatest}
          onRetry={
            onRetryMessage
              ? () => {
                  void onRetryMessage(message.id);
                }
              : undefined
          }
        />
      </div>
    </div>
  );
}

function ClarifyingQuestionsInline({
  questions,
}: {
  questions: ClarifyingQuestion[];
}) {
  return (
    <div className="mt-4 space-y-3 border-t-2 border-border-master/40 pt-3">
      {questions.map((q, qi) => (
        <div key={`${qi}-${q.question.slice(0, 24)}`}>
          <p className="font-body text-body-sm text-ink-primary mb-2">
            {q.question}
          </p>
          {q.options.length > 0 ? (
            <ul className="space-y-1">
              {q.options.map((opt, oi) => (
                <li
                  key={`${oi}-${opt}`}
                  className="font-mono text-mono-sm uppercase text-ink-secondary"
                >
                  {String.fromCharCode(65 + oi)}. {opt}
                </li>
              ))}
            </ul>
          ) : null}
        </div>
      ))}
    </div>
  );
}
