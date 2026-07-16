"use client";

import { useEffect, useRef, useState } from "react";
import { Pencil } from "lucide-react";
import type { ChatRole } from "@/lib/types";
import { useAuth } from "@/lib/auth-context";
import { getChatUserLabel } from "@/lib/user-avatar";
import { UserAvatar } from "@/components/auth/UserAvatar";
import { FivvleLogo } from "@/components/layout/FivvleLogo";
import { ChatMarkdown } from "./ChatMarkdown";

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
  const { user } = useAuth();
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
      <div className="relative mx-auto w-full max-w-full lg:max-w-[680px]">
        {isUser && canEdit && !isEditing && (
          <button
            type="button"
            onClick={() => setIsEditing(true)}
            aria-label="Edit message"
            className="absolute right-0 top-0 rounded-md p-1.5 text-[var(--fv-text-muted)] opacity-0 transition-opacity hover:bg-[var(--fv-hover-overlay)] hover:text-[var(--fv-text-soft)] group-hover:opacity-100"
          >
            <Pencil className="h-3.5 w-3.5" />
          </button>
        )}
        <div className="flex items-start gap-3">
          {isUser ? (
            <UserAvatar
              displayName={user?.displayName}
              email={user?.email}
              photoUrl={user?.photoURL}
              size="sm"
              className="!h-6 !w-6 !text-[11px]"
            />
          ) : (
            <FivvleLogo size={24} />
          )}
          <div className="min-w-0 flex-1">
            <span className="mb-1 block text-[13px] font-medium text-[var(--fv-text-soft)]">
              {isUser ? getChatUserLabel(user) : "Fivvle"}
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
            ) : isUser ? (
              <div className="fv-msg-user whitespace-pre-wrap break-words">
                {content}
              </div>
            ) : (
              <ChatMarkdown content={content} className="fv-msg-ai break-words" />
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
