"use client";

import {
  useCallback,
  useEffect,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import {
  Check,
  Copy,
  RotateCw,
  Send,
  ThumbsDown,
  ThumbsUp,
  X,
} from "lucide-react";
import type {
  ChatHistoryMessage,
  Citation,
  EvidenceChatSendRequest,
  EvidenceChatVerdict,
  ValidationReport,
} from "@/lib/types";
import {
  ApiError,
  getEvidenceChatMessages,
  regenerateEvidenceChatMessage,
  sendEvidenceChatFeedback,
  sendEvidenceChatMessage,
} from "@/lib/api";
import { useToast } from "@/components/ui/ToastProvider";
import type { EvidenceSelection } from "@/components/research/EvidenceReportEditor";

const NEAR_BOTTOM_PX = 50;
const CHIP_MAX_CHARS = 60;
const TEXTAREA_MIN_PX = 60;
const TEXTAREA_MAX_PX = 200;
const COPY_FEEDBACK_MS = 1500;

const EMPTY_STATE_COPY =
  "Ask about a specific finding, why a score is low, or how to interpret the recommendation.";

/** Inline citation marker the v2 prompt emits: `[cite: url1, url2]`. */
const CITE_RE = /\[cite:\s*([^\]]*)\]/gi;

interface EvidenceChatPaneProps {
  experimentId: string;
  report: ValidationReport;
  selection: EvidenceSelection | null;
  onClearSelection: () => void;
}

/** The session-local selection anchor a reply was generated from. Not persisted;
 * used only so an in-session regenerate can re-use the same (or updated) anchor. */
interface SelectionAnchor {
  selection_text: string | null;
  selection_question_id: string | null;
}

/** Flatten to a single line and cap at 60 chars, appending … only if truncated. */
function truncateSelection(text: string): string {
  const flat = text.replace(/\s+/g, " ").trim();
  return flat.length > CHIP_MAX_CHARS
    ? `${flat.slice(0, CHIP_MAX_CHARS)}…`
    : flat;
}

/**
 * Strip `[cite: …]` markers from a reply and collect the unique URLs they
 * reference. The visible text never shows the raw markers; the URLs become
 * source pills. Copy still uses the raw content (markers intact) for portability.
 */
function parseCitations(content: string): { text: string; urls: string[] } {
  const urls: string[] = [];
  const seen = new Set<string>();
  let match: RegExpExecArray | null;
  CITE_RE.lastIndex = 0;
  while ((match = CITE_RE.exec(content)) !== null) {
    for (const raw of match[1].split(",")) {
      const url = raw.trim();
      if (url && !seen.has(url)) {
        seen.add(url);
        urls.push(url);
      }
    }
  }
  const text = content
    .replace(CITE_RE, "")
    .replace(/[^\S\n]+([.,;:!?])/g, "$1")
    .replace(/[^\S\n]{2,}/g, " ")
    .replace(/[^\S\n]+$/gm, "")
    .trim();
  return { text, urls };
}

function isSafeHttpUrl(url: string): boolean {
  return url.startsWith("http://") || url.startsWith("https://");
}

function domainForUrl(
  url: string,
  lookup: Map<string, { domain: string; title: string }>,
): string {
  const info = lookup.get(url);
  if (info?.domain) return info.domain;
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return url;
  }
}

function SourcePills({
  urls,
  lookup,
}: {
  urls: string[];
  lookup: Map<string, { domain: string; title: string }>;
}) {
  return (
    <div className="mt-3 flex flex-wrap gap-2">
      {urls.map((url) => {
        const domain = domainForUrl(url, lookup);
        const letter = (domain[0] ?? "?").toUpperCase();
        const title = lookup.get(url)?.title || domain;
        const avatar = (
          <span className="flex h-4 w-4 items-center justify-center rounded-full bg-brand-primary text-[10px] font-mono font-bold text-ink-inverse">
            {letter}
          </span>
        );
        const label = <span className="max-w-[140px] truncate">{domain}</span>;
        const className =
          "flex items-center gap-2 rounded-full border-2 border-border-master bg-surface-muted px-3 py-1 font-mono text-mono-sm text-ink-primary";
        return isSafeHttpUrl(url) ? (
          <a
            key={url}
            href={url}
            target="_blank"
            rel="noopener noreferrer"
            title={title}
            className={className}
          >
            {avatar}
            {label}
          </a>
        ) : (
          <span key={url} title={title} className={className}>
            {avatar}
            {label}
          </span>
        );
      })}
    </div>
  );
}

