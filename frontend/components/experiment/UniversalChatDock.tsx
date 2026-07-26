"use client";

import {
  useCallback,
  useEffect,
  useLayoutEffect,
  useRef,
  useState,
  type KeyboardEvent,
} from "react";
import {
  ArrowUp,
  Maximize2,
  MessageSquare,
  Paperclip,
  Search,
  X,
} from "lucide-react";
import { ChatMarkdown } from "@/components/chat/ChatMarkdown";
import {
  getUniversalChatMessages,
  sendUniversalChatMessage,
} from "@/lib/api";
import type { ChatHistoryMessage } from "@/lib/types";

const TOOL_CALL_LABELS: Record<string, string> = {
  get_metrics_summary: "Checked the metrics",
  get_report_summary: "Checked the validation report",
  get_landing_status: "Checked the landing page",
};

function toolCallLabel(toolPayload: ChatHistoryMessage["tool_payload"]): string {
  const name =
    toolPayload &&
    typeof toolPayload === "object" &&
    typeof toolPayload.tool_name === "string"
      ? toolPayload.tool_name
      : null;
  if (name && TOOL_CALL_LABELS[name]) {
    return TOOL_CALL_LABELS[name];
  }
  return "Checked project data";
}

type Props = {
  experimentId: string;
  projectName?: string | null;
};

type DockMessage = ChatHistoryMessage & {
  /** Client-only optimistic / error flags */
  optimistic?: boolean;
  error?: boolean;
};

const SCROLL_NEAR_BOTTOM_THRESHOLD_PX = 100;
const TEXTAREA_MAX_PX = 120;
const COLLAPSE_KEY_PREFIX = "fivvle-universal-chat-collapsed";

function collapseStorageKey(experimentId: string): string {
  return `${COLLAPSE_KEY_PREFIX}:${experimentId}`;
}

function isNarrowViewport(): boolean {
  if (typeof window === "undefined") return false;
  return window.matchMedia("(max-width: 639px)").matches;
}

function displayProjectName(projectName?: string | null): string | null {
  const trimmed = projectName?.trim();
  return trimmed ? trimmed : null;
}

