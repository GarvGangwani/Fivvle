"use client";

import {
  memo,
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
  streamUniversalChatMessage,
} from "@/lib/api";
import { tokenizeCitations } from "@/lib/parse-citations";
import type {
  ChatHistoryMessage,
  RefineSubagentToolResult,
  ResearchSubagentSourceRef,
  ResearchSubagentToolResult,
} from "@/lib/types";

const TOOL_CALL_LABELS: Record<string, string> = {
  get_metrics_summary: "Checked the metrics",
  get_report_summary: "Checked the validation report",
  get_landing_status: "Checked the landing page",
  ask_refine_agent: "Asked Refine agent",
  ask_research_agent: "Asked Research agent",
};

const SUBAGENT_HANDOFF: Record<string, string> = {
  ask_refine_agent: "Refine agent thinking…",
  ask_research_agent: "Research agent digging in…",
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

function toolNameFromPayload(
  toolPayload: ChatHistoryMessage["tool_payload"],
): string | null {
  const root = asRecord(toolPayload);
  return root && typeof root.tool_name === "string" ? root.tool_name : null;
}

function asRecord(value: unknown): Record<string, unknown> | null {
  if (value && typeof value === "object" && !Array.isArray(value)) {
    return value as Record<string, unknown>;
  }
  return null;
}

function parseRefineSubagentResult(
  payload: ChatHistoryMessage["tool_payload"],
): RefineSubagentToolResult | null {
  const root = asRecord(payload);
  if (!root || root.tool_name !== "ask_refine_agent") return null;
  if (typeof root.error === "string" && root.result == null) return null;
  const result = asRecord(root.result);
  if (!result || typeof result.assistant_text !== "string") return null;
  return {
    assistant_text: result.assistant_text,
    refined_idea_patch:
      result.refined_idea_patch && typeof result.refined_idea_patch === "object"
        ? (result.refined_idea_patch as Record<string, unknown>)
        : null,
    has_pending_mcq: Boolean(result.has_pending_mcq),
    log_entry: typeof result.log_entry === "string" ? result.log_entry : null,
  };
}

/** Soft-fail refine result — distinct from a successful mapped payload. */
function parseRefineSubagentError(
  payload: ChatHistoryMessage["tool_payload"],
): string | null {
  const root = asRecord(payload);
  if (!root || root.tool_name !== "ask_refine_agent") return null;
  if (typeof root.error === "string" && root.result == null) {
    return root.error;
  }
  return null;
}

function parseResearchSubagentResult(
  payload: ChatHistoryMessage["tool_payload"],
): ResearchSubagentToolResult | null {
  const root = asRecord(payload);
  if (!root || root.tool_name !== "ask_research_agent") return null;
  if (typeof root.error === "string" && root.result == null) return null;
  const result = asRecord(root.result);
  if (!result || typeof result.assistant_text_with_citations !== "string") {
    return null;
  }
  const rawRefs = Array.isArray(result.source_refs) ? result.source_refs : [];
  const source_refs: ResearchSubagentSourceRef[] = [];
  for (const item of rawRefs) {
    const row = asRecord(item);
    if (!row || typeof row.marker_id !== "string") continue;
    source_refs.push({
      marker_id: row.marker_id,
      source_title:
        typeof row.source_title === "string" ? row.source_title : row.marker_id,
      source_url: typeof row.source_url === "string" ? row.source_url : null,
      source_domain:
        typeof row.source_domain === "string" ? row.source_domain : null,
    });
  }
  return {
    assistant_text_with_citations: result.assistant_text_with_citations,
    source_refs,
  };
}

function SubagentStatusChip({ label }: { label: string }) {
  return (
    <span className="inline-flex max-w-full items-center rounded-xs border border-border-master bg-surface-elevated px-1.5 py-0.5 text-[11px] leading-tight text-ink-tertiary">
      {label}
    </span>
  );
}

function InlineCitationChip({
  label,
  title,
}: {
  label: string;
  title?: string;
}) {
  return (
    <span
      title={title || undefined}
      className="mx-0.5 inline-flex max-w-[12rem] align-baseline rounded-xs border border-border-master px-1 py-px text-[10px] leading-tight text-ink-tertiary"
    >
      <span className="truncate">{label}</span>
    </span>
  );
}

function chipLabelForSource(ref: ResearchSubagentSourceRef): string {
  const domain = ref.source_domain?.trim();
  if (domain) return domain;
  const title = ref.source_title.trim();
  if (title.length <= 28) return title;
  return `${title.slice(0, 25)}…`;
}

function ResearchTextWithCitationChips({
  text,
  sourceRefs,
}: {
  text: string;
  sourceRefs: ResearchSubagentSourceRef[];
}) {
  const byMarker = new Map(
    sourceRefs.map((ref) => [ref.marker_id.toLowerCase(), ref]),
  );
  // Also index by bare source id (s1) so `[cite:s1]` / `[cite: s1]` both resolve.
  const byId = new Map<string, ResearchSubagentSourceRef>();
  for (const ref of sourceRefs) {
    const idMatch = /\[cite:\s*(s\d+)\]/i.exec(ref.marker_id);
    if (idMatch) byId.set(idMatch[1].toLowerCase(), ref);
  }
  const tokens = tokenizeCitations(text);

  return (
    <div className="fv-msg-ai break-words text-sm text-[var(--fv-text)]">
      {tokens.map((token, index) => {
        if (token.type === "text") {
          if (!token.value) return null;
          return (
            <ChatMarkdown
              key={`md-${index}`}
              content={token.value}
              className="inline [&_p]:m-0 [&_p]:inline"
            />
          );
        }
        // [ref:...] and unresolved cites stay as plain text (rail is primary-source only).
        const idMatch = /\[cite:\s*(s\d+)\]/i.exec(token.marker);
        const ref =
          byMarker.get(token.marker.toLowerCase()) ??
          (idMatch ? byId.get(idMatch[1].toLowerCase()) : undefined);
        if (!ref) {
          return (
            <span key={`raw-${index}`} className="text-ink-tertiary">
              {token.marker}
            </span>
          );
        }
        return (
          <InlineCitationChip
            key={`cite-${index}`}
            label={chipLabelForSource(ref)}
            title={
              [ref.source_title, ref.source_url].filter(Boolean).join(" — ") ||
              undefined
            }
          />
        );
      })}
    </div>
  );
}

type Props = {
  experimentId: string;
  projectName?: string | null;
  /** Notify parent when collapse state changes (phase panel inset). */
  onCollapsedChange?: (collapsed: boolean) => void;
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

function stubToolCallMessage(
  toolName: string,
  messageId: string,
): DockMessage {
  return {
    id: messageId,
    role: "tool_call",
    content: `Called: ${toolName}`,
    turn_kind: "universal_chat",
    created_at: new Date().toISOString(),
    tool_payload: { tool_name: toolName, arguments: {} },
  };
}

function toolResultFromEvent(
  toolName: string,
  messageId: string,
  payload: Record<string, unknown>,
): DockMessage {
  const toolPayload =
    typeof payload.tool_name === "string"
      ? payload
      : { tool_name: toolName, ...payload };
  return {
    id: messageId,
    role: "tool_result",
    content: "Result received",
    turn_kind: "universal_chat",
    created_at: new Date().toISOString(),
    tool_payload: toolPayload,
  };
}

function agentForToolName(
  toolName: string,
): "refine" | "research" | null {
  if (toolName === "ask_refine_agent") return "refine";
  if (toolName === "ask_research_agent") return "research";
  return null;
}

type StreamingSubagentState = {
  agent: "refine" | "research";
  text: string;
};

export const UniversalChatDock = memo(function UniversalChatDock({
  experimentId,
  projectName,
  onCollapsedChange,
}: Props) {
  const [collapsed, setCollapsed] = useState(false);
  const [messages, setMessages] = useState<DockMessage[]>([]);
  const [historyLoading, setHistoryLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [draft, setDraft] = useState("");
  const [streamingSubagent, setStreamingSubagent] =
    useState<StreamingSubagentState | null>(null);

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
  const streamAbortRef = useRef<AbortController | null>(null);
  const streamingAssistantIdRef = useRef<string | null>(null);

  useEffect(() => {
    const key = collapseStorageKey(experimentId);
    const raw = localStorage.getItem(key);
    let next = false;
    if (raw === "1") {
      next = true;
    } else if (raw === "0") {
      next = false;
    } else {
      next = isNarrowViewport();
    }
    setCollapsed(next);
    onCollapsedChange?.(next);
  }, [experimentId, onCollapsedChange]);

  useEffect(() => {
    return () => {
      streamAbortRef.current?.abort();
    };
  }, []);

  const setCollapsedPersisted = useCallback(
    (next: boolean) => {
      setCollapsed(next);
      onCollapsedChange?.(next);
      localStorage.setItem(
        collapseStorageKey(experimentId),
        next ? "1" : "0",
      );
    },
    [experimentId, onCollapsedChange],
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
  }, [messages, sending, historyLoading, streamingSubagent]);

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

    streamAbortRef.current?.abort();
    const abort = new AbortController();
    streamAbortRef.current = abort;
    streamingAssistantIdRef.current = null;
    setStreamingSubagent(null);

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

    const markFailed = () => {
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
      setStreamingSubagent(null);
    };

    try {
      await streamUniversalChatMessage(
        experimentId,
        trimmed,
        {
          onToolCall: ({ tool_name, message_id }) => {
            const agent = agentForToolName(tool_name);
            if (agent) {
              setStreamingSubagent({ agent, text: "" });
            } else {
              setStreamingSubagent(null);
            }
            setMessages((prev) => [
              ...prev,
              stubToolCallMessage(tool_name, message_id),
            ]);
            forceScrollRef.current = true;
          },
          onToolResult: ({ tool_name, message_id, payload }) => {
            setStreamingSubagent(null);
            setMessages((prev) => [
              ...prev,
              toolResultFromEvent(tool_name, message_id, payload),
            ]);
            forceScrollRef.current = true;
          },
          onSubagentToken: ({ agent, text }) => {
            setStreamingSubagent((prev) => {
              if (prev && prev.agent === agent) {
                return { agent, text: `${prev.text}${text}` };
              }
              return { agent, text };
            });
            forceScrollRef.current = true;
          },
          onAssistantToken: ({ text }) => {
            setStreamingSubagent(null);
            setMessages((prev) => {
              const existingId = streamingAssistantIdRef.current;
              if (existingId) {
                return prev.map((m) =>
                  m.id === existingId
                    ? { ...m, content: `${m.content}${text}` }
                    : m,
                );
              }
              const id = `local-assistant-${crypto.randomUUID()}`;
              streamingAssistantIdRef.current = id;
              return [
                ...prev,
                {
                  id,
                  role: "assistant",
                  content: text,
                  turn_kind: "universal_chat",
                  created_at: new Date().toISOString(),
                  optimistic: true,
                },
              ];
            });
            forceScrollRef.current = true;
          },
          onDone: ({ assistant_message_id, user_message_id }) => {
            setStreamingSubagent(null);
            setMessages((prev) =>
              prev.map((m) => {
                if (m.id === optimisticId) {
                  return {
                    ...m,
                    id: user_message_id ?? m.id,
                    optimistic: false,
                  };
                }
                if (
                  streamingAssistantIdRef.current &&
                  m.id === streamingAssistantIdRef.current
                ) {
                  return {
                    ...m,
                    id: assistant_message_id,
                    optimistic: false,
                  };
                }
                return m;
              }),
            );
          },
          onError: () => {
            if (abort.signal.aborted) return;
            setStreamingSubagent(null);
            setMessages((prev) => {
              const cleaned = prev.filter(
                (m) => !m.id.startsWith("local-assistant-"),
              );
              const hasPersistedTools = cleaned.some(
                (m) => m.role === "tool_call" || m.role === "tool_result",
              );
              if (hasPersistedTools) {
                return cleaned.map((m) =>
                  m.id === optimisticId ? { ...m, optimistic: false } : m,
                );
              }
              return cleaned.map((m) =>
                m.id === optimisticId
                  ? {
                      ...m,
                      error: true,
                      content: `${trimmed}\n\n(Failed to send — retry)`,
                    }
                  : m,
              );
            });
          },
        },
        abort.signal,
      );
    } catch {
      if (!abort.signal.aborted) markFailed();
    } finally {
      if (streamAbortRef.current === abort) {
        streamAbortRef.current = null;
      }
      setSending(false);
      streamingAssistantIdRef.current = null;
    }
  }, [draft, experimentId, sending]);

  const handleRetry = useCallback(
    async (message: DockMessage) => {
      const content = message.content.replace(/\n\n\(Failed to send — retry\)$/, "");
      setMessages((prev) => prev.filter((m) => m.id !== message.id));
      setDraft(content);
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
      <aside className="fixed right-6 top-6 z-[80] w-10 rounded-lg border-2 border-border-master bg-[var(--fv-surface-card)] shadow-brutal-md">
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
    <aside className="fixed bottom-6 right-6 top-6 z-[80] flex w-[420px] flex-col overflow-hidden rounded-sm border-2 border-border-master bg-[var(--fv-surface-card)] shadow-brutal-md">
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
            {messages.map((msg, index) => {
              const next = messages[index + 1];
              const name = toolNameFromPayload(msg.tool_payload);
              const agent = name ? agentForToolName(name) : null;
              const showSubagentHandoff =
                msg.role === "tool_call" &&
                agent != null &&
                (next == null || next.role !== "tool_result") &&
                (streamingSubagent == null ||
                  streamingSubagent.agent !== agent ||
                  streamingSubagent.text.length === 0);
              return (
                <MessageRow
                  key={msg.id}
                  message={msg}
                  showSubagentHandoff={showSubagentHandoff}
                  onRetry={
                    msg.error ? () => void handleRetry(msg) : undefined
                  }
                />
              );
            })}
            {streamingSubagent && streamingSubagent.text.length > 0 ? (
              <StreamingSubagentBlock
                agent={streamingSubagent.agent}
                text={streamingSubagent.text}
              />
            ) : null}
            {sending &&
            streamingSubagent == null &&
            (messages.length === 0 ||
              messages[messages.length - 1]?.role === "user" ||
              messages[messages.length - 1]?.role === "tool_call") ? (
              <TypingIndicator />
            ) : null}
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
});

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

function StreamingSubagentBlock({
  agent,
  text,
}: {
  agent: "refine" | "research";
  text: string;
}) {
  const label =
    agent === "refine" ? "From Refine agent" : "From Research agent";
  return (
    <div>
      <span className="mb-0.5 block text-xs uppercase tracking-wider text-ink-tertiary">
        {label}
      </span>
      {agent === "research" ? (
        <ResearchTextWithCitationChips text={text} sourceRefs={[]} />
      ) : (
        <ChatMarkdown
          content={text}
          className="fv-msg-ai break-words text-sm text-[var(--fv-text)]"
        />
      )}
    </div>
  );
}

function MessageRow({
  message,
  onRetry,
  showSubagentHandoff = false,
}: {
  message: DockMessage;
  onRetry?: () => void;
  showSubagentHandoff?: boolean;
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
    const refine = parseRefineSubagentResult(message.tool_payload);
    if (refine) {
      return (
        <div>
          <span className="mb-0.5 block text-xs uppercase tracking-wider text-ink-tertiary">
            From Refine agent
          </span>
          {refine.assistant_text ? (
            <ChatMarkdown
              content={refine.assistant_text}
              className="fv-msg-ai break-words text-sm text-[var(--fv-text)]"
            />
          ) : null}
          {(refine.refined_idea_patch != null || refine.has_pending_mcq) && (
            <div className="mt-2 flex flex-wrap gap-1.5">
              {refine.refined_idea_patch != null ? (
                <SubagentStatusChip label="Refined idea updated" />
              ) : null}
              {refine.has_pending_mcq ? (
                <SubagentStatusChip label="Open Refine to answer clarifying question" />
              ) : null}
            </div>
          )}
        </div>
      );
    }

    const refineError = parseRefineSubagentError(message.tool_payload);
    if (refineError) {
      return (
        <div>
          <span className="mb-0.5 block text-xs uppercase tracking-wider text-ink-tertiary">
            From Refine agent
          </span>
          <p className="text-sm text-[var(--fv-text-muted)]">{refineError}</p>
        </div>
      );
    }

    const research = parseResearchSubagentResult(message.tool_payload);
    if (research) {
      return (
        <div>
          <span className="mb-0.5 block text-xs uppercase tracking-wider text-ink-tertiary">
            From Research agent
          </span>
          <ResearchTextWithCitationChips
            text={research.assistant_text_with_citations}
            sourceRefs={research.source_refs}
          />
        </div>
      );
    }

    // Phase 1 read-tool results stay hidden in the rail.
    return null;
  }

  if (message.role === "tool_call") {
    const name = toolNameFromPayload(message.tool_payload);
    const label = toolCallLabel(message.tool_payload);
    const handoff =
      showSubagentHandoff && name != null ? SUBAGENT_HANDOFF[name] : null;
    return (
      <div className="space-y-1">
        <div
          className="-my-2 inline-flex max-w-full items-center gap-1.5 rounded-xs border border-border-master bg-surface-elevated px-2 py-1 text-xs text-ink-tertiary"
          aria-label={label}
        >
          <Search className="h-3.5 w-3.5 shrink-0 text-ink-tertiary" aria-hidden />
          <span className="truncate">{label}</span>
        </div>
        {handoff ? (
          <p className="text-xs italic text-ink-tertiary">{handoff}</p>
        ) : null}
      </div>
    );
  }

  return null;
}