function errorMessageFrom(err: unknown): string {
  if (err instanceof ApiError && err.status >= 400 && err.status < 500) {
    const detail = (err.body as { detail?: unknown } | null)?.detail;
    if (typeof detail === "string" && detail.trim()) return detail;
  }
  return "Couldn't send — retry";
}

export function EvidenceChatPane({
  experimentId,
  report,
  selection,
  onClearSelection,
}: EvidenceChatPaneProps) {
  const { toast } = useToast();
  const [messages, setMessages] = useState<ChatHistoryMessage[]>([]);
  const [input, setInput] = useState("");
  const [loadingHistory, setLoadingHistory] = useState(true);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [thumbs, setThumbs] = useState<Record<string, EvidenceChatVerdict>>({});
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [regeneratingId, setRegeneratingId] = useState<string | null>(null);

  // Body + optimistic id of the last failed send, so retry re-fires it exactly.
  const retryRef = useRef<{ body: EvidenceChatSendRequest; id: string } | null>(
    null,
  );
  // assistant message id -> selection anchor it was generated from (session only).
  const selectionMapRef = useRef<Map<string, SelectionAnchor>>(new Map());
  const thumbsRef = useRef(thumbs);
  const scrollRef = useRef<HTMLDivElement>(null);
  const anchorRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const wasAtBottomRef = useRef(true);

  useEffect(() => {
    thumbsRef.current = thumbs;
  }, [thumbs]);

  // URL -> {domain, title} from the report's citations, for resolving pills.
  const citationLookup = useMemo(() => {
    const map = new Map<string, { domain: string; title: string }>();
    const add = (citations: Citation[]) => {
      for (const c of citations) {
        if (c.url && !map.has(c.url)) {
          map.set(c.url, { domain: c.source_domain?.trim() || "", title: c.title });
        }
      }
    };
    for (const qf of report.questions_and_findings) {
      for (const finding of qf.findings) add(finding.citations);
    }
    for (const competitor of report.competitors) add(competitor.citations);
    return map;
  }, [report]);

  useEffect(() => {
    let cancelled = false;
    setLoadingHistory(true);
    (async () => {
      try {
        const resp = await getEvidenceChatMessages(experimentId);
        if (cancelled) return;
        setMessages(resp.messages);
      } catch {
        if (cancelled) return;
        toast("Could not load the chat history.", "error");
      } finally {
        if (!cancelled) setLoadingHistory(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [experimentId, toast]);

  // Auto-grow the composer, capped at the max height.
  useLayoutEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, TEXTAREA_MAX_PX)}px`;
  }, [input]);

  // Only follow new content when the user was already near the bottom.
  useEffect(() => {
    if (wasAtBottomRef.current) {
      anchorRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, sending]);

  const handleScroll = useCallback(() => {
    const el = scrollRef.current;
    if (!el) return;
    wasAtBottomRef.current =
      el.scrollHeight - el.scrollTop - el.clientHeight < NEAR_BOTTOM_PX;
  }, []);

  const doSend = useCallback(
    async (body: EvidenceChatSendRequest, optimisticId: string) => {
      setSending(true);
      setError(null);
      try {
        const resp = await sendEvidenceChatMessage(experimentId, body);
        retryRef.current = null;
        // Remember the anchor this reply came from, keyed by the assistant id,
        // so an in-session regenerate can re-use it.
        selectionMapRef.current.set(resp.assistant_message.id, {
          selection_text: body.selection_text ?? null,
          selection_question_id: body.selection_question_id ?? null,
        });
        // Replace the optimistic user message id with the real one and append
        // the assistant reply in a single update to avoid a flash.
        setMessages((prev) => {
          const next = prev.map((m) =>
            m.id === optimisticId ? resp.user_message : m,
          );
          next.push(resp.assistant_message);
          return next;
        });
      } catch (err) {
        retryRef.current = { body, id: optimisticId };
        setError(errorMessageFrom(err));
      } finally {
        setSending(false);
      }
    },
    [experimentId],
  );

  const handleSubmit = useCallback(() => {
    const trimmed = input.trim();
    if (!trimmed || sending || error) return;
    const optimisticId = `local-${crypto.randomUUID()}`;
    const body: EvidenceChatSendRequest = {
      message: trimmed,
      selection_text: selection?.text ?? null,
      selection_question_id: selection?.question_id ?? null,
    };
    const optimistic: ChatHistoryMessage = {
      id: optimisticId,
      role: "user",
      content: trimmed,
      turn_kind: "evidence_chat",
      created_at: new Date().toISOString(),
    };
    // The user just acted — always follow their own message down.
    wasAtBottomRef.current = true;
    setMessages((prev) => [...prev, optimistic]);
    setInput("");
    void doSend(body, optimisticId);
  }, [input, sending, error, selection, doSend]);

  const handleRetry = useCallback(() => {
    const pending = retryRef.current;
    if (!pending) return;
    wasAtBottomRef.current = true;
    void doSend(pending.body, pending.id);
  }, [doSend]);

  const doFeedback = useCallback(
    async (messageId: string, verdict: EvidenceChatVerdict) => {
      try {
        await sendEvidenceChatFeedback(experimentId, messageId, verdict);
      } catch {
        // Assume intent is captured — do NOT revert the visual thumb state.
        toast("Couldn't send feedback", "error");
      }
    },
    [experimentId, toast],
  );

  const handleThumb = useCallback(
    (messageId: string, verdict: EvidenceChatVerdict) => {
      // Clicking the already-active thumb is a no-op (no backend call).
      if (thumbsRef.current[messageId] === verdict) return;
      setThumbs((prev) => ({ ...prev, [messageId]: verdict }));
      void doFeedback(messageId, verdict);
    },
    [doFeedback],
  );

  const handleCopy = useCallback(
    async (message: ChatHistoryMessage) => {
      try {
        // Raw content WITH [cite:] markers, so the copied text is portable.
        await navigator.clipboard.writeText(message.content);
        setCopiedId(message.id);
        window.setTimeout(
          () => setCopiedId((c) => (c === message.id ? null : c)),
          COPY_FEEDBACK_MS,
        );
        toast("Copied", "success");
      } catch {
        toast("Couldn't copy", "error");
      }
    },
    [toast],
  );

  const handleRegenerate = useCallback(
    async (message: ChatHistoryMessage) => {
      if (regeneratingId) return;
      const anchor = selectionMapRef.current.get(message.id) ?? {
        selection_text: null,
        selection_question_id: null,
      };
      setRegeneratingId(message.id);
      try {
        const resp = await regenerateEvidenceChatMessage(
          experimentId,
          message.id,
          anchor,
        );
        const fresh = resp.assistant_message;
        setMessages((prev) =>
          prev.map((m) => (m.id === message.id ? fresh : m)),
        );
        // Carry the anchor onto the new id; the old reply's thumb no longer applies.
        selectionMapRef.current.delete(message.id);
        selectionMapRef.current.set(fresh.id, anchor);
        setThumbs((prev) => {
          if (!(message.id in prev)) return prev;
          const next = { ...prev };
          delete next[message.id];
          return next;
        });
      } catch {
        toast("Couldn't regenerate — try again", "error");
      } finally {
        setRegeneratingId(null);
      }
    },
    [experimentId, regeneratingId, toast],
  );

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  }

  const chipLabel = selection
    ? selection.question_id
      ? `Referring to ${selection.question_id.toUpperCase()} — "${truncateSelection(
          selection.text,
        )}"`
      : `Referring to selected text — "${truncateSelection(selection.text)}"`
    : null;

  const sendDisabled = !input.trim() || sending || error !== null;
  const showEmptyState = !loadingHistory && !sending && messages.length === 0;

  return (
    <div className="flex h-full min-h-[400px] flex-col border-2 border-border-master bg-surface-card shadow-brutal-sm">
      <div className="shrink-0 border-b-2 border-border-master px-4 py-3">
        <h2 className="font-mono text-mono-sm uppercase text-ink-primary">
          Chat with report
        </h2>
      </div>

      <div
        ref={scrollRef}
        onScroll={handleScroll}
        className="min-h-0 flex-1 space-y-3 overflow-y-auto p-4"
      >
        {showEmptyState ? (
          <div className="flex h-full items-center justify-center">
            <p className="max-w-[280px] text-center font-mono text-mono-sm text-ink-tertiary">
              {EMPTY_STATE_COPY}
            </p>
          </div>
        ) : (
          <>
            {messages.map((m) => {
              if (m.role === "user") {
                return (
                  <div key={m.id} className="flex justify-end">
                    <div className="max-w-[85%] whitespace-pre-wrap break-words border-2 border-border-master bg-brand-primary p-3 text-sm text-ink-inverse shadow-brutal-sm">
                      {m.content}
                    </div>
                  </div>
                );
              }
              const { text, urls } = parseCitations(m.content);
              const isRegenerating = regeneratingId === m.id;
              const verdict = thumbs[m.id];
              return (
                <div key={m.id} className="flex flex-col items-start gap-2">
                  <div
                    className={`max-w-[85%] border-2 border-border-master bg-surface-muted p-3 text-sm text-ink-primary shadow-brutal-sm ${
                      isRegenerating ? "opacity-50" : ""
                    }`}
                  >
                    {isRegenerating ? (
                      <div className="flex items-center gap-2 text-ink-tertiary">
                        <RotateCw className="h-3.5 w-3.5 animate-spin" />
                        <span className="font-mono text-mono-sm uppercase">
                          Regenerating…
                        </span>
                      </div>
                    ) : (
                      <>
                        <div className="whitespace-pre-wrap break-words">
                          {text}
                        </div>
                        {urls.length > 0 && (
                          <SourcePills urls={urls} lookup={citationLookup} />
                        )}
                      </>
                    )}
                  </div>

                  {!isRegenerating && (
                    <div className="flex items-center gap-2 pl-1 text-ink-tertiary">
                      <button
                        type="button"
                        onClick={() => handleCopy(m)}
                        aria-label="Copy message"
                        title="Copy"
                        className="transition-colors hover:text-ink-primary"
                      >
                        {copiedId === m.id ? (
                          <Check className="h-3.5 w-3.5" />
                        ) : (
                          <Copy className="h-3.5 w-3.5" />
                        )}
                      </button>
                      <button
                        type="button"
                        onClick={() => handleThumb(m.id, "up")}
                        aria-label="Good response"
                        aria-pressed={verdict === "up"}
                        title="Good response"
                        className={`transition-colors ${
                          verdict === "up"
                            ? "text-brand-primary"
                            : "hover:text-ink-primary"
                        }`}
                      >
                        <ThumbsUp className="h-3.5 w-3.5" />
                      </button>
                      <button
                        type="button"
                        onClick={() => handleThumb(m.id, "down")}
                        aria-label="Bad response"
                        aria-pressed={verdict === "down"}
                        title="Bad response"
                        className={`transition-colors ${
                          verdict === "down"
                            ? "text-brand-primary"
                            : "hover:text-ink-primary"
                        }`}
                      >
                        <ThumbsDown className="h-3.5 w-3.5" />
                      </button>
                      <button
                        type="button"
                        onClick={() => handleRegenerate(m)}
                        disabled={regeneratingId !== null}
                        aria-label="Regenerate response"
                        title="Regenerate"
                        className="transition-colors hover:text-ink-primary disabled:opacity-40"
                      >
                        <RotateCw className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  )}
                </div>
              );
            })}
            {sending && (
              <div className="flex justify-start">
                <div className="flex items-center gap-1.5 border-2 border-border-master bg-surface-muted p-3 shadow-brutal-sm">
                  {[0, 150, 300].map((delay) => (
                    <span
                      key={delay}
                      className="h-2 w-2 animate-pulse rounded-full bg-ink-tertiary"
                      style={{ animationDelay: `${delay}ms` }}
                    />
                  ))}
                </div>
              </div>
            )}
          </>
        )}
        <div ref={anchorRef} />
      </div>

      <div className="shrink-0 border-t-2 border-border-master p-4">
        {chipLabel && (
          <div className="mb-3 flex items-center gap-2 border-2 border-border-master bg-brutalist-yellow p-2 font-mono text-mono-sm text-ink-primary shadow-brutal-sm">
            <span className="min-w-0 flex-1 truncate">{chipLabel}</span>
            <button
              type="button"
              onClick={onClearSelection}
              aria-label="Clear selection"
              className="shrink-0"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          </div>
        )}

        <div className="flex items-end gap-2">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            rows={1}
            placeholder="Ask about the report…"
            style={{ minHeight: TEXTAREA_MIN_PX, maxHeight: TEXTAREA_MAX_PX }}
            className="min-w-0 flex-1 resize-none border-2 border-border-master bg-surface-card px-3 py-2 text-sm text-ink-primary placeholder:text-ink-tertiary focus:outline-none"
          />
          <button
            type="button"
            onClick={handleSubmit}
            disabled={sendDisabled}
            aria-label="Send message"
            className={`flex h-[42px] w-[42px] shrink-0 items-center justify-center border-2 border-border-master shadow-brutal-sm ${
              sendDisabled
                ? "bg-surface-muted text-ink-tertiary"
                : "bg-brand-primary text-ink-inverse"
            }`}
          >
            <Send className="h-4 w-4" />
          </button>
        </div>

        {error && (
          <div className="mt-3 flex items-center justify-between gap-2 border-2 border-status-critical bg-surface-card p-3 font-mono text-mono-sm text-status-critical">
            <span className="min-w-0 flex-1 break-words">{error}</span>
            <button
              type="button"
              onClick={handleRetry}
              className="inline-flex shrink-0 items-center gap-1.5 uppercase"
            >
              <RotateCw className="h-3.5 w-3.5" />
              Retry
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
