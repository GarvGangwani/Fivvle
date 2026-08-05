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
  AlertTriangle,
  BarChart3,
  Building2,
  Check,
  ChevronLeft,
  ChevronRight,
  Copy,
  FileQuestion,
  Pencil,
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
  RefCitation,
  SiblingInfo,
  ValidationReport,
} from "@/lib/types";
import {
  ApiError,
  activateEvidenceChatBranch,
  editEvidenceChatMessage,
  getEvidenceChatMessages,
  regenerateEvidenceChatMessage,
  sendEvidenceChatFeedback,
  streamEvidenceChatMessage,
} from "@/lib/api";
import { parseCitations } from "@/lib/parse-citations";
import { SECTION_LABELS, type ReportSectionId } from "@/lib/validation-report-scores";
import { useToast } from "@/components/ui/ToastProvider";
import type { EvidenceSelection } from "@/components/research/EvidenceReportEditor";

const NEAR_BOTTOM_PX = 50;
const CHIP_MAX_CHARS = 60;
const TEXTAREA_MIN_PX = 60;
const TEXTAREA_MAX_PX = 200;
const COPY_FEEDBACK_MS = 1500;

const EMPTY_STATE_COPY =
  "Ask about a specific finding, why a score is low, or how to interpret the recommendation.";

interface EvidenceChatPaneProps {
  experimentId: string;
  report: ValidationReport;
  selection: EvidenceSelection | null;
  onClearSelection: () => void;
  /** Scroll + flash a report anchor in the editor pane (question/competitor/limitation). */
  onFocusReference: (anchor: RefCitation) => void;
}

/** The session-local selection anchor a reply was generated from. Not persisted;
 * used only so an in-session regenerate can re-use the same (or updated) anchor. */
interface SelectionAnchor {
  selection_text: string | null;
  selection_question_id: string | null;
}

function localId(): string {
  return `local-${crypto.randomUUID()}`;
}

/** "9:42 PM" — hour:minute with AM/PM, locale-formatted. */
function formatTime(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  return d.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
}

