"use client";

import {
  useCallback,
  useEffect,
  useLayoutEffect,
  useRef,
  useState,
} from "react";
import { RotateCw, Send, X } from "lucide-react";
import type { ChatHistoryMessage, EvidenceChatSendRequest } from "@/lib/types";
import {
  ApiError,
  getEvidenceChatMessages,
  sendEvidenceChatMessage,
} from "@/lib/api";
import { useToast } from "@/components/ui/ToastProvider";
import type { EvidenceSelection } from "@/components/research/EvidenceReportEditor";

const NEAR_BOTTOM_PX = 50;
const CHIP_MAX_CHARS = 60;
const TEXTAREA_MIN_PX = 60;
const TEXTAREA_MAX_PX = 200;

const EMPTY_STATE_COPY =
  "Ask about a specific finding, why a score is low, or how to interpret the recommendation.";

interface EvidenceChatPaneProps {
  experimentId: string;
  selection: EvidenceSelection | null;
  onClearSelection: () => void;
}

/** Flatten to a single line and cap at 60 chars, appending … only if truncated. */
function truncateSelection(text: string): string {
  const flat = text.replace(/\s+/g, " ").trim();
  return flat.length > CHIP_MAX_CHARS
    ? `${flat.slice(0, CHIP_MAX_CHARS)}…`
    : flat;
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
  selection,
  onClearSelection,
}: EvidenceChatPaneProps) {
  const { toast } = useToast();
  const [messages, setMessages] = useState<ChatHistoryMessage[]>([]);
  const [input, setInput] = useState("");
  const [loadingHistory, setLoadingHistory] = useState(true);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Body + optimistic id of the last failed send, so retry re-fires it exactly.
  const retryRef = useRef<{ body: EvidenceChatSendRequest; id: string } | null>(
    null,
  );
  const scrollRef = useRef<HTMLDivElement>(null);
  const anchorRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const wasAtBottomRef = useRef(true);

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
            {messages.map((m) =>
              m.role === "user" ? (
                <div key={m.id} className="flex justify-end">
                  <div className="max-w-[85%] whitespace-pre-wrap break-words border-2 border-border-master bg-brand-primary p-3 text-sm text-ink-inverse shadow-brutal-sm">
                    {m.content}
                  </div>
                </div>
              ) : (
                <div key={m.id} className="flex justify-start">
                  <div className="max-w-[85%] whitespace-pre-wrap break-words border-2 border-border-master bg-surface-muted p-3 text-sm text-ink-primary shadow-brutal-sm">
                    {m.content}
                  </div>
                </div>
              ),
            )}
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
