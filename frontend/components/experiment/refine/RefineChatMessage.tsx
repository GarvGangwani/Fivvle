"use client";

import type { Components } from "react-markdown";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { ProfileAvatar } from "@/components/dashboard/ProfileAvatar";
import {
  MessageAttachments,
  type RefineMessageAttachment,
} from "./MessageAttachments";

export type RefineChatMessageModel = {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  attachments: RefineMessageAttachment[];
  created_at: string;
  is_streaming?: boolean;
  error?: boolean;
};

type Profile = {
  displayName: string | null;
  photoURL: string | null;
} | null;

type Props = {
  message: RefineChatMessageModel;
  currentUserProfile: Profile;
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

function formatTime(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "";
  return date.toLocaleTimeString("en-GB", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
    timeZone: "UTC",
  });
}

export function RefineChatMessage({ message, currentUserProfile }: Props) {
  if (message.role === "user") {
    return <UserMessage message={message} profile={currentUserProfile} />;
  }
  if (message.role === "assistant") {
    return <AssistantMessage message={message} />;
  }
  return null;
}

function UserMessage({
  message,
  profile,
}: {
  message: RefineChatMessageModel;
  profile: Profile;
}) {
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
        <p className="font-mono text-mono-sm uppercase text-ink-tertiary mt-1">
          {formatTime(message.created_at)} · SENT
        </p>
      </div>
      <ProfileAvatar
        photoURL={profile?.photoURL ?? null}
        displayName={profile?.displayName ?? null}
        size="sm"
      />
    </div>
  );
}

function AssistantMessage({ message }: { message: RefineChatMessageModel }) {
  return (
    <div className="flex justify-start mb-6">
      <div className="max-w-[85%]">
        <p className="font-mono text-mono-sm uppercase text-brand-primary mb-2">
          REFINER · {formatTime(message.created_at)} UTC
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
            <span className="animate-pulse text-brand-primary" aria-hidden="true">
              ▊
            </span>
          ) : null}
        </div>
      </div>
    </div>
  );
}