/** Flatten to a single line and cap at 60 chars, appending … only if truncated. */
function truncateSelection(text: string): string {
  const flat = text.replace(/\s+/g, " ").trim();
  return flat.length > CHIP_MAX_CHARS
    ? `${flat.slice(0, CHIP_MAX_CHARS)}…`
    : flat;
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
          <span className="flex h-4 w-4 items-center justify-center rounded-full bg-accent text-[10px] font-mono font-bold text-ink-inverse">
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

function refIcon(kind: RefCitation["kind"]) {
  switch (kind) {
    case "question":
      return <FileQuestion className="h-3.5 w-3.5" />;
    case "competitor":
      return <Building2 className="h-3.5 w-3.5" />;
    case "section":
      return <BarChart3 className="h-3.5 w-3.5" />;
    case "limitation":
      return <AlertTriangle className="h-3.5 w-3.5" />;
  }
}

function refLabel(ref: RefCitation): string {
  switch (ref.kind) {
    case "question":
      return ref.value.toUpperCase();
    case "competitor":
      return ref.value;
    case "section":
      return SECTION_LABELS[ref.value as ReportSectionId] ?? ref.value;
    case "limitation":
      return "Limitations";
  }
}

function RefPills({
  refs,
  onActivate,
}: {
  refs: RefCitation[];
  onActivate: (ref: RefCitation) => void;
}) {
  return (
    <div className="mt-2 flex flex-wrap gap-2">
      {refs.map((ref) => (
        <button
          key={`${ref.kind}:${ref.value}`}
          type="button"
          onClick={() => onActivate(ref)}
          title={refLabel(ref)}
          className="flex items-center gap-2 rounded-full border-2 border-border-master bg-surface-card px-3 py-1 font-mono text-mono-sm text-ink-primary transition-shadow hover:shadow-brutal-sm"
        >
          {refIcon(ref.kind)}
          <span className="max-w-[140px] truncate">{refLabel(ref)}</span>
        </button>
      ))}
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
  onFocusReference,
}: EvidenceChatPaneProps) {
  const { toast } = useToast();
  const [messages, setMessages] = useState<ChatHistoryMessage[]>([]);
  const [siblingInfo, setSiblingInfo] = useState<Record<string, SiblingInfo>>(
    {},
  );
  const [input, setInput] = useState("");
  const [loadingHistory, setLoadingHistory] = useState(true);
  const [sending, setSending] = useState(false);
  const [streamingId, setStreamingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [thumbs, setThumbs] = useState<Record<string, EvidenceChatVerdict>>({});
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [regeneratingId, setRegeneratingId] = useState<string | null>(null);
  const [navigatingId, setNavigatingId] = useState<string | null>(null);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editValue, setEditValue] = useState("");

  // Body + optimistic user id of the last failed send, so retry re-fires it.
  const retryRef = useRef<{ body: EvidenceChatSendRequest; userId: string } | null>(
    null,
  );
  // assistant message id -> selection anchor it was generated from (session only).
  const selectionMapRef = useRef<Map<string, SelectionAnchor>>(new Map());
  const thumbsRef = useRef(thumbs);
  const abortRef = useRef<AbortController | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const anchorRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const editTextareaRef = useRef<HTMLTextAreaElement>(null);
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

  const applyBranch = useCallback(
    (
      msgs: ChatHistoryMessage[],
      info: Record<string, SiblingInfo>,
    ) => {
      setMessages(msgs);
      setSiblingInfo(info);
    },
    [],
  );

  const refreshBranch = useCallback(async () => {
    const resp = await getEvidenceChatMessages(experimentId);
    applyBranch(resp.messages, resp.sibling_info);
  }, [experimentId, applyBranch]);

  useEffect(() => {
    let cancelled = false;
    setLoadingHistory(true);
    (async () => {
      try {
        const resp = await getEvidenceChatMessages(experimentId);
        if (cancelled) return;
        applyBranch(resp.messages, resp.sibling_info);
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
  }, [experimentId, toast, applyBranch]);

  // Abort any in-flight stream when the pane unmounts (overlay closed).
  useEffect(() => {
    return () => {
      abortRef.current?.abort();
    };
  }, []);

  // Auto-grow the composer, capped at the max height.
  useLayoutEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, TEXTAREA_MAX_PX)}px`;
  }, [input]);

  // Auto-grow the inline-edit textarea the same way.
  useLayoutEffect(() => {
    const el = editTextareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, TEXTAREA_MAX_PX)}px`;
  }, [editValue, editingId]);

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

  const doStream = useCallback(
    (
      body: EvidenceChatSendRequest,
      optimisticUserId: string,
      pendingAssistantId: string,
    ) => {
      setSending(true);
      setError(null);
      setStreamingId(pendingAssistantId);
      const controller = new AbortController();
      abortRef.current = controller;

      const fail = (message: string) => {
        setMessages((prev) => prev.filter((m) => m.id !== pendingAssistantId));
        retryRef.current = { body, userId: optimisticUserId };
        setError(message);
        setStreamingId(null);
        setSending(false);
        abortRef.current = null;
      };

      void streamEvidenceChatMessage(
        experimentId,
        body,
        {
          onToken: (text) => {
            wasAtBottomRef.current =
              !scrollRef.current ||
              scrollRef.current.scrollHeight -
                scrollRef.current.scrollTop -
                scrollRef.current.clientHeight <
                NEAR_BOTTOM_PX;
            setMessages((prev) =>
              prev.map((m) =>
                m.id === pendingAssistantId
                  ? { ...m, content: m.content + text }
                  : m,
              ),
            );
          },
          onDone: (payload) => {
            selectionMapRef.current.set(payload.assistant_message_id, {
              selection_text: body.selection_text ?? null,
              selection_question_id: body.selection_question_id ?? null,
            });
            setMessages((prev) =>
              prev.map((m) => {
                if (m.id === optimisticUserId)
                  return { ...m, id: payload.user_message_id };
                if (m.id === pendingAssistantId)
                  return { ...m, id: payload.assistant_message_id };
                return m;
              }),
            );
            setSiblingInfo((prev) => ({ ...prev, ...payload.sibling_info }));
            retryRef.current = null;
            setStreamingId(null);
            setSending(false);
            abortRef.current = null;
          },
          onError: fail,
        },
        controller.signal,
      ).catch((err) => {
        if (controller.signal.aborted) return;
        fail(errorMessageFrom(err));
      });
    },
    [experimentId],
  );

  const handleSubmit = useCallback(() => {
    const trimmed = input.trim();
    if (!trimmed || sending || error) return;
    const optimisticUserId = localId();
    const pendingAssistantId = localId();
    const body: EvidenceChatSendRequest = {
      message: trimmed,
      selection_text: selection?.text ?? null,
      selection_question_id: selection?.question_id ?? null,
    };
    const now = new Date().toISOString();
    const userMsg: ChatHistoryMessage = {
      id: optimisticUserId,
      role: "user",
      content: trimmed,
      turn_kind: "evidence_chat",
      created_at: now,
    };
    const pendingMsg: ChatHistoryMessage = {
      id: pendingAssistantId,
      role: "assistant",
      content: "",
      turn_kind: "evidence_chat",
      created_at: now,
    };
    // The user just acted — always follow their own message down.
    wasAtBottomRef.current = true;
    setMessages((prev) => [...prev, userMsg, pendingMsg]);
    setInput("");
    doStream(body, optimisticUserId, pendingAssistantId);
  }, [input, sending, error, selection, doStream]);

  const handleRetry = useCallback(() => {
    const pending = retryRef.current;
    if (!pending) return;
    const pendingAssistantId = localId();
    wasAtBottomRef.current = true;
    setError(null);
    setMessages((prev) => [
      ...prev,
      {
        id: pendingAssistantId,
        role: "assistant",
        content: "",
        turn_kind: "evidence_chat",
        created_at: new Date().toISOString(),
      },
    ]);
    doStream(pending.body, pending.userId, pendingAssistantId);
  }, [doStream]);

  const doFeedback = useCallback(
    async (messageId: string, verdict: EvidenceChatVerdict) => {
      try {
        await sendEvidenceChatFeedback(experimentId, messageId, verdict);
      } catch {
        toast("Couldn't send feedback", "error");
      }
    },
    [experimentId, toast],
  );

  const handleThumb = useCallback(
    (messageId: string, verdict: EvidenceChatVerdict) => {
      if (thumbsRef.current[messageId] === verdict) return;
      setThumbs((prev) => ({ ...prev, [messageId]: verdict }));
      void doFeedback(messageId, verdict);
    },
    [doFeedback],
  );

  const handleCopy = useCallback(
    async (message: ChatHistoryMessage) => {
      try {
        // Raw content WITH [cite:]/[ref:] markers, so the copy is portable.
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
        selectionMapRef.current.delete(message.id);
        selectionMapRef.current.set(fresh.id, anchor);
        setThumbs((prev) => {
          if (!(message.id in prev)) return prev;
          const next = { ...prev };
          delete next[message.id];
          return next;
        });
        // The regenerated reply is a new sibling — resync sibling metadata.
        try {
          await refreshBranch();
        } catch {
          /* non-fatal: the reply is already shown */
        }
      } catch {
        toast("Couldn't regenerate — try again", "error");
      } finally {
        setRegeneratingId(null);
      }
    },
    [experimentId, regeneratingId, toast, refreshBranch],
  );

  const startEdit = useCallback((message: ChatHistoryMessage) => {
    setEditingId(message.id);
    setEditValue(message.content);
  }, []);

  const cancelEdit = useCallback(() => {
    setEditingId(null);
    setEditValue("");
  }, []);

  const saveEdit = useCallback(
    async (messageId: string) => {
      const trimmed = editValue.trim();
      if (!trimmed) return;
      setEditingId(null);
      setEditValue("");
      wasAtBottomRef.current = true;
      try {
        const resp = await editEvidenceChatMessage(experimentId, messageId, {
          content: trimmed,
          selection_text: selection?.text ?? null,
          selection_question_id: selection?.question_id ?? null,
        });
        selectionMapRef.current.set(resp.new_assistant_message.id, {
          selection_text: selection?.text ?? null,
          selection_question_id: selection?.question_id ?? null,
        });
        await refreshBranch();
      } catch {
        toast("Couldn't save the edit — try again", "error");
      }
    },
    [editValue, experimentId, selection, refreshBranch, toast],
  );

  const navigateSibling = useCallback(
    async (info: SiblingInfo, direction: -1 | 1) => {
      if (navigatingId) return;
      const targetIndex = info.sibling_index + direction;
      if (targetIndex < 0 || targetIndex >= info.sibling_ids.length) return;
      const targetId = info.sibling_ids[targetIndex];
      setNavigatingId(targetId);
      try {
        await activateEvidenceChatBranch(experimentId, targetId);
        await refreshBranch();
      } catch {
        toast("Couldn't switch versions — try again", "error");
      } finally {
        setNavigatingId(null);
      }
    },
    [experimentId, navigatingId, refreshBranch, toast],
  );

  const handleRefActivate = useCallback(
    (ref: RefCitation) => {
      if (ref.kind === "section") {
        const label = SECTION_LABELS[ref.value as ReportSectionId] ?? ref.value;
        toast(
          `Section scores were removed from the report — this refers to ${label}`,
          "info",
        );
        return;
      }
      onFocusReference(ref);
    },
    [onFocusReference, toast],
  );

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  }

  function handleEditKeyDown(
    e: React.KeyboardEvent<HTMLTextAreaElement>,
    messageId: string,
  ) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      void saveEdit(messageId);
    } else if (e.key === "Escape") {
      e.preventDefault();
      cancelEdit();
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

  function renderSiblingNav(messageId: string, align: "start" | "end") {
    const info = siblingInfo[messageId];
    if (!info || info.sibling_count <= 1) return null;
    const isNav = navigatingId !== null;
    return (
      <div
        className={`flex ${align === "end" ? "justify-end pr-1" : "pl-1"}`}
      >
        <div
          tabIndex={0}
          role="group"
          aria-label="Switch versions"
          onKeyDown={(e) => {
            if (e.key === "ArrowLeft") {
              e.preventDefault();
              void navigateSibling(info, -1);
            } else if (e.key === "ArrowRight") {
              e.preventDefault();
              void navigateSibling(info, 1);
            }
          }}
          className="inline-flex items-center gap-1 font-mono text-mono-sm text-ink-tertiary focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-ring"
        >
          <button
            type="button"
            onClick={() => navigateSibling(info, -1)}
            disabled={info.sibling_index === 0 || isNav}
            aria-label="Previous version"
            className="transition-colors hover:text-ink-primary disabled:opacity-30"
          >
            <ChevronLeft className="h-3.5 w-3.5" />
          </button>
          <span className="tabular-nums">
            {info.sibling_index + 1}/{info.sibling_count}
          </span>
          <button
            type="button"
            onClick={() => navigateSibling(info, 1)}
            disabled={info.sibling_index === info.sibling_count - 1 || isNav}
            aria-label="Next version"
            className="transition-colors hover:text-ink-primary disabled:opacity-30"
          >
            <ChevronRight className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>
    );
  }

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
                const isEditing = editingId === m.id;
                return (
                  <div key={m.id} className="flex flex-col items-end gap-2">
                    {isEditing ? (
                      <div className="w-full max-w-[85%]">
                        <textarea
                          ref={editTextareaRef}
                          value={editValue}
                          onChange={(e) => setEditValue(e.target.value)}
                          onKeyDown={(e) => handleEditKeyDown(e, m.id)}
                          autoFocus
                          style={{
                            minHeight: TEXTAREA_MIN_PX,
                            maxHeight: TEXTAREA_MAX_PX,
                          }}
                          className="w-full resize-none border-2 border-border-master bg-surface-card px-3 py-2 text-sm text-ink-primary focus:outline-none"
                        />
                        <div className="mt-2 flex justify-end gap-2">
                          <button
                            type="button"
                            onClick={cancelEdit}
                            className="border-2 border-border-master bg-surface-card px-3 py-1 font-mono text-mono-sm uppercase text-ink-primary transition-shadow hover:shadow-brutal-sm"
                          >
                            Cancel
                          </button>
                          <button
                            type="button"
                            onClick={() => saveEdit(m.id)}
                            disabled={!editValue.trim()}
                            className="border-2 border-border-master bg-accent px-3 py-1 font-mono text-mono-sm uppercase text-ink-inverse shadow-brutal-sm disabled:opacity-40"
                          >
                            Save
                          </button>
                        </div>
                      </div>
                    ) : (
                      <>
                        <div className="max-w-[85%] whitespace-pre-wrap break-words border-2 border-border-master bg-accent p-3 text-sm text-ink-inverse shadow-brutal-sm">
                          {m.content}
                        </div>
                        {renderSiblingNav(m.id, "end")}
                        <div className="flex items-center justify-end gap-2 pr-1 text-ink-tertiary">
                          <button
                            type="button"
                            onClick={() => startEdit(m)}
                            aria-label="Edit message"
                            title="Edit"
                            className="transition-colors hover:text-ink-primary"
                          >
                            <Pencil className="h-3.5 w-3.5" />
                          </button>
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
                          <span className="font-mono text-[11px] tabular-nums">
                            {formatTime(m.created_at)}
                          </span>
                        </div>
                      </>
                    )}
                  </div>
                );
              }

              const isStreaming = streamingId === m.id;
              const isRegenerating = regeneratingId === m.id;
              const verdict = thumbs[m.id];
              const { cleanedText, urlCitations, refCitations } = parseCitations(
                m.content,
              );
              const showActions = !isStreaming && !isRegenerating;

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
                    ) : isStreaming && m.content.length === 0 ? (
                      <div className="flex items-center gap-1.5">
                        {[0, 150, 300].map((delay) => (
                          <span
                            key={delay}
                            className="h-2 w-2 animate-pulse rounded-full bg-ink-tertiary"
                            style={{ animationDelay: `${delay}ms` }}
                          />
                        ))}
                      </div>
                    ) : (
                      <>
                        <div className="whitespace-pre-wrap break-words">
                          {cleanedText}
                        </div>
                        {!isStreaming && urlCitations.length > 0 && (
                          <SourcePills
                            urls={urlCitations}
                            lookup={citationLookup}
                          />
                        )}
                        {!isStreaming && refCitations.length > 0 && (
                          <RefPills
                            refs={refCitations}
                            onActivate={handleRefActivate}
                          />
                        )}
                      </>
                    )}
                  </div>

                  {showActions && renderSiblingNav(m.id, "start")}

                  {showActions && (
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
                            ? "text-accent"
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
                            ? "text-accent"
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
                      <span className="font-mono text-[11px] tabular-nums">
                        {formatTime(m.created_at)}
                      </span>
                    </div>
                  )}
                </div>
              );
            })}
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
                : "bg-accent text-ink-inverse"
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
