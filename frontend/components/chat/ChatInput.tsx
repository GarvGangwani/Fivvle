"use client";

import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type ChangeEvent,
  type ClipboardEvent,
  type KeyboardEvent,
} from "react";
import { Image as ImageIcon, Loader2, Paperclip, Send, X, Zap } from "lucide-react";
import { uploadChatAttachments, ApiError } from "@/lib/api";
import type { ChatAttachmentUploadItem } from "@/lib/api";

const MAX_ATTACHMENTS = 5;

const ACCEPTED_FILE_TYPES =
  "image/png,image/jpeg,image/webp,.pdf,.txt,.md,.markdown,.docx";

interface PendingAttachment extends ChatAttachmentUploadItem {
  localKey: string;
}

interface ChatInputProps {
  onSend: (
    text: string,
    deepResearch: boolean,
    attachments: Array<{ id: string; filename: string }>,
  ) => void;
  disabled: boolean;
  placeholder: string;
  deepResearchLocked?: boolean;
  prefillText?: string | null;
  prefillNonce?: number;
}

const MIN_TEXTAREA_HEIGHT_PX = 40;
const MAX_TEXTAREA_HEIGHT_PX = 120;

function getMaxTextareaHeightPx(): number {
  if (typeof window === "undefined") return MAX_TEXTAREA_HEIGHT_PX;
  const mobileCap = Math.floor(window.innerHeight * 0.28);
  if (window.matchMedia("(max-width: 1023px)").matches) {
    return Math.min(MAX_TEXTAREA_HEIGHT_PX, mobileCap);
  }
  return MAX_TEXTAREA_HEIGHT_PX;
}

function uploadErrorMessage(err: unknown): string {
  if (err instanceof ApiError) {
    if (typeof err.body === "object" && err.body !== null && "detail" in err.body) {
      const detail = (err.body as { detail?: unknown }).detail;
      if (typeof detail === "string") return detail;
    }
  }
  return "Could not upload file. Try a smaller PNG, JPEG, WebP, PDF, TXT, Markdown, or DOCX.";
}

function extensionForImageMime(mime: string): string {
  if (mime === "image/png") return "png";
  if (mime === "image/webp") return "webp";
  return "jpg";
}

function filesFromClipboardItems(items: DataTransferItemList): File[] {
  const imageFiles: File[] = [];
  for (const item of Array.from(items)) {
    if (!item.type.startsWith("image/")) continue;
    const blob = item.getAsFile();
    if (!blob) continue;
    const ext = extensionForImageMime(item.type);
    imageFiles.push(
      new File([blob], `pasted-image-${Date.now()}-${imageFiles.length}.${ext}`, {
        type: item.type,
      }),
    );
  }
  return imageFiles;
}

