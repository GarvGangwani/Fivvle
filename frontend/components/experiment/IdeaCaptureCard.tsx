"use client";

import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type DragEvent,
  type KeyboardEvent,
} from "react";
import { File, FileText, Loader2, Paperclip, X } from "lucide-react";
import { useToast } from "@/components/ui/ToastProvider";
import { uploadChatAttachments } from "@/lib/api";
import {
  FILE_ACCEPT,
  MAX_DRAFT_ATTACHMENT_BYTES,
  MAX_DRAFT_ATTACHMENTS,
  fileExtension,
  formatFileSize,
  isAcceptedAttachmentFile,
  isImageAttachmentFile,
  revokePreview,
  type DraftAttachment,
} from "@/lib/chat-draft-attachments";
import { downscaleImageForUpload } from "@/lib/downscale-image";

const DEFAULT_PROMPT =
  "Let's capture your idea. Tell me what you're building — and add any files you have (logo, research, sketches).";

type Props = {
  prompt?: string;
  disabled?: boolean;
  submitting?: boolean;
  onCapture: (payload: {
    ideaText: string;
    attachmentIds: string[];
  }) => void | Promise<void>;
};

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

function uploadErrorMessage(err: unknown): string {
  if (err instanceof Error && err.message && !err.message.startsWith("API ")) {
    return err.message;
  }
  if (err && typeof err === "object" && "body" in err) {
    const body = (err as { body: unknown }).body;
    if (typeof body === "string" && body.trim()) return body;
    if (
      body &&
      typeof body === "object" &&
      "detail" in body &&
      typeof (body as { detail: unknown }).detail === "string"
    ) {
      return (body as { detail: string }).detail;
    }
  }
  return "Upload failed. Try again.";
}

