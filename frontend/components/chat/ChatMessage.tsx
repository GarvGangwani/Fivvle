"use client";

import { useEffect, useRef, useState } from "react";
import { Pencil } from "lucide-react";
import type { ChatRole } from "@/lib/types";

interface ChatMessageProps {
  id: string;
  role: ChatRole;
  content: string;
  timestamp?: string;
  showRefining?: boolean;
  canEdit?: boolean;
  onEdit?: (messageId: string, newContent: string) => Promise<void>;
}

export function ChatMessage({
  id,
  role,
  content,
  showRefining = false,
  canEdit = false,
  onEdit,
}: ChatMessageProps) {
  const isUser = role === "user";
  const [isEditing, setIsEditing] = useState(false);
  const [draft, setDraft] = useState(content);
  const [saving, setSaving] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (!isEditing) {
      setDraft(content);
    }
  }, [content, isEditing]);

  useEffect(() => {
    if (isEditing && textareaRef.current) {
      textareaRef.current.focus();
      textareaRef.current.setSelectionRange(
        textareaRef.current.value.length,
        textareaRef.current.value.length,
      );
    }
  }, [isEditing]);

  function handleCancel() {
    setDraft(content);
    setIsEditing(false);
  }

  async function handleSave() {
    const trimmed = draft.trim();
    if (!trimmed || !onEdit || trimmed === content) {
      handleCancel();
      return;
    }
    setSaving(true);
    try {
      await onEdit(id, trimmed);
      setIsEditing(false);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="fv-msg-enter group border-b border-[var(--fv-border)] py-6">
      <div className="relative mx-auto max-w-[680px]">
        {isUser && canEdit && !isEditing && (
          <button
            type="button"
            onClick={() => setIsEditing(true)}
            aria-label="Edit message"
            className="absolute right-0 top-0 rounded-md p-1.5 text-[var(--fv-text-muted)] opacity-0 transition-opacity hover:bg-white/[0.06] hover:text-[var(--fv-text-soft)] group-hover:opacity-100"
          >
            <Pencil className="h-3.5 w-3.5" />
          </button>
        )}
        <div className="flex items-start gap-3">
          {isUser ? (
            <div
              className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-white/[0.08] text-[11px] font-semibold text-[var(--fv-text-soft)]"
              aria-hidden
            >
              Y
            </div>
          ) : (
            <div
              className="fv-f-logo"
              style={{ width: 24, height: 24, fontSize: 12 }}
              aria-hidden
            >
              F
            </div>
          )}
          <div className="min-w-0 flex-1">
            <span className="mb-1 block text-[13px] font-medium text-[var(--fv-text-soft)]">
              {isUser ? "You" : "Fivvle"}
              {!isUser && showRefining && (
                <span className="fv-refining-badge ml-2">Refining</span>
              )}
            </span>
            {isEditing ? (
              <div className="space-y-3">
                <textarea
                  ref={textareaRef}
                  value={draft}
                  onChange={(e) => setDraft(e.target.value)}
                  disabled={saving}
                  rows={3}
                  className="fv-input w-full resize-y px-3 py-2 text-[15px] leading-[1.65] text-[var(--fv-text)]"
                />
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => void handleSave()}
                    disabled={saving || !draft.trim()}
                    className="fv-btn-primary px-4 py-2 text-sm disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    {saving ? "Saving…" : "Save"}
                  </button>
                  <button
                    type="button"
                    onClick={handleCancel}
                    disabled={saving}
                    className="fv-btn-ghost px-4 py-2 text-sm disabled:opacity-50"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            ) : (
              <div
                className={`whitespace-pre-wrap break-words ${isUser ? "fv-msg-user" : "fv-msg-ai"}`}
              >
                {content}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