export function UniversalChatDock({ experimentId, projectName }: Props) {
  const [collapsed, setCollapsed] = useState(false);
  const [messages, setMessages] = useState<DockMessage[]>([]);
  const [historyLoading, setHistoryLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [draft, setDraft] = useState("");

  const named = displayProjectName(projectName);
  const placeholder = named
    ? `Ask anything about ${named}`
    : "Ask anything about this project";
  const emptyCopy = named
    ? `Ask me anything about ${named}.`
    : "Ask me anything about your project.";

  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const scrollAnchorRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const isNearBottomRef = useRef(true);
  const forceScrollRef = useRef(false);

  useEffect(() => {
    const key = collapseStorageKey(experimentId);
    const raw = localStorage.getItem(key);
    if (raw === "1") {
      setCollapsed(true);
    } else if (raw === "0") {
      setCollapsed(false);
    } else {
      setCollapsed(isNarrowViewport());
    }
  }, [experimentId]);

  const setCollapsedPersisted = useCallback(
    (next: boolean) => {
      setCollapsed(next);
      localStorage.setItem(
        collapseStorageKey(experimentId),
        next ? "1" : "0",
      );
    },
    [experimentId],
  );

  useEffect(() => {
    let cancelled = false;
    setHistoryLoading(true);
    void getUniversalChatMessages(experimentId)
      .then((data) => {
        if (cancelled) return;
        setMessages(data.messages);
        forceScrollRef.current = true;
      })
      .catch(() => {
        if (cancelled) return;
        setMessages([]);
      })
      .finally(() => {
        if (!cancelled) setHistoryLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [experimentId]);

  const updateNearBottom = useCallback(() => {
    const container = scrollContainerRef.current;
    if (!container) {
      isNearBottomRef.current = true;
      return;
    }
    const distanceFromBottom =
      container.scrollHeight - container.scrollTop - container.clientHeight;
    isNearBottomRef.current =
      distanceFromBottom <= SCROLL_NEAR_BOTTOM_THRESHOLD_PX;
  }, []);

  const handleScroll = useCallback(() => {
    updateNearBottom();
  }, [updateNearBottom]);

  useEffect(() => {
    if (forceScrollRef.current || isNearBottomRef.current) {
      scrollAnchorRef.current?.scrollIntoView({ behavior: "smooth" });
      forceScrollRef.current = false;
    }
  }, [messages, sending, historyLoading]);

  const resizeTextarea = useCallback(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, TEXTAREA_MAX_PX)}px`;
  }, []);

  useLayoutEffect(() => {
    resizeTextarea();
  }, [draft, resizeTextarea]);

  const handleSend = useCallback(async () => {
    const trimmed = draft.trim();
    if (!trimmed || sending) return;

    const optimisticId = `local-${crypto.randomUUID()}`;
    const optimistic: DockMessage = {
      id: optimisticId,
      role: "user",
      content: trimmed,
      turn_kind: "universal_chat",
      created_at: new Date().toISOString(),
      optimistic: true,
    };

    setDraft("");
    setSending(true);
    forceScrollRef.current = true;
    setMessages((prev) => [...prev, optimistic]);

    try {
      const result = await sendUniversalChatMessage(experimentId, trimmed);
      setMessages((prev) => {
        const withoutOptimistic = prev.filter((m) => m.id !== optimisticId);
        return [...withoutOptimistic, ...result.messages];
      });
      forceScrollRef.current = true;
    } catch {
      setMessages((prev) =>
        prev.map((m) =>
          m.id === optimisticId
            ? {
                ...m,
                error: true,
                content: `${trimmed}\n\n(Failed to send — retry)`,
              }
            : m,
        ),
      );
    } finally {
      setSending(false);
    }
  }, [draft, experimentId, sending]);

  const handleRetry = useCallback(
    async (message: DockMessage) => {
      const content = message.content.replace(/\n\n\(Failed to send — retry\)$/, "");
      setMessages((prev) => prev.filter((m) => m.id !== message.id));
      setDraft(content);
      // Focus after state flush
      requestAnimationFrame(() => textareaRef.current?.focus());
    },
    [],
  );

  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      void handleSend();
    }
  };

  const canSend = draft.trim().length > 0 && !sending;

  if (collapsed) {
    return (
      <aside className="fixed right-6 top-6 z-20 w-10 rounded-lg border-2 border-border-master bg-[var(--fv-surface-card)] shadow-brutal-md">
        <button
          type="button"
          onClick={() => setCollapsedPersisted(false)}
          className="flex h-full min-h-[140px] w-full flex-col items-center justify-center gap-2 py-4 text-[var(--fv-text)]"
          aria-label="Open universal chat"
        >
          <MessageSquare className="h-4 w-4 text-[var(--fv-accent)]" aria-hidden />
          <span className="font-label-md text-label-sm uppercase tracking-widest [writing-mode:vertical-rl]">
            CHAT
          </span>
        </button>
      </aside>
    );
  }

  return (
    <aside className="fixed bottom-6 right-6 top-6 z-20 flex w-[420px] flex-col overflow-hidden rounded-sm border-2 border-border-master bg-[var(--fv-surface-card)] shadow-brutal-md">
      <header className="flex h-12 shrink-0 items-center justify-between gap-3 border-b border-[var(--fv-border)] px-3">
        <h2 className="min-w-0 truncate text-sm font-medium text-[var(--fv-text)]">
          Fivvle
        </h2>
        <div className="flex shrink-0 items-center gap-1">
          <IconButton
            label="Fullscreen coming soon"
            disabled
            title="Fullscreen coming soon"
          >
            <Maximize2 className="h-4 w-4" aria-hidden />
          </IconButton>
          <IconButton
            label="Collapse chat"
            title="Collapse"
            onClick={() => setCollapsedPersisted(true)}
          >
            <X className="h-4 w-4" aria-hidden />
          </IconButton>
        </div>
      </header>

      <div
        ref={scrollContainerRef}
        onScroll={handleScroll}
        className="min-h-0 flex-1 space-y-5 overflow-y-auto px-4 py-4"
      >
        {historyLoading ? (
          <div className="flex h-full items-center justify-center">
            <p className="text-sm text-[var(--fv-text-muted)]">Loading…</p>
          </div>
        ) : messages.length === 0 && !sending ? (
          <div className="flex h-full items-center justify-center px-4">
            <p className="text-center text-sm text-[var(--fv-text-muted)]">
              {emptyCopy}
            </p>
          </div>
        ) : (
          <>
            {messages.map((msg) => (
              <MessageRow
                key={msg.id}
                message={msg}
                onRetry={
                  msg.error ? () => void handleRetry(msg) : undefined
                }
              />
            ))}
            {sending ? <TypingIndicator /> : null}
          </>
        )}
        <div ref={scrollAnchorRef} />
      </div>

      <div className="shrink-0 border-t border-[var(--fv-border)] p-3">
        <div className="flex items-end gap-2">
          <button
            type="button"
            disabled
            title="Attachments coming soon"
            aria-label="Attachments coming soon"
            className="flex h-10 w-10 shrink-0 items-center justify-center rounded-md text-[var(--fv-text-muted)] opacity-50 cursor-not-allowed"
          >
            <Paperclip className="h-4 w-4" aria-hidden />
          </button>
          <textarea
            ref={textareaRef}
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={sending}
            rows={1}
            placeholder={placeholder}
            aria-label={placeholder}
            className="min-h-[40px] min-w-0 flex-1 resize-none rounded-md border border-[var(--fv-border)] bg-[var(--fv-surface-2)] px-3 py-2 text-sm text-[var(--fv-text)] placeholder:text-[var(--fv-text-muted)] focus:border-[var(--fv-accent)] focus:outline-none disabled:opacity-60"
            style={{ maxHeight: TEXTAREA_MAX_PX }}
          />
          <button
            type="button"
            onClick={() => void handleSend()}
            disabled={!canSend}
            aria-label="Send message"
            className="flex h-10 w-10 shrink-0 items-center justify-center rounded-md bg-[var(--fv-accent)] text-white transition-colors hover:bg-[var(--fv-accent-hover)] disabled:cursor-not-allowed disabled:opacity-40"
          >
            <ArrowUp className="h-4 w-4" aria-hidden />
          </button>
        </div>
      </div>
    </aside>
  );
}

function IconButton({
  children,
  label,
  title,
  disabled,
  onClick,
}: {
  children: React.ReactNode;
  label: string;
  title?: string;
  disabled?: boolean;
  onClick?: () => void;
}) {
  return (
    <button
      type="button"
      aria-label={label}
      title={title ?? label}
      disabled={disabled}
      onClick={onClick}
      className="flex h-8 w-8 items-center justify-center rounded-md text-[var(--fv-text-muted)] transition-colors hover:text-[var(--fv-text)] disabled:cursor-not-allowed disabled:opacity-40 disabled:hover:text-[var(--fv-text-muted)]"
    >
      {children}
    </button>
  );
}

function TypingIndicator() {
  return (
    <div>
      <span className="mb-1 block text-xs uppercase tracking-wide text-[var(--fv-text-muted)]">
        Fivvle
      </span>
      <div className="flex items-center gap-1.5 py-1">
        {[0, 150, 300].map((delay) => (
          <span
            key={delay}
            className="h-2 w-2 animate-pulse rounded-full bg-[var(--fv-accent)]"
            style={{ animationDelay: `${delay}ms` }}
          />
        ))}
      </div>
    </div>
  );
}

function MessageRow({
  message,
  onRetry,
}: {
  message: DockMessage;
  onRetry?: () => void;
}) {
  if (message.role === "user") {
    return (
      <div className="flex justify-end">
        <div className="flex max-w-[85%] flex-col items-end gap-1">
          <div
            className={`rounded-md border-2 border-border-master bg-[var(--fv-accent-muted)] p-3 shadow-brutal-sm ${
              message.error ? "opacity-80" : ""
            } ${message.optimistic && !message.error ? "opacity-90" : ""}`}
          >
            <p className="whitespace-pre-wrap font-body text-body-sm text-[var(--fv-text)]">
              {message.error
                ? message.content.replace(/\n\n\(Failed to send — retry\)$/, "")
                : message.content}
            </p>
          </div>
          {message.error && onRetry ? (
            <button
              type="button"
              onClick={onRetry}
              className="text-xs text-[var(--fv-accent)] hover:underline"
            >
              Failed to send — retry
            </button>
          ) : null}
        </div>
      </div>
    );
  }

  if (message.role === "assistant") {
    return (
      <div>
        <span className="mb-1 block text-xs uppercase tracking-wide text-[var(--fv-text-muted)]">
          Fivvle
        </span>
        <ChatMarkdown
          content={message.content}
          className="fv-msg-ai break-words text-sm text-[var(--fv-text)]"
        />
      </div>
    );
  }

  if (message.role === "tool_result") {
    return null;
  }

  if (message.role === "tool_call") {
    const label = toolCallLabel(message.tool_payload);
    return (
      <div
        className="-my-2 inline-flex max-w-full items-center gap-1.5 rounded-xs border border-border-master bg-surface-elevated px-2 py-1 text-xs text-ink-tertiary"
        aria-label={label}
      >
        <Search className="h-3.5 w-3.5 shrink-0 text-ink-tertiary" aria-hidden />
        <span className="truncate">{label}</span>
      </div>
    );
  }

  return null;
}
