"use client";

import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type ChangeEvent,
  type KeyboardEvent,
} from "react";

export type AttachmentDraft = {
  id: string;
  file: File;
  previewUrl: string | null;
};

type Props = {
  onSend: (text: string, attachments: AttachmentDraft[]) => void | Promise<void>;
  sending: boolean;
  disabled?: boolean;
};

const MAX_ATTACHMENTS = 5;
const ACCEPTED =
  "image/png,image/jpeg,image/webp,application/pdf";

function revokePreview(url: string | null) {
  if (url) URL.revokeObjectURL(url);
}

export function RefineChatInput({
  onSend,
  sending,
  disabled = false,
}: Props) {
  const [text, setText] = useState("");
  const [attachments, setAttachments] = useState<AttachmentDraft[]>([]);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const isBusy = sending || disabled;

  const canSend =
    !isBusy && (text.trim().length > 0 || attachments.length > 0);

  const resizeTextarea = useCallback(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 240)}px`;
  }, []);

  useEffect(() => {
    resizeTextarea();
  }, [text, resizeTextarea]);

  useEffect(() => {
    return () => {
      attachments.forEach((item) => revokePreview(item.previewUrl));
    };
    // Only on unmount
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const addFiles = useCallback((files: File[]) => {
    setUploadError(null);
    setAttachments((prev) => {
      const remaining = MAX_ATTACHMENTS - prev.length;
      if (remaining <= 0) {
        setUploadError(
          `You can attach up to ${MAX_ATTACHMENTS} files per message.`,
        );
        return prev;
      }
      if (files.length > remaining) {
        setUploadError(`Only ${remaining} more file(s) can be attached.`);
      }
      const batch = files.slice(0, remaining);
      return [
        ...prev,
        ...batch.map((file) => ({
          id: crypto.randomUUID(),
          file,
          previewUrl: file.type.startsWith("image/")
            ? URL.createObjectURL(file)
            : null,
        })),
      ];
    });
  }, []);

  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;

    const handlePaste = (e: ClipboardEvent) => {
      const items = e.clipboardData?.items;
      if (!items) return;
      const imageFiles: File[] = [];
      for (const item of Array.from(items)) {
        if (!item.type.startsWith("image/")) continue;
        const file = item.getAsFile();
        if (file) imageFiles.push(file);
      }
      if (imageFiles.length === 0) return;
      e.preventDefault();
      addFiles(imageFiles);
    };

    el.addEventListener("paste", handlePaste);
    return () => el.removeEventListener("paste", handlePaste);
  }, [addFiles]);

  const removeAttachment = (id: string) => {
    setAttachments((prev) => {
      const target = prev.find((item) => item.id === id);
      revokePreview(target?.previewUrl ?? null);
      return prev.filter((item) => item.id !== id);
    });
  };

  const handleFileSelected = (event: ChangeEvent<HTMLInputElement>) => {
    const selected = Array.from(event.target.files ?? []);
    event.target.value = "";
    if (selected.length > 0) addFiles(selected);
  };

  const handleSend = async () => {
    if (!canSend) return;
    const payloadText = text;
    const payloadAttachments = attachments;
    setText("");
    setAttachments([]);
    setUploadError(null);
    if (textareaRef.current) {
      textareaRef.current.style.height = "64px";
    }
    await onSend(payloadText, payloadAttachments);
  };

  const onKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && (event.metaKey || event.ctrlKey)) {
      event.preventDefault();
      void handleSend();
    }
  };

  return (
    <div className="border-2 border-border-master bg-surface-card shadow-brutal-md nodrag">
      {attachments.length > 0 || uploadError ? (
        <div className="px-3 pt-3 space-y-2">
          {attachments.length > 0 ? (
            <ul className="flex flex-wrap gap-2">
              {attachments.map((item) => (
                <li
                  key={item.id}
                  className="border-2 border-border-master bg-surface-elevated h-14 flex items-center gap-2 px-2 max-w-full"
                >
                  {item.previewUrl ? (
                    <div className="w-12 h-12 border-2 border-border-master overflow-hidden shrink-0">
                      {/* eslint-disable-next-line @next/next/no-img-element */}
                      <img
                        src={item.previewUrl}
                        alt={item.file.name}
                        className="w-full h-full object-cover"
                      />
                    </div>
                  ) : (
                    <div className="w-12 h-12 border-2 border-border-master flex items-center justify-center shrink-0">
                      <span
                        className="material-symbols-outlined text-ink-secondary"
                        style={{ fontSize: 20 }}
                        aria-hidden="true"
                      >
                        description
                      </span>
                    </div>
                  )}
                  <span className="font-mono text-mono-sm truncate max-w-[120px]">
                    {item.file.name}
                  </span>
                  <button
                    type="button"
                    onClick={() => removeAttachment(item.id)}
                    aria-label={`Remove ${item.file.name}`}
                    className="p-1 hover:bg-brand-primary-soft shrink-0"
                    disabled={isBusy}
                  >
                    <span
                      className="material-symbols-outlined"
                      style={{ fontSize: 16 }}
                    >
                      close
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          ) : null}
          {uploadError ? (
            <p className="font-mono text-mono-sm text-red-600 uppercase">
              {uploadError}
            </p>
          ) : null}
        </div>
      ) : null}

      <textarea
        ref={textareaRef}
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={onKeyDown}
        disabled={isBusy}
        placeholder="Continue the conversation..."
        rows={2}
        className="nodrag w-full p-3 font-body text-body-md placeholder:text-ink-tertiary bg-transparent border-none focus:outline-none resize-none min-h-[64px] max-h-[240px] cursor-text"
      />

      <div className="flex items-center justify-between gap-3 border-t-2 border-border-master px-3 py-2">
        <div className="flex items-center gap-1">
          <input
            ref={fileInputRef}
            type="file"
            accept={ACCEPTED}
            onChange={handleFileSelected}
            className="hidden"
            multiple
          />
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            className="p-2 hover:bg-brand-primary-soft disabled:opacity-50"
            aria-label="Attach file"
            disabled={isBusy || attachments.length >= MAX_ATTACHMENTS}
          >
            <span
              className="material-symbols-outlined text-ink-secondary"
              style={{ fontSize: 20 }}
            >
              attach_file
            </span>
          </button>
        </div>

        <div className="flex items-center gap-3">
          <span className="hidden sm:inline font-mono text-mono-sm uppercase text-ink-tertiary">
            Cmd+Enter
          </span>
          <button
            type="button"
            onClick={() => void handleSend()}
            disabled={!canSend}
            className="bg-brand-primary text-ink-inverse px-6 py-2 border-2 border-border-master font-label-md text-label-md uppercase tracking-wider shadow-brutal-sm hover:shadow-brutal-md hover:-translate-x-0.5 hover:-translate-y-0.5 active:translate-x-0 active:translate-y-0 active:shadow-none disabled:opacity-50 disabled:cursor-not-allowed transition-all"
          >
            {sending ? "SENDING..." : "SEND"}
          </button>
        </div>
      </div>
    </div>
  );
}
