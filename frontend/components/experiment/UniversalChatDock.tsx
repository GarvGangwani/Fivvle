"use client";

import {
  memo,
  useCallback,
  useEffect,
  useLayoutEffect,
  useRef,
  useState,
  type DragEvent,
  type KeyboardEvent,
  type ReactNode,
} from "react";
import {
  ArrowUp,
  Check,
  File,
  FileText,
  Loader2,
  Maximize2,
  MessageSquare,
  Pencil,
  Plus,
  Square,
  X,
} from "lucide-react";
import { ChatMarkdown } from "@/components/chat/ChatMarkdown";
import { MessageAttachments } from "@/components/experiment/refine/MessageAttachments";
import { useToast } from "@/components/ui/ToastProvider";
import {
  ApiError,
  cancelUniversalChatTurn,
  captureExperimentIdea,
  getUniversalChatMessages,
  streamCaptureGreeting,
  streamUniversalChatMessage,
  uploadChatAttachments,
} from "@/lib/api";
import { IdeaCaptureCard } from "@/components/experiment/IdeaCaptureCard";
import { downscaleImageForUpload } from "@/lib/downscale-image";
import { parseRefAnchor, tokenizeCitations } from "@/lib/parse-citations";
import { setPendingEvidenceFocus } from "@/lib/pending-evidence-focus";
import type {
  ChatHistoryMessage,
  RefineMcqOption,
  RefineSubagentToolResult,
  RefCitation,
  ResearchSubagentSourceRef,
} from "@/lib/types";

export type UniversalOpenPhase =
  | "refine"
  | "evidence"
  | "launch"
  | "signal";

const WORKING_LABELS: Record<string, string | null> = {
  get_metrics_summary: "Checking your metrics…",
  get_report_summary: "Reading the report…",
  get_research_context: "Pulling the research…",
  get_landing_status: "Checking the landing page…",
  ask_refine_agent: "Thinking through your idea…",
  open_phase_panel: null,
};