export function IdeaCaptureCard({
  prompt = DEFAULT_PROMPT,
  disabled = false,
  submitting = false,
  onCapture,
}: Props) {
  const { toast } = useToast();
  const [ideaText, setIdeaText] = useState("");
  const [draftAttachments, setDraftAttachments] = useState<DraftAttachment[]>(
    [],
  );
  const [attachError, setAttachError] = useState<string | null>(null);
  const [dragActive, setDragActive] = useState(false);

  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const dragDepthRef = useRef(0);
  const draftAttachmentsRef = useRef(draftAttachments);
  draftAttachmentsRef.current = draftAttachments;

  const locked = disabled || submitting;
  const readyAttachmentIds = draftAttachments
    .filter((a) => a.status === "ready" && a.serverId)
    .map((a) => a.serverId!);
  const attachmentsUploading = draftAttachments.some(
    (a) => a.status === "uploading",
  );
  const canCapture =
    !locked &&
    !attachmentsUploading &&
    ideaText.trim().length > 0;

  const uploadOneDraft = useCallback(
    async (localId: string, file: File) => {
      try {
        const toUpload = isImageAttachmentFile(file)
          ? await downscaleImageForUpload(file)
          : file;
        const uploaded = await uploadChatAttachments([toUpload]);
        const item = uploaded[0];
        if (!item) throw new Error("Upload returned no attachment.");
        setDraftAttachments((prev) =>
          prev.map((row) =>
            row.localId !== localId
              ? row
              : {
                  ...row,
                  status: "ready" as const,
                  serverId: item.id,
                  contentKind: item.content_kind,
                  errorMessage: undefined,
                },
          ),
        );
      } catch (err) {
        const message = uploadErrorMessage(err);
        setDraftAttachments((prev) =>
          prev.map((row) =>
            row.localId === localId
              ? { ...row, status: "error", errorMessage: message }
              : row,
          ),
        );
        toast(message, "error");
      }
    },
    [toast],
  );

  const addFiles = useCallback(
    (files: File[]) => {
      if (locked || files.length === 0) return;
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
            `You can attach up to ${MAX_DRAFT_ATTACHMENTS} files.`,
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
    [locked, uploadOneDraft],
  );

  const removeDraftAttachment = useCallback((localId: string) => {
    setDraftAttachments((prev) => {
      const target = prev.find((row) => row.localId === localId);
      revokePreview(target?.previewUrl ?? null);
      return prev.filter((row) => row.localId !== localId);
    });
    setAttachError(null);
  }, []);

  const retryDraftAttachment = useCallback(
    (localId: string) => {
      const target = draftAttachments.find((row) => row.localId === localId);
      if (!target || locked) return;
      setDraftAttachments((prev) =>
        prev.map((row) =>
          row.localId === localId
            ? { ...row, status: "uploading", errorMessage: undefined }
            : row,
        ),
      );
      void uploadOneDraft(localId, target.file);
    },
    [draftAttachments, locked, uploadOneDraft],
  );

  useEffect(() => {
    return () => {
      for (const row of draftAttachmentsRef.current) {
        revokePreview(row.previewUrl);
      }
    };
  }, []);

  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    const handlePaste = (e: ClipboardEvent) => {
      if (locked) return;
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
  }, [addFiles, locked]);

  const onDragEnter = (e: DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (locked) return;
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
    if (locked) return;
    if (e.dataTransfer.types.includes("Files")) {
      e.dataTransfer.dropEffect = "copy";
    }
  };
  const onDrop = (e: DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    dragDepthRef.current = 0;
    setDragActive(false);
    if (locked) return;
    const files = Array.from(e.dataTransfer.files ?? []);
    if (files.length > 0) addFiles(files);
  };

  const handleCapture = () => {
    if (!canCapture) return;
    void onCapture({
      ideaText: ideaText.trim(),
      attachmentIds: readyAttachmentIds,
    });
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && (event.metaKey || event.ctrlKey)) {
      event.preventDefault();
      handleCapture();
    }
  };

  return (
    <section
      aria-label="Capture your idea"
      className={`relative flex max-h-[min(50vh,24rem)] w-full flex-col rounded-t-md rounded-b-none border border-b-0 border-border-master bg-[var(--fv-surface-muted)] px-2.5 pb-2 pt-2 ${
        dragActive ? "border-accent" : ""
      }`}
      onDragEnter={onDragEnter}
      onDragLeave={onDragLeave}
      onDragOver={onDragOver}
      onDrop={onDrop}
    >
      {dragActive ? (
        <div
          className="pointer-events-none absolute inset-0 z-10 flex items-center justify-center rounded-t-md bg-[color-mix(in_srgb,var(--fv-accent)_12%,transparent)]"
          aria-hidden
        >
          <div className="rounded-md border border-dashed border-accent bg-[var(--fv-surface-card)] px-3 py-2 font-mono text-[10px] uppercase tracking-wide text-accent">
            Drop files to attach
          </div>
        </div>
      ) : null}

      <div className="shrink-0 space-y-1.5 pb-2">
        <p className="font-mono text-mono-sm uppercase tracking-[0.14em] text-accent">
          Capture
        </p>
        <h3 className="text-[13px] font-medium leading-snug text-ink-primary">
          {prompt}
        </h3>
      </div>

      <div className="min-h-0 flex-1 space-y-2 overflow-y-auto pr-0.5">
        <textarea
          ref={textareaRef}
          value={ideaText}
          onChange={(e) => setIdeaText(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={locked}
          rows={4}
          placeholder="Describe your idea…"
          aria-label="Your idea"
          className="min-h-[4.5rem] w-full resize-none rounded-sm border border-border-master bg-[var(--fv-surface-card)] px-2.5 py-2 text-[13px] leading-snug text-ink-primary placeholder:text-ink-tertiary focus:border-accent focus:outline-none disabled:cursor-not-allowed disabled:opacity-60"
        />

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
                    disabled={locked}
                    className="shrink-0 px-1 font-mono text-[10px] uppercase text-accent hover:underline disabled:opacity-40"
                  >
                    Retry
                  </button>
                ) : null}
                <button
                  type="button"
                  onClick={() => removeDraftAttachment(item.localId)}
                  aria-label={`Remove ${item.filename}`}
                  disabled={locked}
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

      <div className="flex shrink-0 items-center justify-between gap-2 px-0.5 pt-2">
        <button
          type="button"
          onClick={() => fileInputRef.current?.click()}
          disabled={locked || draftAttachments.length >= MAX_DRAFT_ATTACHMENTS}
          title="Attach file"
          aria-label="Attach file"
          className="flex h-7 w-7 shrink-0 items-center justify-center rounded-sm text-ink-tertiary transition-colors hover:bg-accent-muted hover:text-accent disabled:cursor-not-allowed disabled:opacity-40"
        >
          <Paperclip className="h-3.5 w-3.5" aria-hidden />
        </button>
        <button
          type="button"
          disabled={!canCapture}
          onClick={handleCapture}
          className="h-7 shrink-0 rounded-sm border border-border-master bg-accent px-3 font-mono text-[10px] uppercase tracking-wider text-accent-fg transition-colors hover:bg-accent-hover disabled:cursor-not-allowed disabled:opacity-40"
        >
          {submitting ? "Capturing…" : "Capture"}
        </button>
      </div>

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
    </section>
  );
}