export function ChatInput({
  onSend,
  disabled,
  placeholder,
  deepResearchLocked = false,
  prefillText = null,
  prefillNonce = 0,
}: ChatInputProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [deepResearch, setDeepResearch] = useState(true);
  const [attachments, setAttachments] = useState<PendingAttachment[]>([]);
  const [uploadingCount, setUploadingCount] = useState(0);
  const [uploadError, setUploadError] = useState<string | null>(null);

  const resizeTextarea = useCallback(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    const nextHeight = Math.max(
      MIN_TEXTAREA_HEIGHT_PX,
      Math.min(el.scrollHeight, getMaxTextareaHeightPx()),
    );
    el.style.height = `${nextHeight}px`;
  }, []);

  useEffect(() => {
    resizeTextarea();
  }, [resizeTextarea]);

  useEffect(() => {
    const onResize = () => resizeTextarea();
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, [resizeTextarea]);

  useEffect(() => {
    if (!prefillText || prefillNonce === 0) return;
    const el = textareaRef.current;
    if (!el) return;
    el.value = prefillText;
    resizeTextarea();
    el.focus();
  }, [prefillText, prefillNonce, resizeTextarea]);

  const isBusy = disabled || uploadingCount > 0;

  function handleSend() {
    const el = textareaRef.current;
    if (!el || isBusy) return;
    const text = el.value.trim();
    if (!text && attachments.length === 0) return;
    onSend(
      text,
      deepResearchLocked ? false : deepResearch,
      attachments.map((item) => ({ id: item.id, filename: item.filename })),
    );
    el.value = "";
    el.style.height = `${MIN_TEXTAREA_HEIGHT_PX}px`;
    setAttachments([]);
    setUploadError(null);
  }

  function handleKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  async function uploadFiles(selected: File[]) {
    if (selected.length === 0) return;

    const remainingSlots = MAX_ATTACHMENTS - attachments.length;
    if (remainingSlots <= 0) {
      setUploadError(`You can attach up to ${MAX_ATTACHMENTS} files per message.`);
      return;
    }

    const batch = selected.slice(0, remainingSlots);
    if (selected.length > remainingSlots) {
      setUploadError(`Only ${remainingSlots} more file(s) can be attached.`);
    } else {
      setUploadError(null);
    }

    setUploadingCount((count) => count + batch.length);
    try {
      const uploaded = await uploadChatAttachments(batch);
      setAttachments((prev) => [
        ...prev,
        ...uploaded.map((item, index) => ({
          ...item,
          localKey: `${item.id}-${Date.now()}-${index}`,
        })),
      ]);
    } catch (err) {
      setUploadError(uploadErrorMessage(err));
    } finally {
      setUploadingCount((count) => Math.max(0, count - batch.length));
    }
  }

  async function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    const selected = Array.from(event.target.files ?? []);
    event.target.value = "";
    await uploadFiles(selected);
  }

  function handlePaste(event: ClipboardEvent<HTMLTextAreaElement>) {
    const items = event.clipboardData?.items;
    if (!items) return;

    const imageFiles = filesFromClipboardItems(items);
    if (imageFiles.length === 0) return;

    event.preventDefault();
    void uploadFiles(imageFiles);
  }

  function removeAttachment(localKey: string) {
    setAttachments((prev) => prev.filter((item) => item.localKey !== localKey));
    setUploadError(null);
  }

  return (
    <div className="shrink-0 bg-gradient-to-t from-[var(--fv-bg)] via-[var(--fv-bg)]/95 to-transparent px-4 pb-3 pt-2 backdrop-blur-md lg:px-12">
      <div className="mx-auto max-w-3xl rounded-2xl border border-[var(--fv-border)] bg-[var(--fv-surface)]/90 p-2 shadow-[0_-4px_24px_rgba(0,0,0,0.25)] backdrop-blur-xl">
        {(attachments.length > 0 || uploadError) && (
          <div className="mb-2 space-y-1.5 px-1">
            {attachments.length > 0 && (
              <div className="flex flex-wrap gap-1.5">
                {attachments.map((item) => (
                  <span
                    key={item.localKey}
                    className="inline-flex max-w-full items-center gap-1 rounded-full border border-[var(--fv-border)] bg-[var(--fv-bg)]/70 px-2.5 py-1 text-[12px] text-[var(--fv-text-muted)]"
                    title={item.excerpt}
                  >
                    {item.content_kind === "image" ? (
                      <ImageIcon className="h-3 w-3 shrink-0" />
                    ) : (
                      <Paperclip className="h-3 w-3 shrink-0" />
                    )}
                    <span className="truncate">{item.filename}</span>
                    <button
                      type="button"
                      onClick={() => removeAttachment(item.localKey)}
                      className="fv-icon-btn !h-5 !w-5 shrink-0"
                      aria-label={`Remove ${item.filename}`}
                      disabled={isBusy}
                    >
                      <X className="h-3 w-3" />
                    </button>
                  </span>
                ))}
              </div>
            )}
            {uploadError && (
              <p className="text-[12px] text-red-400">{uploadError}</p>
            )}
          </div>
        )}

        <div className="flex items-end gap-2">
          <input
            ref={fileInputRef}
            type="file"
            className="hidden"
            multiple
            accept={ACCEPTED_FILE_TYPES}
            onChange={handleFileChange}
          />
          <button
            type="button"
            className="fv-icon-btn mb-0.5 shrink-0 disabled:cursor-not-allowed disabled:opacity-40"
            title="Attach images, PDFs, or documents (or paste an image)"
            aria-label="Attach file"
            disabled={isBusy || attachments.length >= MAX_ATTACHMENTS}
            onClick={() => fileInputRef.current?.click()}
          >
            {uploadingCount > 0 ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Paperclip className="h-4 w-4" />
            )}
          </button>

          <textarea
            ref={textareaRef}
            rows={1}
            placeholder={placeholder}
            disabled={isBusy}
            onChange={resizeTextarea}
            onKeyDown={handleKeyDown}
            onPaste={handlePaste}
            className="max-h-[120px] min-h-[40px] flex-1 resize-none border-none bg-transparent px-1 py-2 text-[14px] leading-5 text-[var(--fv-text)] outline-none placeholder:text-[var(--fv-text-muted)] disabled:cursor-not-allowed disabled:opacity-50"
          />

          <button
            type="button"
            onClick={handleSend}
            disabled={isBusy}
            aria-label="Send message"
            className="fv-send-btn mb-0.5 shrink-0 disabled:cursor-not-allowed"
          >
            {disabled ? (
              <Loader2 className="h-[15px] w-[15px] animate-spin" />
            ) : (
              <Send className="h-[15px] w-[15px]" />
            )}
          </button>
        </div>

        {!deepResearchLocked && (
          <div className="mt-1.5 flex items-center px-1">
            <button
              type="button"
              onClick={() => setDeepResearch((v) => !v)}
              disabled={isBusy}
              className={`fv-deep-toggle ${deepResearch ? "fv-deep-toggle-on" : ""}`}
            >
              <Zap className="h-[13px] w-[13px]" />
              Deep Research {deepResearch ? "ON" : "OFF"}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