function workingLabelForTool(toolName: string): string | null {
  return toolName in WORKING_LABELS ? WORKING_LABELS[toolName] : "Working…";
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

/** Sentence-case UPPERCASE MCQ labels for readable chat bubbles. */
function sentenceCaseMcqLabel(label: string): string {
  const lowered = label.trim().toLowerCase();
  if (!lowered) return lowered;
  const idx = lowered.search(/[a-z]/);
  if (idx < 0) return lowered;
  return lowered.slice(0, idx) + lowered[idx]!.toUpperCase() + lowered.slice(idx + 1);
}

/** Natural join: "A", "A and B", "A, B, and C". */
function formatMcqAnswerDisplay(labels: string[]): string {
  const cleaned = labels.map(sentenceCaseMcqLabel).filter(Boolean);
  if (cleaned.length === 0) return "";
  if (cleaned.length === 1) return cleaned[0]!;
  if (cleaned.length === 2) return `${cleaned[0]} and ${cleaned[1]}`;
  return `${cleaned.slice(0, -1).join(", ")}, and ${cleaned[cleaned.length - 1]}`;
}

function parseRefineSubagentResult(
  payload: ChatHistoryMessage["tool_payload"],
): RefineSubagentToolResult | null {
  const root = asRecord(payload);
  if (!root || root.tool_name !== "ask_refine_agent") return null;
  if (typeof root.error === "string" && root.result == null) return null;
  const result = asRecord(root.result);
  if (!result) return null;
  // Question-only turns may omit prose; treat missing assistant_text as "".
  if (
    result.assistant_text != null &&
    typeof result.assistant_text !== "string"
  ) {
    return null;
  }

  const optionsRaw = Array.isArray(result.mcq_options) ? result.mcq_options : [];
  const mcq_options: RefineMcqOption[] = [];
  for (const item of optionsRaw) {
    const row = asRecord(item);
    if (!row || typeof row.label !== "string") continue;
    const index =
      typeof row.index === "number"
        ? row.index
        : typeof row.index === "string"
          ? Number(row.index)
          : NaN;
    if (!Number.isFinite(index)) continue;
    mcq_options.push({ index, label: row.label });
  }

  const mode = result.mcq_selection_mode;
  const mcq_selection_mode: "single" | "multiple" =
    mode === "single" ? "single" : "multiple";

  return {
    assistant_text:
      typeof result.assistant_text === "string" ? result.assistant_text : "",
    refined_idea_patch:
      result.refined_idea_patch && typeof result.refined_idea_patch === "object"
        ? (result.refined_idea_patch as Record<string, unknown>)
        : null,
    has_pending_mcq: Boolean(result.has_pending_mcq),
    log_entry: typeof result.log_entry === "string" ? result.log_entry : null,
    mcq_question:
      typeof result.mcq_question === "string" ? result.mcq_question : null,
    mcq_options,
    mcq_answered_question_id:
      typeof result.mcq_answered_question_id === "string"
        ? result.mcq_answered_question_id
        : null,
    mcq_selection_mode,
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

function parseNavigateResult(
  payload: ChatHistoryMessage["tool_payload"],
): { navigate_to: UniversalOpenPhase; source_ref_id: string | null } | null {
  const root = asRecord(payload);
  if (!root || root.tool_name !== "open_phase_panel") return null;
  if (typeof root.error === "string" && root.result == null) return null;
  const result = asRecord(root.result) ?? root;
  const navigateTo = result.navigate_to;
  if (
    navigateTo !== "refine" &&
    navigateTo !== "evidence" &&
    navigateTo !== "launch" &&
    navigateTo !== "signal"
  ) {
    return null;
  }
  return {
    navigate_to: navigateTo,
    source_ref_id:
      typeof result.source_ref_id === "string" ? result.source_ref_id : null,
  };
}

function extractSourceRefs(
  payload: Record<string, unknown>,
): ResearchSubagentSourceRef[] {
  const result = asRecord(payload.result) ?? payload;
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
  return source_refs;
}

function QuestionCard({
  question,
  options,
  answeredQuestionId,
  selectionMode,
  disabled = false,
  onAnswer,
  onSkip,
}: {
  question: string | null;
  options: RefineMcqOption[];
  answeredQuestionId: string;
  selectionMode: "single" | "multiple";
  disabled?: boolean;
  onAnswer?: (answer: { indices: number[]; labels: string[] }) => void;
  onSkip?: () => void;
}) {
  const [selected, setSelected] = useState<number[]>([]);

  const submit = (indices: number[]) => {
    if (!onAnswer || indices.length === 0) return;
    const labels = indices
      .map((i) => options.find((o) => o.index === i)?.label)
      .filter((label): label is string => typeof label === "string");
    onAnswer({ indices, labels });
  };

  return (
    <section
      aria-label={`Question ${answeredQuestionId}`}
      className="flex max-h-[min(50vh,24rem)] w-full flex-col rounded-t-md rounded-b-none border border-b-0 border-border-master bg-[var(--fv-surface-muted)] px-2.5 pb-2 pt-2"
    >
      <div className="shrink-0 space-y-1.5 pb-2">
        <p className="font-mono text-mono-sm uppercase tracking-[0.14em] text-accent">
          Question
        </p>
        {question ? (
          <h3 className="text-[13px] font-medium leading-snug text-ink-primary">
            {question}
          </h3>
        ) : null}
      </div>

      <div className="min-h-0 flex-1 space-y-1 overflow-y-auto pr-0.5">
        {options.map((opt) => {
          const isSelected = selected.includes(opt.index);
          return (
            <button
              key={opt.index}
              type="button"
              disabled={disabled || !onAnswer}
              onClick={() => {
                if (selectionMode === "single") {
                  submit([opt.index]);
                  return;
                }
                setSelected((prev) =>
                  prev.includes(opt.index)
                    ? prev.filter((i) => i !== opt.index)
                    : [...prev, opt.index].sort((a, b) => a - b),
                );
              }}
              className={`group relative flex w-full items-start gap-2 overflow-hidden rounded-sm border bg-[var(--fv-surface-card)] py-1.5 pl-3 pr-2 text-left transition-[background-color,border-color,transform] duration-100 ease-out disabled:cursor-not-allowed disabled:opacity-50 ${
                isSelected
                  ? "border-accent bg-accent-muted"
                  : "border-border-master hover:border-[color-mix(in_srgb,var(--fv-accent)_55%,var(--fv-border-master))] hover:bg-[color-mix(in_srgb,var(--fv-accent)_6%,var(--fv-surface-card))] active:translate-x-px"
              }`}
            >
              <span
                aria-hidden
                className={`absolute inset-y-0 left-0 w-[3px] transition-colors duration-100 ${
                  isSelected
                    ? "bg-accent"
                    : "bg-transparent group-hover:bg-accent"
                }`}
              />
              <span
                className={`mt-px shrink-0 font-mono text-[10px] font-medium tabular-nums leading-none tracking-tight transition-colors duration-100 ${
                  isSelected
                    ? "text-accent"
                    : "text-ink-tertiary group-hover:text-accent"
                }`}
              >
                {String(opt.index + 1).padStart(2, "0")}
              </span>
              <span className="min-w-0 flex-1 text-[13px] leading-snug text-ink-primary">
                {opt.label}
              </span>
              {selectionMode === "multiple" && isSelected ? (
                <Check
                  className="mt-0.5 h-3.5 w-3.5 shrink-0 text-accent"
                  aria-hidden
                  strokeWidth={2.5}
                />
              ) : null}
            </button>
          );
        })}
      </div>

      <div className="flex shrink-0 items-center justify-between gap-2 px-0.5 pt-2">
        <button
          type="button"
          disabled={disabled || !onSkip}
          onClick={onSkip}
          className="font-mono text-[10px] uppercase tracking-[0.12em] text-ink-tertiary transition-colors hover:text-ink-primary disabled:opacity-40"
        >
          Skip
        </button>
        {selectionMode === "multiple" ? (
          <button
            type="button"
            disabled={disabled || !onAnswer || selected.length === 0}
            onClick={() => submit(selected)}
            className="h-7 shrink-0 rounded-sm border border-border-master bg-accent px-3 font-mono text-[10px] uppercase tracking-wider text-accent-fg transition-colors hover:bg-accent-hover disabled:cursor-not-allowed disabled:opacity-40"
          >
            Submit
          </button>
        ) : null}
      </div>
    </section>
  );
}

type PendingQuestion = {
  messageId: string;
  question: string | null;
  options: RefineMcqOption[];
  answeredQuestionId: string;
  selectionMode: "single" | "multiple";
};

function refineResultAsPendingQuestion(
  messageId: string,
  refine: RefineSubagentToolResult,
): PendingQuestion | null {
  if (
    !(refine.has_pending_mcq || refine.mcq_question != null) ||
    refine.mcq_options.length === 0 ||
    refine.mcq_answered_question_id == null
  ) {
    return null;
  }
  return {
    messageId,
    question: refine.mcq_question,
    options: refine.mcq_options,
    answeredQuestionId: refine.mcq_answered_question_id,
    selectionMode: refine.mcq_selection_mode,
  };
}

/** Latest unanswered refine MCQ in history, or null. */
function pendingQuestionFromMessages(
  messages: ChatHistoryMessage[],
): PendingQuestion | null {
  for (let i = messages.length - 1; i >= 0; i--) {
    const msg = messages[i];
    if (msg.role !== "tool_result") continue;
    const refine = parseRefineSubagentResult(msg.tool_payload);
    if (!refine) continue;
    const pending = refineResultAsPendingQuestion(msg.id, refine);
    if (!pending) continue;
    const answeredLater = messages
      .slice(i + 1)
      .some(
        (m) =>
          m.role === "user" ||
          m.role === "tool_call" ||
          m.role === "assistant",
      );
    return answeredLater ? null : pending;
  }
  return null;
}

function isExternalHttpUrl(url: string | null | undefined): url is string {
  if (!url?.trim()) return false;
  try {
    const parsed = new URL(url.trim());
    return parsed.protocol === "http:" || parsed.protocol === "https:";
  } catch {
    return false;
  }
}

function citationDomain(ref: ResearchSubagentSourceRef): string | null {
  const fromMeta = ref.source_domain?.trim().replace(/^www\./i, "");
  if (fromMeta) return fromMeta;
  if (!isExternalHttpUrl(ref.source_url)) return null;
  try {
    return new URL(ref.source_url).hostname.replace(/^www\./i, "") || null;
  } catch {
    return null;
  }
}

function googleFaviconUrl(domain: string): string {
  return `https://www.google.com/s2/favicons?domain=${encodeURIComponent(domain)}&sz=64`;
}

function InlineCitationChip({
  variant,
  indexLabel,
  domain,
  title,
  href,
  onClick,
}: {
  variant: "source" | "report";
  /** Superscript fallback when favicon fails, e.g. "1" from s1. */
  indexLabel: string;
  domain?: string | null;
  title?: string;
  /** External source — opens in a new tab. */
  href?: string;
  onClick?: () => void;
}) {
  const [faviconFailed, setFaviconFailed] = useState(false);
  const className =
    "ml-0.5 inline-flex h-3.5 w-3.5 shrink-0 items-center justify-center align-text-bottom text-ink-tertiary transition-opacity hover:opacity-80 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-accent-ring";

  let body: ReactNode;
  if (variant === "report") {
    body = <FileText className="h-3.5 w-3.5" aria-hidden />;
  } else if (domain && !faviconFailed) {
    body = (
      // eslint-disable-next-line @next/next/no-img-element -- remote favicon service; next/image not appropriate
      <img
        src={googleFaviconUrl(domain)}
        alt=""
        width={14}
        height={14}
        className="h-3.5 w-3.5 rounded-[2px]"
        loading="lazy"
        decoding="async"
        onError={() => setFaviconFailed(true)}
      />
    );
  } else {
    body = (
      <span className="align-super text-[0.65em] font-medium leading-none tracking-tight">
        {indexLabel}
      </span>
    );
  }

  if (href) {
    return (
      <a
        href={href}
        target="_blank"
        rel="noopener noreferrer"
        title={title || undefined}
        className={className}
        aria-label={title || "Open source"}
      >
        {body}
      </a>
    );
  }

  if (onClick) {
    return (
      <button
        type="button"
        title={title || undefined}
        onClick={onClick}
        className={className}
        aria-label={title || "Open in report"}
      >
        {body}
      </button>
    );
  }

  return (
    <span title={title || undefined} className={className}>
      {body}
    </span>
  );
}

function citationIndexLabel(ref: ResearchSubagentSourceRef): string {
  const idMatch = /\[cite:\s*s(\d+)\]/i.exec(ref.marker_id);
  if (idMatch) return idMatch[1];
  const domain = ref.source_domain?.trim();
  if (domain) return domain.slice(0, 12);
  return "·";
}

function citationHoverTitle(ref: ResearchSubagentSourceRef): string | undefined {
  const parts = [
    ref.source_domain?.trim() || null,
    ref.source_title.trim() || null,
    ref.source_url,
  ].filter(Boolean);
  return parts.length > 0 ? parts.join(" — ") : undefined;
}

function reportRefHoverTitle(ref: RefCitation): string {
  switch (ref.kind) {
    case "question":
      return `Report — ${ref.value.toUpperCase()}`;
    case "competitor":
      return `Report — competitor: ${ref.value}`;
    case "section":
      return `Report — section: ${ref.value}`;
    case "limitation":
      return "Report — Research Limitations";
    case "url":
      return `Report — ${ref.value}`;
  }
}

function openReportCitationInEvidence(
  onOpenPhase: (
    phase: UniversalOpenPhase,
    options?: { sourceRef?: ResearchSubagentSourceRef | null },
  ) => void,
  anchor: RefCitation,
  sourceRef?: ResearchSubagentSourceRef,
): void {
  setPendingEvidenceFocus(anchor);
  onOpenPhase("evidence", sourceRef ? { sourceRef } : undefined);
}

function focusAnchorForSourceRef(ref: ResearchSubagentSourceRef): RefCitation {
  if (ref.source_url?.trim()) {
    return { kind: "url", value: ref.source_url.trim() };
  }
  if (ref.source_domain?.trim()) {
    return { kind: "url", value: ref.source_domain.trim() };
  }
  return { kind: "url", value: "" };
}

function ResearchTextWithCitationChips({
  text,
  sourceRefs,
  onSourceCitationClick,
  onReportRefClick,
}: {
  text: string;
  sourceRefs: ResearchSubagentSourceRef[];
  /** Non-external cites (no usable http URL) — open evidence panel. */
  onSourceCitationClick?: (ref: ResearchSubagentSourceRef) => void;
  /** `[ref:…]` in-report anchors. */
  onReportRefClick?: (ref: RefCitation) => void;
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

        const reportBody = /\[ref:\s*([^\]]*)\]/i.exec(token.marker);
        if (reportBody) {
          const reportRef = parseRefAnchor(reportBody[1]);
          if (reportRef) {
            return (
              <InlineCitationChip
                key={`ref-${index}`}
                variant="report"
                indexLabel="¶"
                title={reportRefHoverTitle(reportRef)}
                onClick={
                  onReportRefClick
                    ? () => onReportRefClick(reportRef)
                    : undefined
                }
              />
            );
          }
        }

        const idMatch = /\[cite:\s*(s\d+)\]/i.exec(token.marker);
        const ref =
          byMarker.get(token.marker.toLowerCase()) ??
          (idMatch ? byId.get(idMatch[1].toLowerCase()) : undefined);
        if (!ref) {
          return (
            <span
              key={`raw-${index}`}
              className="align-super text-[0.65em] text-ink-tertiary"
            >
              {token.marker}
            </span>
          );
        }

        const external = isExternalHttpUrl(ref.source_url);
        return (
          <InlineCitationChip
            key={`cite-${index}`}
            variant={external ? "source" : "report"}
            indexLabel={citationIndexLabel(ref)}
            domain={external ? citationDomain(ref) : null}
            title={citationHoverTitle(ref)}
            href={external ? ref.source_url! : undefined}
            onClick={
              !external && onSourceCitationClick
                ? () => onSourceCitationClick(ref)
                : undefined
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
  /** Currently open canvas overlay act (null when closed). */
  currentOpenPhase?: UniversalOpenPhase | null;
  /** Open a phase panel from navigate / citation / MCQ. */
  onOpenPhase?: (
    phase: UniversalOpenPhase,
    options?: { sourceRef?: ResearchSubagentSourceRef | null },
  ) => void;
  /** When true, show the one-shot idea capture card as the first turn. */
  needsIdeaCapture?: boolean;
  /** After successful capture — parent refreshes experiment detail. */
  onIdeaCaptured?: () => void | Promise<void>;
  /**
   * Ask the founder about the AI-suggested canvas palette. Resolves once they
   * answer (either way), which is what holds the refine handoff until then.
   */
  onPaletteSuggested?: (paletteName: string) => Promise<void>;
};

type DockMessage = ChatHistoryMessage & {
  /** Client-only optimistic / error flags */
  optimistic?: boolean;
  error?: boolean;
};

type DraftAttachment = {
  localId: string;
  file: File;
  filename: string;
  previewUrl: string | null;
  status: "uploading" | "ready" | "error";
  serverId?: string;
  contentKind?: string;
  errorMessage?: string;
};

const SCROLL_NEAR_BOTTOM_THRESHOLD_PX = 100;
const TEXTAREA_MAX_PX = 120;
const COLLAPSE_KEY_PREFIX = "fivvle-universal-chat-collapsed";
const MAX_DRAFT_ATTACHMENTS = 5;
const MAX_DRAFT_ATTACHMENT_BYTES = 10 * 1024 * 1024;
const ACCEPTED_EXTENSIONS = new Set([
  "png",
  "jpg",
  "jpeg",
  "webp",
  "pdf",
  "txt",
  "md",
  "markdown",
  "docx",
]);
const FILE_ACCEPT =
  "image/png,image/jpeg,image/webp,application/pdf,text/plain,text/markdown,.md,.txt,.docx,application/vnd.openxmlformats-officedocument.wordprocessingml.document";

function collapseStorageKey(experimentId: string): string {
  return `${COLLAPSE_KEY_PREFIX}:${experimentId}`;
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function fileExtension(name: string): string {
  const idx = name.lastIndexOf(".");
  return idx >= 0 ? name.slice(idx + 1).toLowerCase() : "";
}

function isAcceptedAttachmentFile(file: File): boolean {
  const ext = fileExtension(file.name);
  if (ACCEPTED_EXTENSIONS.has(ext)) return true;
  const mime = file.type.toLowerCase();
  return (
    mime === "image/png" ||
    mime === "image/jpeg" ||
    mime === "image/webp" ||
    mime === "application/pdf" ||
    mime === "text/plain" ||
    mime === "text/markdown" ||
    mime ===
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
  );
}

function revokePreview(url: string | null) {
  if (url) URL.revokeObjectURL(url);
}

/** Session-scoped blob URLs for sent attachment thumbs (lost on full reload). */
const attachmentPreviewById = new Map<string, string>();

function registerAttachmentPreview(id: string, url: string) {
  const prev = attachmentPreviewById.get(id);
  if (prev && prev !== url) URL.revokeObjectURL(prev);
  attachmentPreviewById.set(id, url);
}

function getAttachmentPreview(id: string): string | null {
  return attachmentPreviewById.get(id) ?? null;
}

function unregisterAttachmentPreview(id: string) {
  const url = attachmentPreviewById.get(id);
  if (url) {
    URL.revokeObjectURL(url);
    attachmentPreviewById.delete(id);
  }
}

function isImageAttachmentFile(file: File): boolean {
  if (file.type.startsWith("image/")) return true;
  const ext = fileExtension(file.name);
  return ext === "png" || ext === "jpg" || ext === "jpeg" || ext === "webp";
}

function DocGlyph({ filename }: { filename: string }) {
  const ext = fileExtension(filename);
  if (ext === "pdf") return <File className="h-3.5 w-3.5 shrink-0" aria-hidden />;
  return <FileText className="h-3.5 w-3.5 shrink-0" aria-hidden />;
}

function DraftThumb({
  previewUrl,
  filename,
}: {
  previewUrl: string | null;
  filename: string;
}) {
  const [failed, setFailed] = useState(false);
  if (!previewUrl || failed) {
    return (
      <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-sm border border-border-master bg-[var(--fv-surface-muted)] text-[var(--fv-text-muted)]">
        <DocGlyph filename={filename} />
      </div>
    );
  }
  return (
    <div className="h-9 w-9 shrink-0 overflow-hidden rounded-sm border border-border-master bg-[var(--fv-surface-muted)]">
      {/* eslint-disable-next-line @next/next/no-img-element -- local blob: preview */}
      <img
        src={previewUrl}
        alt=""
        className="h-9 w-9 object-cover"
        onError={() => setFailed(true)}
      />
    </div>
  );
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

export const UniversalChatDock = memo(function UniversalChatDock({
  experimentId,
  projectName,
  onCollapsedChange,
  currentOpenPhase = null,
  onOpenPhase,
  needsIdeaCapture = false,
  onIdeaCaptured,
  onPaletteSuggested,
}: Props) {
  const { toast } = useToast();
  const [collapsed, setCollapsed] = useState(false);
  const [capturing, setCapturing] = useState(false);
  /** Capture card waits until the greeting stream finishes (or history already has it). */
  const [captureGreetingComplete, setCaptureGreetingComplete] = useState(
    () => !needsIdeaCapture,
  );
  const greetingAbortRef = useRef<AbortController | null>(null);
  const needsIdeaCaptureRef = useRef(needsIdeaCapture);
  needsIdeaCaptureRef.current = needsIdeaCapture;
  const [messages, setMessages] = useState<DockMessage[]>([]);
  const [historyLoading, setHistoryLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [draft, setDraft] = useState("");
  const [draftAttachments, setDraftAttachments] = useState<DraftAttachment[]>(
    [],
  );
  const [attachError, setAttachError] = useState<string | null>(null);
  const [dragActive, setDragActive] = useState(false);
  const [workingLabel, setWorkingLabel] = useState<string | null>(null);
  const [streamingAssistantText, setStreamingAssistantText] = useState("");
  const [pendingSourceRefs, setPendingSourceRefs] = useState<
    ResearchSubagentSourceRef[]
  >([]);
  /** Active refine question docked above the input (null when none). */
  const [pendingQuestion, setPendingQuestion] = useState<PendingQuestion | null>(
    null,
  );
  const [editingMessageId, setEditingMessageId] = useState<string | null>(null);
  const [editDraft, setEditDraft] = useState("");
  /** Hold MCQ from tool_result until the turn finishes so the card never races streaming text. */
  const heldPendingQuestionRef = useRef<PendingQuestion | null>(null);
  const dispatchedNavigateIdsRef = useRef<Set<string>>(new Set());
  const stoppedRef = useRef(false);

  const named = displayProjectName(projectName);
  const placeholder = pendingQuestion
    ? "Type your own answer…"
    : named
      ? `Ask anything about ${named}`
      : "Ask anything about this project";
  const emptyCopy = needsIdeaCapture
    ? "Capture your original idea to unlock the canvas."
    : named
      ? `Ask me anything about ${named}.`
      : "Ask me anything about your project.";

  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const scrollAnchorRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const dragDepthRef = useRef(0);
  const isNearBottomRef = useRef(true);
  const forceScrollRef = useRef(false);
  const streamAbortRef = useRef<AbortController | null>(null);
  /** Durable turn id for explicit stop (reload must not cancel). */
  const activeTurnIdRef = useRef<string | null>(null);
  const pollTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const streamingAssistantIdRef = useRef<string | null>(null);
  /** Full token accumulation — commit source of truth (never read inside setState). */
  const streamingAssistantTextRef = useRef("");

  const resetStreamingState = useCallback(() => {
    streamingAssistantTextRef.current = "";
    setStreamingAssistantText("");
  }, []);

  const handleIdeaCapture = useCallback(
    async (payload: { ideaText: string; attachmentIds: string[] }) => {
      if (capturing) return;
      setCapturing(true);
      try {
        const captured = await captureExperimentIdea(experimentId, {
          idea_text: payload.ideaText,
          attachment_ids: payload.attachmentIds,
        });
        await onIdeaCaptured?.();
        const history = await getUniversalChatMessages(experimentId);
        setMessages(history.messages ?? []);
        setPendingQuestion(pendingQuestionFromMessages(history.messages ?? []));
        forceScrollRef.current = true;

        // Founder answers the theme suggestion before refine takes over the canvas.
        await onPaletteSuggested?.(captured.suggested_palette);

        // Agent-initiated refine handoff — no new founder message.
        const abort = new AbortController();
        streamAbortRef.current?.abort();
        streamAbortRef.current = abort;
        setSending(true);
        setWorkingLabel("Thinking through your idea…");
        resetStreamingState();
        heldPendingQuestionRef.current = null;
        stoppedRef.current = false;
        onOpenPhase?.("refine");

        try {
          await streamUniversalChatMessage(
            experimentId,
            "",
            {
              onTurnStarted: ({ turn_id }) => {
                activeTurnIdRef.current = turn_id;
              },
              onToolCall: ({ tool_name, message_id }) => {
                if (abort.signal.aborted || stoppedRef.current) return;
                const label = workingLabelForTool(tool_name);
                if (label) setWorkingLabel(label);
                setMessages((prev) => [
                  ...prev,
                  stubToolCallMessage(tool_name, message_id),
                ]);
                forceScrollRef.current = true;
              },
              onToolResult: ({ tool_name, message_id, payload }) => {
                if (abort.signal.aborted || stoppedRef.current) return;
                const toolPayload =
                  typeof payload.tool_name === "string"
                    ? payload
                    : { tool_name, ...payload };
                if (tool_name === "ask_refine_agent") {
                  const refine = parseRefineSubagentResult(toolPayload);
                  if (refine) {
                    heldPendingQuestionRef.current =
                      refineResultAsPendingQuestion(message_id, refine);
                  }
                }
                if (tool_name === "open_phase_panel") {
                  const phase = (payload as { phase?: string }).phase;
                  if (
                    phase === "refine" ||
                    phase === "evidence" ||
                    phase === "launch" ||
                    phase === "signal"
                  ) {
                    onOpenPhase?.(phase);
                  }
                }
                setMessages((prev) => [
                  ...prev,
                  toolResultFromEvent(tool_name, message_id, payload),
                ]);
                forceScrollRef.current = true;
              },
              onSubagentToken: () => {},
              onAssistantToken: ({ text }) => {
                if (abort.signal.aborted || stoppedRef.current) return;
                setWorkingLabel(null);
                streamingAssistantTextRef.current += text;
                setStreamingAssistantText(streamingAssistantTextRef.current);
              },
              onDone: ({ assistant_message_id }) => {
                if (abort.signal.aborted || stoppedRef.current) return;
                setWorkingLabel(null);
                activeTurnIdRef.current = null;
                const committed = streamingAssistantTextRef.current;
                if (committed && assistant_message_id) {
                  setMessages((prev) => [
                    ...prev,
                    {
                      id: assistant_message_id,
                      role: "assistant",
                      content: committed,
                      turn_kind: "universal_chat",
                      created_at: new Date().toISOString(),
                      tool_payload: null,
                    },
                  ]);
                }
                const held = heldPendingQuestionRef.current;
                heldPendingQuestionRef.current = null;
                if (held) setPendingQuestion(held);
                requestAnimationFrame(() => {
                  streamingAssistantTextRef.current = "";
                  setStreamingAssistantText("");
                });
                void getUniversalChatMessages(experimentId).then((next) => {
                  setMessages(next.messages ?? []);
                  setPendingQuestion(
                    pendingQuestionFromMessages(next.messages ?? []),
                  );
                });
              },
              onError: (message) => {
                if (abort.signal.aborted || stoppedRef.current) return;
                setWorkingLabel(null);
                toast(message, "error");
                resetStreamingState();
              },
            },
            abort.signal,
            {
              current_open_phase: "refine",
              kick: "post_capture_refine",
            },
          );
        } catch {
          if (!abort.signal.aborted) {
            toast("Couldn’t start refine. Try asking in chat.", "error");
          }
        } finally {
          if (streamAbortRef.current === abort) {
            streamAbortRef.current = null;
          }
          setSending(false);
          setWorkingLabel(null);
        }
      } catch (err) {
        if (err instanceof ApiError && err.status === 409) {
          await onIdeaCaptured?.();
          return;
        }
        const message =
          err instanceof Error && err.message
            ? err.message
            : "Couldn’t capture your idea. Try again.";
        toast(message, "error");
      } finally {
        setCapturing(false);
      }
    },
    [
      capturing,
      experimentId,
      onIdeaCaptured,
      onOpenPhase,
      onPaletteSuggested,
      resetStreamingState,
      toast,
    ],
  );

  const readyAttachmentIds = draftAttachments
    .filter((a) => a.status === "ready" && a.serverId)
    .map((a) => a.serverId!);
  const attachmentsUploading = draftAttachments.some(
    (a) => a.status === "uploading",
  );
  const canSend =
    !sending &&
    !attachmentsUploading &&
    (draft.trim().length > 0 || readyAttachmentIds.length > 0);

  const uploadOneDraft = useCallback(async (localId: string, file: File) => {
    try {
      const toUpload = isImageAttachmentFile(file)
        ? await downscaleImageForUpload(file)
        : file;
      const uploaded = await uploadChatAttachments([toUpload]);
      const item = uploaded[0];
      if (!item) throw new Error("Upload returned no attachment.");
      setDraftAttachments((prev) =>
        prev.map((row) => {
          if (row.localId !== localId) return row;
          if (row.previewUrl) {
            registerAttachmentPreview(item.id, row.previewUrl);
          }
          return {
            ...row,
            status: "ready" as const,
            serverId: item.id,
            contentKind: item.content_kind,
            errorMessage: undefined,
          };
        }),
      );
    } catch (err) {
      let message = "Upload failed. Try again.";
      if (err instanceof Error && err.message && !err.message.startsWith("API ")) {
        message = err.message;
      } else if (err && typeof err === "object" && "body" in err) {
        const body = (err as { body: unknown }).body;
        if (typeof body === "string" && body.trim()) message = body;
        else if (
          body &&
          typeof body === "object" &&
          "detail" in body &&
          typeof (body as { detail: unknown }).detail === "string"
        ) {
          message = (body as { detail: string }).detail;
        }
      }
      setDraftAttachments((prev) =>
        prev.map((row) =>
          row.localId === localId
            ? { ...row, status: "error", errorMessage: message }
            : row,
        ),
      );
      toast(message, "error");
    }
  }, [toast]);

  const addFiles = useCallback(
    (files: File[]) => {
      if (files.length === 0) return;
      setAttachError(null);

      const accepted: File[] = [];
      for (const file of files) {
        if (!isAcceptedAttachmentFile(file)) {
          setAttachError(
            `"${file.name}" isn’t supported. Use PNG, JPEG, WebP, PDF, TXT, Markdown, or DOCX.`,
          );
          continue;
        }
        if (file.size > MAX_DRAFT_ATTACHMENT_BYTES) {
          setAttachError(`"${file.name}" is larger than 10 MB.`);
          continue;
        }
        accepted.push(file);
      }
      if (accepted.length === 0) return;

      setDraftAttachments((prev) => {
        const remaining = MAX_DRAFT_ATTACHMENTS - prev.length;
        if (remaining <= 0) {
          setAttachError(
            `You can attach up to ${MAX_DRAFT_ATTACHMENTS} files per message.`,
          );
          return prev;
        }
        if (accepted.length > remaining) {
          setAttachError(
            `Only ${remaining} more file(s) can be attached (max ${MAX_DRAFT_ATTACHMENTS}).`,
          );
        }
        const batch = accepted.slice(0, remaining).map((file) => {
          const localId = crypto.randomUUID();
          const previewUrl = isImageAttachmentFile(file)
            ? URL.createObjectURL(file)
            : null;
          void uploadOneDraft(localId, file);
          return {
            localId,
            file,
            filename: file.name,
            previewUrl,
            status: "uploading" as const,
          };
        });
        return [...prev, ...batch];
      });
    },
    [uploadOneDraft],
  );

  const removeDraftAttachment = useCallback((localId: string) => {
    setDraftAttachments((prev) => {
      const target = prev.find((row) => row.localId === localId);
      if (target?.serverId && attachmentPreviewById.has(target.serverId)) {
        // Keep registered URL if somehow already sent — only revoke unregistered.
        // Draft removal before send: unregister so we don't leak.
        unregisterAttachmentPreview(target.serverId);
      } else {
        revokePreview(target?.previewUrl ?? null);
      }
      return prev.filter((row) => row.localId !== localId);
    });
    setAttachError(null);
  }, []);

  const retryDraftAttachment = useCallback(
    (localId: string) => {
      const target = draftAttachments.find((row) => row.localId === localId);
      if (!target) return;
      setDraftAttachments((prev) =>
        prev.map((row) =>
          row.localId === localId
            ? { ...row, status: "uploading", errorMessage: undefined }
            : row,
        ),
      );
      void uploadOneDraft(localId, target.file);
    },
    [draftAttachments, uploadOneDraft],
  );

  useEffect(() => {
    return () => {
      for (const [id, url] of [...attachmentPreviewById.entries()]) {
        URL.revokeObjectURL(url);
        attachmentPreviewById.delete(id);
      }
    };
  }, [experimentId]);

  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    const handlePaste = (e: ClipboardEvent) => {
      const collected: File[] = [];
      if (e.clipboardData?.files && e.clipboardData.files.length > 0) {
        collected.push(...Array.from(e.clipboardData.files));
      } else if (e.clipboardData?.items) {
        for (const item of Array.from(e.clipboardData.items)) {
          if (item.kind !== "file") continue;
          const file = item.getAsFile();
          if (file) collected.push(file);
        }
      }
      if (collected.length === 0) return;
      e.preventDefault();
      addFiles(collected);
    };
    el.addEventListener("paste", handlePaste);
    return () => el.removeEventListener("paste", handlePaste);
  }, [addFiles, pendingQuestion]);

  const onDragEnter = (e: DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    dragDepthRef.current += 1;
    if (e.dataTransfer.types.includes("Files")) setDragActive(true);
  };
  const onDragLeave = (e: DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    dragDepthRef.current = Math.max(0, dragDepthRef.current - 1);
    if (dragDepthRef.current === 0) setDragActive(false);
  };
  const onDragOver = (e: DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.dataTransfer.types.includes("Files")) {
      e.dataTransfer.dropEffect = "copy";
    }
  };
  const onDrop = (e: DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    dragDepthRef.current = 0;
    setDragActive(false);
    const files = Array.from(e.dataTransfer.files ?? []);
    if (files.length > 0) addFiles(files);
  };

  useEffect(() => {
    const key = collapseStorageKey(experimentId);
    const raw = localStorage.getItem(key);
    let next = false;
    if (needsIdeaCapture) {
      next = false;
    } else if (raw === "1") {
      next = true;
    } else if (raw === "0") {
      next = false;
    } else {
      next = isNarrowViewport();
    }
    setCollapsed(next);
    onCollapsedChange?.(next);
  }, [experimentId, onCollapsedChange, needsIdeaCapture]);

  useEffect(() => {
    if (needsIdeaCapture) {
      setCollapsed(false);
      onCollapsedChange?.(false);
    }
  }, [needsIdeaCapture, onCollapsedChange]);
  useEffect(() => {
    return () => {
      // Abort SSE only — do NOT cancel the server turn on unmount/reload.
      streamAbortRef.current?.abort();
      greetingAbortRef.current?.abort();
      if (pollTimerRef.current) {
        clearInterval(pollTimerRef.current);
        pollTimerRef.current = null;
      }
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
    if (!needsIdeaCapture) {
      setCaptureGreetingComplete(true);
    }
  }, [needsIdeaCapture]);

  useEffect(() => {
    let cancelled = false;
    setHistoryLoading(true);
    greetingAbortRef.current?.abort();
    greetingAbortRef.current = null;
    const needsCapture = needsIdeaCaptureRef.current;
    if (!needsCapture) {
      setCaptureGreetingComplete(true);
    } else {
      setCaptureGreetingComplete(false);
    }

    const stopPolling = () => {
      if (pollTimerRef.current) {
        clearInterval(pollTimerRef.current);
        pollTimerRef.current = null;
      }
    };

    const applyHistory = (data: {
      messages: ChatHistoryMessage[];
      in_progress_turn_id?: string | null;
    }) => {
      setMessages(data.messages);
      setPendingQuestion(pendingQuestionFromMessages(data.messages));
      forceScrollRef.current = true;

      const runningId = data.in_progress_turn_id ?? null;
      if (runningId) {
        activeTurnIdRef.current = runningId;
        setSending(true);
        setWorkingLabel("Thinking…");
        stopPolling();
        pollTimerRef.current = setInterval(() => {
          void getUniversalChatMessages(experimentId)
            .then((next) => {
              if (cancelled) return;
              setMessages(next.messages);
              setPendingQuestion(pendingQuestionFromMessages(next.messages));
              if (!next.in_progress_turn_id) {
                stopPolling();
                activeTurnIdRef.current = null;
                setSending(false);
                setWorkingLabel(null);
                const last = next.messages[next.messages.length - 1];
                const failed = next.messages.some(
                  (m) => m.metadata?.turn_status === "failed",
                );
                if (failed && last?.role === "user") {
                  setMessages((prev) =>
                    prev.map((m) =>
                      m.id === last.id
                        ? {
                            ...m,
                            error: true,
                            content: `${m.content}\n\n(Failed to send — retry)`,
                          }
                        : m,
                    ),
                  );
                }
              }
            })
            .catch(() => {
              /* keep polling */
            });
        }, 1500);
      } else {
        activeTurnIdRef.current = null;
        setSending(false);
        setWorkingLabel(null);
      }
    };

    void getUniversalChatMessages(experimentId)
      .then(async (data) => {
        if (cancelled) return;
        applyHistory(data);

        const hasAssistant = data.messages.some((m) => m.role === "assistant");
        if (!needsCapture || hasAssistant || data.messages.length > 0) {
          if (needsCapture) setCaptureGreetingComplete(true);
          return;
        }

        // Seed + stream greeting before showing the capture card.
        const abort = new AbortController();
        greetingAbortRef.current = abort;
        setSending(true);
        resetStreamingState();
        setHistoryLoading(false);

        try {
          await streamCaptureGreeting(
            experimentId,
            {
              onAssistantToken: ({ text }) => {
                if (cancelled || abort.signal.aborted) return;
                streamingAssistantTextRef.current += text;
                setStreamingAssistantText(streamingAssistantTextRef.current);
                forceScrollRef.current = true;
              },
              onDone: ({ assistant_message_id }) => {
                if (cancelled || abort.signal.aborted) return;
                const committed = streamingAssistantTextRef.current;
                if (committed) {
                  setMessages([
                    {
                      id: assistant_message_id,
                      role: "assistant",
                      content: committed,
                      turn_kind: "universal_chat",
                      created_at: new Date().toISOString(),
                      tool_payload: null,
                    },
                  ]);
                }
                resetStreamingState();
                setSending(false);
                setCaptureGreetingComplete(true);
              },
              onError: (message) => {
                if (cancelled || abort.signal.aborted) return;
                toast(message, "error");
                resetStreamingState();
                setSending(false);
                // Fail open so the founder can still capture.
                setCaptureGreetingComplete(true);
              },
            },
            abort.signal,
          );
        } catch {
          if (!cancelled && !abort.signal.aborted) {
            toast("Couldn’t load greeting. You can still capture your idea.", "error");
            setSending(false);
            setCaptureGreetingComplete(true);
          }
        } finally {
          if (greetingAbortRef.current === abort) {
            greetingAbortRef.current = null;
          }
        }
      })
      .catch(() => {
        if (cancelled) return;
        setMessages([]);
        setPendingQuestion(null);
        if (needsCapture) {
          setCaptureGreetingComplete(true);
        }
      })
      .finally(() => {
        if (!cancelled) setHistoryLoading(false);
      });
    return () => {
      cancelled = true;
      stopPolling();
      greetingAbortRef.current?.abort();
      greetingAbortRef.current = null;
    };
  }, [experimentId, resetStreamingState, toast]);

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

  const pinScrollToBottom = useCallback(() => {
    const container = scrollContainerRef.current;
    if (!container) return;
    container.scrollTop = container.scrollHeight;
  }, []);

  // Instant stick-to-bottom before paint. Smooth scrollIntoView per token was
  // fighting content growth (and browser scroll-anchoring) → jitter.
  useLayoutEffect(() => {
    if (!(forceScrollRef.current || isNearBottomRef.current)) return;
    pinScrollToBottom();
    forceScrollRef.current = false;
  }, [
    messages,
    sending,
    historyLoading,
    workingLabel,
    streamingAssistantText,
    pinScrollToBottom,
  ]);

  const resizeTextarea = useCallback(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, TEXTAREA_MAX_PX)}px`;
  }, []);

  useLayoutEffect(() => {
    resizeTextarea();
  }, [draft, resizeTextarea]);

  const handleStop = useCallback(() => {
    const partial = streamingAssistantTextRef.current.trim();
    const turnId = activeTurnIdRef.current;
    stoppedRef.current = true;
    streamAbortRef.current?.abort();
    streamAbortRef.current = null;
    if (pollTimerRef.current) {
      clearInterval(pollTimerRef.current);
      pollTimerRef.current = null;
    }
    setWorkingLabel(null);
    heldPendingQuestionRef.current = null;
    setPendingQuestion(null);
    setSending(false);
    activeTurnIdRef.current = null;

    if (turnId) {
      void cancelUniversalChatTurn(experimentId, turnId).catch(() => {
        /* best-effort */
      });
    }

    setMessages((prev) => {
      const next = prev.map((m) =>
        m.optimistic ? { ...m, optimistic: false } : m,
      );
      if (partial) {
        next.push({
          id: `stopped-${crypto.randomUUID()}`,
          role: "assistant",
          content: partial,
          turn_kind: "universal_chat",
          created_at: new Date().toISOString(),
          tool_payload: null,
        });
      }
      return next;
    });
    resetStreamingState();
  }, [experimentId, resetStreamingState]);

  const handleSend = useCallback(
    async (
      overrideText?: string,
      mcqAnswer?: {
        selected_option_indices: number[];
        answered_question_id: string;
        skipped?: boolean;
      } | null,
      sendOptions?: {
        replaceMessageId?: string;
        attachmentIds?: string[];
        attachmentMeta?: Array<{
          id: string;
          filename: string;
          content_kind: string;
        }>;
      },
    ) => {
      const trimmed = (overrideText ?? draft).trim();
      // Card selection/skip: submit indices without echoing a user bubble.
      const isCardAnswer = mcqAnswer != null;
      const attachmentIds = isCardAnswer
        ? []
        : (sendOptions?.attachmentIds ?? readyAttachmentIds);
      const attachmentsForOptimistic = isCardAnswer
        ? []
        : sendOptions?.attachmentMeta
          ? sendOptions.attachmentMeta
          : draftAttachments
              .filter((a) => a.status === "ready" && a.serverId)
              .map((a) => ({
                id: a.serverId!,
                filename: a.filename,
                content_kind: a.contentKind ?? "document",
              }));

      if (sending || attachmentsUploading) return;
      if (!trimmed && attachmentIds.length === 0) return;

      // Dismiss docked card when answering (option / custom / skip / prose).
      const dismissedPending = pendingQuestion;
      if (pendingQuestion) setPendingQuestion(null);
      heldPendingQuestionRef.current = null;
      setEditingMessageId(null);

      streamAbortRef.current?.abort();
      const abort = new AbortController();
      streamAbortRef.current = abort;
      streamingAssistantIdRef.current = null;
      stoppedRef.current = false;
      resetStreamingState();
      setWorkingLabel("Thinking…");
      setPendingSourceRefs([]);

      const displayContent =
        trimmed ||
        (attachmentIds.length > 0 ? "Shared attachments" : "");

      const optimisticId = isCardAnswer
        ? null
        : `local-${crypto.randomUUID()}`;
      if (!isCardAnswer) {
        const optimistic: DockMessage = {
          id: optimisticId!,
          role: "user",
          content: displayContent,
          turn_kind: "universal_chat",
          created_at: new Date().toISOString(),
          optimistic: true,
          metadata:
            attachmentsForOptimistic.length > 0
              ? { attachments: attachmentsForOptimistic }
              : null,
        };
        if (overrideText == null) {
          setDraft("");
        }
        // Keep blob URLs registered by attachment id for sent-message thumbs.
        setDraftAttachments((prev) => {
          for (const row of prev) {
            if (row.serverId && attachmentPreviewById.has(row.serverId)) {
              continue;
            }
            revokePreview(row.previewUrl);
          }
          return [];
        });
        setAttachError(null);
        setMessages((prev) => {
          let base = prev;
          if (sendOptions?.replaceMessageId) {
            const idx = prev.findIndex(
              (m) => m.id === sendOptions.replaceMessageId,
            );
            if (idx >= 0) base = prev.slice(0, idx);
          }
          return [...base, optimistic];
        });
      }

      setSending(true);
      forceScrollRef.current = true;

      const markFailed = () => {
        if (optimisticId) {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === optimisticId
                ? {
                    ...m,
                    error: true,
                    content: `${displayContent}\n\n(Failed to send — retry)`,
                  }
                : m,
            ),
          );
        }
        resetStreamingState();
        setWorkingLabel(null);
        if (dismissedPending) setPendingQuestion(dismissedPending);
      };

      try {
        await streamUniversalChatMessage(
          experimentId,
          trimmed,
          {
            onTurnStarted: ({ turn_id, user_message_id }) => {
              activeTurnIdRef.current = turn_id;
              if (optimisticId && user_message_id) {
                setMessages((prev) =>
                  prev.map((m) =>
                    m.id === optimisticId
                      ? { ...m, id: user_message_id, optimistic: false }
                      : m,
                  ),
                );
              }
            },
            onToolCall: ({ tool_name, message_id }) => {
              const label = workingLabelForTool(tool_name);
              if (label) setWorkingLabel(label);
              setMessages((prev) => [
                ...prev,
                stubToolCallMessage(tool_name, message_id),
              ]);
              forceScrollRef.current = true;
            },
            onToolResult: ({ tool_name, message_id, payload }) => {
              // Never clear the working label here — keep it until the first
              // assistant token so there's no blank gap after tools finish.
              const toolPayload =
                typeof payload.tool_name === "string"
                  ? payload
                  : { tool_name, ...payload };
              if (tool_name === "get_research_context") {
                const refs = extractSourceRefs(toolPayload);
                setPendingSourceRefs(refs);
              }
              if (tool_name === "ask_refine_agent") {
                const refine = parseRefineSubagentResult(toolPayload);
                if (refine) {
                  heldPendingQuestionRef.current = refineResultAsPendingQuestion(
                    message_id,
                    refine,
                  );
                }
              }
              setMessages((prev) => [
                ...prev,
                toolResultFromEvent(tool_name, message_id, payload),
              ]);
              forceScrollRef.current = true;
              const nav = parseNavigateResult(
                toolPayload,
              );
              if (
                nav &&
                onOpenPhase &&
                !dispatchedNavigateIdsRef.current.has(message_id)
              ) {
                dispatchedNavigateIdsRef.current.add(message_id);
                if (
                  nav.source_ref_id &&
                  /^https?:\/\//i.test(nav.source_ref_id)
                ) {
                  setPendingEvidenceFocus({
                    kind: "url",
                    value: nav.source_ref_id,
                  });
                }
                onOpenPhase(nav.navigate_to);
              }
            },
            onSubagentToken: () => {},
            onAssistantToken: ({ text }) => {
              setWorkingLabel(null);
              streamingAssistantTextRef.current += text;
              setStreamingAssistantText(streamingAssistantTextRef.current);
            },
            onDone: ({ assistant_message_id, user_message_id }) => {
              if (stoppedRef.current) return;
              activeTurnIdRef.current = null;
              if (
                assistant_message_id &&
                streamingAssistantIdRef.current === assistant_message_id
              ) {
                return;
              }
              if (assistant_message_id) {
                streamingAssistantIdRef.current = assistant_message_id;
              }
              setWorkingLabel(null);

              const committedAssistantText = streamingAssistantTextRef.current;
              setStreamingAssistantText(committedAssistantText);

              setMessages((prev) => [
                ...prev.map((m) => {
                  if (optimisticId && m.id === optimisticId) {
                    return {
                      ...m,
                      id: user_message_id ?? m.id,
                      optimistic: false,
                    };
                  }
                  return m;
                }),
                ...(committedAssistantText && assistant_message_id
                  ? [
                      {
                        id: assistant_message_id,
                        role: "assistant" as const,
                        content: committedAssistantText,
                        turn_kind: "universal_chat" as const,
                        created_at: new Date().toISOString(),
                        tool_payload: null,
                      },
                    ]
                  : []),
              ]);

              const held = heldPendingQuestionRef.current;
              heldPendingQuestionRef.current = null;
              if (held) setPendingQuestion(held);

              requestAnimationFrame(() => {
                streamingAssistantTextRef.current = "";
                setStreamingAssistantText("");
              });
            },
            onError: () => {
              if (abort.signal.aborted || stoppedRef.current) return;
              setWorkingLabel(null);
              heldPendingQuestionRef.current = null;
              resetStreamingState();
              setMessages((prev) => {
                const cleaned = prev;
                const hasPersistedTools = cleaned.some(
                  (m) => m.role === "tool_call" || m.role === "tool_result",
                );
                if (hasPersistedTools || !optimisticId) {
                  return cleaned.map((m) =>
                    optimisticId && m.id === optimisticId
                      ? { ...m, optimistic: false }
                      : m,
                  );
                }
                return cleaned.map((m) =>
                  m.id === optimisticId
                    ? {
                        ...m,
                        error: true,
                        content: `${displayContent}\n\n(Failed to send — retry)`,
                      }
                    : m,
                );
              });
              if (dismissedPending) setPendingQuestion(dismissedPending);
            },
          },
          abort.signal,
          {
            current_open_phase: currentOpenPhase ?? null,
            attachment_ids: attachmentIds,
            replace_message_id: sendOptions?.replaceMessageId ?? null,
            mcq_answer: mcqAnswer ?? null,
          },
        );
      } catch {
        if (!abort.signal.aborted && !stoppedRef.current) markFailed();
      } finally {
        if (streamAbortRef.current === abort) {
          streamAbortRef.current = null;
        }
        setSending(false);
      }
    },
    [
      draft,
      draftAttachments,
      readyAttachmentIds,
      attachmentsUploading,
      experimentId,
      sending,
      currentOpenPhase,
      onOpenPhase,
      resetStreamingState,
      pendingQuestion,
    ],
  );

  const handleMcqAnswer = useCallback(
    (answer: { indices: number[]; labels: string[] }) => {
      if (!pendingQuestion) return;
      const display = formatMcqAnswerDisplay(answer.labels);
      void handleSend(display, {
        selected_option_indices: answer.indices,
        answered_question_id: pendingQuestion.answeredQuestionId,
      });
    },
    [handleSend, pendingQuestion],
  );

  const handleMcqSkip = useCallback(() => {
    if (!pendingQuestion) return;
    void handleSend("Skipped", {
      selected_option_indices: [],
      answered_question_id: pendingQuestion.answeredQuestionId,
      skipped: true,
    });
  }, [handleSend, pendingQuestion]);

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

  const draftChips = (
    <>
      {draftAttachments.length > 0 || attachError ? (
        <div className="mb-2 space-y-1.5">
          {draftAttachments.length > 0 ? (
            <ul className="flex flex-wrap gap-1.5">
              {draftAttachments.map((item) => (
                <li
                  key={item.localId}
                  className={`group relative flex h-12 max-w-full items-center gap-1.5 rounded-md border border-border-master bg-[var(--fv-surface-2)] px-1.5 ${
                    item.status === "uploading" ? "opacity-70" : ""
                  } ${item.status === "error" ? "border-status-critical" : ""}`}
                  title={
                    item.status === "error"
                      ? item.errorMessage || "Upload failed"
                      : item.filename
                  }
                >
                  <DraftThumb
                    previewUrl={item.previewUrl}
                    filename={item.filename}
                  />
                  <div className="min-w-0 max-w-[7.5rem]">
                    <p className="truncate font-mono text-[10px] uppercase leading-tight text-[var(--fv-text)]">
                      {item.filename}
                    </p>
                    <p className="font-mono text-[10px] text-[var(--fv-text-muted)]">
                      {item.status === "uploading"
                        ? "Uploading…"
                        : item.status === "error"
                          ? "Failed"
                          : formatFileSize(item.file.size)}
                    </p>
                  </div>
                  {item.status === "uploading" ? (
                    <Loader2
                      className="h-3.5 w-3.5 shrink-0 animate-spin text-accent"
                      aria-hidden
                    />
                  ) : item.status === "error" ? (
                    <button
                      type="button"
                      onClick={() => retryDraftAttachment(item.localId)}
                      className="shrink-0 px-1 font-mono text-[10px] uppercase text-accent hover:underline"
                    >
                      Retry
                    </button>
                  ) : null}
                  <button
                    type="button"
                    onClick={() => removeDraftAttachment(item.localId)}
                    aria-label={`Remove ${item.filename}`}
                    disabled={sending}
                    className="flex h-6 w-6 shrink-0 items-center justify-center rounded-sm text-[var(--fv-text-muted)] hover:bg-accent-muted hover:text-[var(--fv-text)] disabled:opacity-40"
                  >
                    <X className="h-3.5 w-3.5" aria-hidden />
                  </button>
                </li>
              ))}
            </ul>
          ) : null}
          {attachError ? (
            <p
              role="alert"
              className="font-mono text-[10px] uppercase text-status-critical"
            >
              {attachError}
            </p>
          ) : null}
        </div>
      ) : null}
      <input
        ref={fileInputRef}
        type="file"
        accept={FILE_ACCEPT}
        multiple
        className="hidden"
        onChange={(e) => {
          const selected = Array.from(e.target.files ?? []);
          e.target.value = "";
          if (selected.length > 0) addFiles(selected);
        }}
      />
    </>
  );

  const attachButton = (
    <button
      type="button"
      onClick={() => fileInputRef.current?.click()}
      disabled={
        sending || draftAttachments.length >= MAX_DRAFT_ATTACHMENTS
      }
      title="Attach file"
      aria-label="Attach file"
      className="flex h-10 w-10 shrink-0 items-center justify-center rounded-md text-[var(--fv-text-muted)] transition-colors hover:bg-accent-muted hover:text-accent disabled:cursor-not-allowed disabled:opacity-40"
    >
      <Plus className="h-4 w-4" aria-hidden />
    </button>
  );

  if (collapsed) {
    return (
      <aside className="fixed right-6 top-6 z-[80] w-10 rounded-md border-2 border-border-master bg-[var(--fv-surface-card)] shadow-brutal-md">
        <button
          type="button"
          onClick={() => setCollapsedPersisted(false)}
          className="flex h-full min-h-[140px] w-full flex-col items-center justify-center gap-2 py-4 text-[var(--fv-text)]"
          aria-label="Open universal chat"
        >
          <MessageSquare className="h-4 w-4 text-accent" aria-hidden />
          <span className="font-label-md text-label-sm uppercase tracking-widest [writing-mode:vertical-rl]">
            CHAT
          </span>
        </button>
      </aside>
    );
  }

  return (
    <aside
      className={`fixed bottom-6 right-6 top-6 z-[80] flex w-[480px] flex-col overflow-hidden rounded-md border-2 bg-[var(--fv-surface-card)] shadow-brutal-md ${
        dragActive
          ? "border-accent"
          : "border-border-master"
      }`}
      onDragEnter={onDragEnter}
      onDragLeave={onDragLeave}
      onDragOver={onDragOver}
      onDrop={onDrop}
    >
      {dragActive ? (
        <div
          className="pointer-events-none absolute inset-0 z-20 flex items-center justify-center bg-[color-mix(in_srgb,var(--fv-accent)_12%,transparent)]"
          aria-hidden
        >
          <div className="rounded-md border-2 border-dashed border-accent bg-[var(--fv-surface-card)] px-4 py-3 font-mono text-mono-sm uppercase tracking-wide text-accent shadow-brutal-sm">
            Drop files to attach
          </div>
        </div>
      ) : null}
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
        className="min-h-0 flex-1 space-y-5 overflow-y-auto px-4 py-4 [overflow-anchor:none]"
      >
        {historyLoading ? (
          <div className="flex h-full items-center justify-center">
            <p className="text-sm text-[var(--fv-text-muted)]">Loading…</p>
          </div>
        ) : messages.length === 0 &&
          !sending &&
          !pendingQuestion &&
          !streamingAssistantText ? (
          <div className="flex h-full items-center justify-center px-4">
            <p className="text-center text-sm text-[var(--fv-text-muted)]">
              {emptyCopy}
            </p>
          </div>
        ) : (
          <>
            {(() => {
              let turnSourceRefs: ResearchSubagentSourceRef[] = [];
              const lastMsg = messages[messages.length - 1];
              const streamingSupersededByCommit =
                Boolean(streamingAssistantText) &&
                lastMsg?.role === "assistant" &&
                lastMsg.content === streamingAssistantText;
              return (
                <>
            {messages.map((msg) => {
              if (msg.role === "user") turnSourceRefs = [];
              if (
                msg.role === "tool_result" &&
                toolNameFromPayload(msg.tool_payload) === "get_research_context"
              ) {
                turnSourceRefs = extractSourceRefs(msg.tool_payload ?? {});
              }
              const sourceRefs =
                msg.role === "assistant" ? turnSourceRefs : undefined;
              return (
                <MessageRow
                  key={msg.id}
                  message={msg}
                  onOpenPhase={onOpenPhase}
                  sourceRefs={sourceRefs}
                  editing={editingMessageId === msg.id}
                  editDraft={editingMessageId === msg.id ? editDraft : ""}
                  onStartEdit={
                    sending || msg.error
                      ? undefined
                      : () => {
                          const text =
                            msg.content === "Shared attachments"
                              ? ""
                              : msg.content;
                          setEditingMessageId(msg.id);
                          setEditDraft(text);
                        }
                  }
                  onEditDraftChange={setEditDraft}
                  onCancelEdit={() => setEditingMessageId(null)}
                  onSaveEdit={() => {
                    if (!editingMessageId) return;
                    const meta = msg.metadata?.attachments ?? [];
                    void handleSend(editDraft, null, {
                      replaceMessageId: msg.id,
                      attachmentIds: meta.map((a) => a.id),
                      attachmentMeta: meta.map((a) => ({
                        id: a.id,
                        filename: a.filename,
                        content_kind: a.content_kind,
                      })),
                    });
                  }}
                  onRetry={
                    msg.error ? () => void handleRetry(msg) : undefined
                  }
                />
              );
            })}
            {streamingAssistantText && !streamingSupersededByCommit ? (
              <ResearchTextWithCitationChips
                text={streamingAssistantText}
                sourceRefs={pendingSourceRefs}
                onSourceCitationClick={
                  onOpenPhase
                    ? (ref) =>
                        openReportCitationInEvidence(
                          onOpenPhase,
                          focusAnchorForSourceRef(ref),
                          ref,
                        )
                    : undefined
                }
                onReportRefClick={
                  onOpenPhase
                    ? (anchor) =>
                        openReportCitationInEvidence(onOpenPhase, anchor)
                    : undefined
                }
              />
            ) : null}
            {workingLabel ? (
              <p className="text-sm italic text-ink-tertiary">{workingLabel}</p>
            ) : null}
            {sending &&
            !workingLabel &&
            !streamingAssistantText &&
            (messages.length === 0 ||
              messages[messages.length - 1]?.role === "user" ||
              messages[messages.length - 1]?.role === "tool_call") ? (
              <TypingIndicator />
            ) : null}
                </>
              );
            })()}
          </>
        )}
        <div ref={scrollAnchorRef} />
      </div>

      {needsIdeaCapture ? (
        captureGreetingComplete ? (
          <div className="shrink-0 px-4 pb-3 pt-2">
            <div className="overflow-hidden rounded-md border border-border-master">
              <IdeaCaptureCard
                disabled={capturing || sending}
                submitting={capturing}
                onCapture={handleIdeaCapture}
              />
            </div>
          </div>
        ) : null
      ) : pendingQuestion ? (
        <div className="shrink-0 px-4 pb-3 pt-2">
          <div className="overflow-hidden rounded-t-md">
            <QuestionCard
              question={pendingQuestion.question}
              options={pendingQuestion.options}
              answeredQuestionId={pendingQuestion.answeredQuestionId}
              selectionMode={pendingQuestion.selectionMode}
              disabled={sending}
              onAnswer={sending ? undefined : handleMcqAnswer}
              onSkip={sending ? undefined : handleMcqSkip}
            />
            <div className="rounded-b-md border border-t-0 border-border-master bg-[var(--fv-surface-muted)] px-2.5 py-2">
              {draftChips}
              <div className="flex items-end gap-2">
                {attachButton}
                <textarea
                  ref={textareaRef}
                  value={draft}
                  onChange={(e) => setDraft(e.target.value)}
                  onKeyDown={handleKeyDown}
                  disabled={sending}
                  rows={1}
                  placeholder={placeholder}
                  aria-label={placeholder}
                  className="min-h-[40px] min-w-0 flex-1 resize-none rounded-md border border-[var(--fv-border)] bg-[var(--fv-surface-2)] px-3 py-2 text-sm text-[var(--fv-text)] placeholder:text-[var(--fv-text-muted)] focus:border-accent focus:outline-none disabled:opacity-60"
                  style={{ maxHeight: TEXTAREA_MAX_PX }}
                />
                <button
                  type="button"
                  onClick={() =>
                    sending ? handleStop() : void handleSend()
                  }
                  disabled={sending ? false : !canSend}
                  aria-label={sending ? "Stop generating" : "Send message"}
                  title={sending ? "Stop" : "Send"}
                  className="flex h-10 w-10 shrink-0 items-center justify-center rounded-md bg-accent text-accent-fg transition-colors hover:bg-accent-hover disabled:cursor-not-allowed disabled:opacity-40"
                >
                  {sending ? (
                    <Square className="h-3.5 w-3.5 fill-current" aria-hidden />
                  ) : (
                    <ArrowUp className="h-4 w-4" aria-hidden />
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
      ) : (
        <div className="shrink-0 border-t border-[var(--fv-border)] p-3">
          {draftChips}
          <div className="flex items-end gap-2">
            {attachButton}
            <textarea
              ref={textareaRef}
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={sending}
              rows={1}
              placeholder={placeholder}
              aria-label={placeholder}
              className="min-h-[40px] min-w-0 flex-1 resize-none rounded-md border border-[var(--fv-border)] bg-[var(--fv-surface-2)] px-3 py-2 text-sm text-[var(--fv-text)] placeholder:text-[var(--fv-text-muted)] focus:border-accent focus:outline-none disabled:opacity-60"
              style={{ maxHeight: TEXTAREA_MAX_PX }}
            />
            <button
              type="button"
              onClick={() =>
                sending ? handleStop() : void handleSend()
              }
              disabled={sending ? false : !canSend}
              aria-label={sending ? "Stop generating" : "Send message"}
              title={sending ? "Stop" : "Send"}
              className="flex h-10 w-10 shrink-0 items-center justify-center rounded-md bg-accent text-accent-fg transition-colors hover:bg-accent-hover disabled:cursor-not-allowed disabled:opacity-40"
            >
              {sending ? (
                <Square className="h-3.5 w-3.5 fill-current" aria-hidden />
              ) : (
                <ArrowUp className="h-4 w-4" aria-hidden />
              )}
            </button>
          </div>
        </div>
      )}
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
    <div className="flex items-center gap-1.5 py-1">
      {[0, 150, 300].map((delay) => (
        <span
          key={delay}
          className="h-2 w-2 animate-pulse rounded-full bg-accent"
          style={{ animationDelay: `${delay}ms` }}
        />
      ))}
    </div>
  );
}

function MessageRow({
  message,
  onRetry,
  onOpenPhase,
  sourceRefs = [],
  editing = false,
  editDraft = "",
  onStartEdit,
  onEditDraftChange,
  onCancelEdit,
  onSaveEdit,
}: {
  message: DockMessage;
  onRetry?: () => void;
  onOpenPhase?: (
    phase: UniversalOpenPhase,
    options?: { sourceRef?: ResearchSubagentSourceRef | null },
  ) => void;
  sourceRefs?: ResearchSubagentSourceRef[];
  editing?: boolean;
  editDraft?: string;
  onStartEdit?: () => void;
  onEditDraftChange?: (value: string) => void;
  onCancelEdit?: () => void;
  onSaveEdit?: () => void;
}) {
  if (message.role === "user") {
    const attachments = (message.metadata?.attachments ?? []).map((a) => ({
      id: a.id,
      filename: a.filename,
      content_kind: a.content_kind,
      previewUrl: getAttachmentPreview(a.id),
    }));
    const bodyText = message.error
      ? message.content.replace(/\n\n\(Failed to send — retry\)$/, "")
      : message.content;
    const hideSharedLabel =
      bodyText === "Shared attachments" && attachments.length > 0;

    if (editing) {
      return (
        <div className="flex justify-end">
          <div className="flex w-full max-w-[85%] flex-col items-end gap-2">
            <textarea
              value={editDraft}
              onChange={(e) => onEditDraftChange?.(e.target.value)}
              rows={3}
              className="w-full resize-y rounded-md border-2 border-accent bg-[var(--fv-surface-2)] p-3 font-body text-body-sm text-[var(--fv-text)] focus:outline-none"
              aria-label="Edit message"
              autoFocus
            />
            {attachments.length > 0 ? (
              <MessageAttachments attachments={attachments} />
            ) : null}
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={onCancelEdit}
                className="rounded-md px-2 py-1 font-mono text-[10px] uppercase text-[var(--fv-text-muted)] hover:text-[var(--fv-text)]"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={onSaveEdit}
                disabled={!editDraft.trim() && attachments.length === 0}
                className="rounded-md bg-accent px-3 py-1 font-mono text-[10px] uppercase text-accent-fg disabled:opacity-40"
              >
                Save
              </button>
            </div>
          </div>
        </div>
      );
    }

    return (
      <div className="group flex justify-end">
        <div className="flex max-w-[85%] flex-col items-end gap-1">
          <div
            className={`rounded-md border-2 border-border-master bg-accent-muted p-3 shadow-brutal-sm ${
              message.error ? "opacity-80" : ""
            } ${message.optimistic && !message.error ? "opacity-90" : ""}`}
          >
            {!hideSharedLabel && bodyText ? (
              <p className="whitespace-pre-wrap font-body text-body-sm text-[var(--fv-text)]">
                {bodyText}
              </p>
            ) : null}
            {attachments.length > 0 ? (
              <MessageAttachments attachments={attachments} />
            ) : null}
          </div>
          <div className="flex items-center gap-2">
            {onStartEdit && !message.optimistic ? (
              <button
                type="button"
                onClick={onStartEdit}
                aria-label="Edit message"
                title="Edit"
                className="opacity-0 transition-opacity group-hover:opacity-100 focus-visible:opacity-100"
              >
                <Pencil className="h-3.5 w-3.5 text-[var(--fv-text-muted)] hover:text-[var(--fv-text)]" />
              </button>
            ) : null}
            {message.error && onRetry ? (
              <button
                type="button"
                onClick={onRetry}
                className="text-xs text-accent hover:underline"
              >
                Failed to send — retry
              </button>
            ) : null}
          </div>
        </div>
      </div>
    );
  }

  if (message.role === "assistant") {
    return (
      <ResearchTextWithCitationChips
        text={message.content}
        sourceRefs={sourceRefs}
        onSourceCitationClick={
          onOpenPhase
            ? (ref) =>
                openReportCitationInEvidence(
                  onOpenPhase,
                  focusAnchorForSourceRef(ref),
                  ref,
                )
            : undefined
        }
        onReportRefClick={
          onOpenPhase
            ? (anchor) => openReportCitationInEvidence(onOpenPhase, anchor)
            : undefined
        }
      />
    );
  }

  if (message.role === "tool_result") {
    const refine = parseRefineSubagentResult(message.tool_payload);
    if (refine) {
      // Question cards dock above the input — never plant them in history.
      if (
        (refine.has_pending_mcq || refine.mcq_question != null) &&
        refine.mcq_options.length > 0 &&
        refine.mcq_answered_question_id != null
      ) {
        return null;
      }
      const prose = refine.assistant_text.trim();
      return prose ? (
        <ChatMarkdown
          content={prose}
          className="fv-msg-ai break-words text-sm text-[var(--fv-text)]"
        />
      ) : null;
    }

    const refineError = parseRefineSubagentError(message.tool_payload);
    if (refineError) {
      return (
        <p className="text-sm text-[var(--fv-text-muted)]">{refineError}</p>
      );
    }

    // Read tools render nothing — the master's assistant row is the answer.
    return null;
  }

  if (message.role === "tool_call") {
    return null;
  }

  return null;
}
