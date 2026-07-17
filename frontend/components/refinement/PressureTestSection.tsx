"use client";

import { useEffect, useRef, useState } from "react";
import { Pencil } from "lucide-react";
import type { SourcedClarityQaBlock } from "@/lib/refinement-thread";
import { ClarityAnswerCarousel } from "./ClarityAnswerCarousel";

interface PressureTestSectionProps {
  blocks: SourcedClarityQaBlock[];
  contentKey: string;
  messageContentById: Record<string, string>;
  canEditMessage: (messageId: string) => boolean;
  onEdit: (messageId: string, newContent: string) => Promise<void>;
}

function EditActions({
  saving,
  canSave,
  onSave,
  onCancel,
}: {
  saving: boolean;
  canSave: boolean;
  onSave: () => void;
  onCancel: () => void;
}) {
  return (
    <div className="mt-3 flex items-center gap-2">
      <button
        type="button"
        onClick={onSave}
        disabled={saving || !canSave}
        className="fv-btn-primary px-4 py-2 text-sm disabled:cursor-not-allowed disabled:opacity-50"
      >
        {saving ? "Saving…" : "Save"}
      </button>
      <button
        type="button"
        onClick={onCancel}
        disabled={saving}
        className="fv-btn-ghost px-4 py-2 text-sm disabled:opacity-50"
      >
        Cancel
      </button>
    </div>
  );
}

/** Chapter 2 — all research-engine Q&A in one traversable card. */
export function PressureTestSection({
  blocks,
  contentKey,
  messageContentById,
  canEditMessage,
  onEdit,
}: PressureTestSectionProps) {
  const [index, setIndex] = useState(0);
  const [editingMessageId, setEditingMessageId] = useState<string | null>(null);
  const [draft, setDraft] = useState("");
  const [saving, setSaving] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const currentBlock = blocks[index];
  const editingContent = editingMessageId
    ? messageContentById[editingMessageId]
    : undefined;

  useEffect(() => {
    if (!editingMessageId) return;
    setDraft(editingContent ?? "");
  }, [editingMessageId, editingContent]);

  useEffect(() => {
    if (editingMessageId && textareaRef.current) {
      textareaRef.current.focus();
    }
  }, [editingMessageId]);

  const canEditCurrent =
    currentBlock != null && canEditMessage(currentBlock.messageId);

  const editButton =
    canEditCurrent && !editingMessageId ? (
      <button
        type="button"
        onClick={() => setEditingMessageId(currentBlock.messageId)}
        aria-label="Edit answers"
        className="rounded-md p-1.5 text-[var(--fv-text-muted)] transition-colors hover:bg-[var(--fv-hover-overlay)] hover:text-[var(--fv-text-soft)]"
      >
        <Pencil className="h-3.5 w-3.5" />
      </button>
    ) : null;

  async function handleSave() {
    if (!editingMessageId) return;
    const trimmed = draft.trim();
    const original = messageContentById[editingMessageId] ?? "";
    if (!trimmed || trimmed === original) {
      setEditingMessageId(null);
      return;
    }
    setSaving(true);
    try {
      await onEdit(editingMessageId, trimmed);
      setEditingMessageId(null);
    } finally {
      setSaving(false);
    }
  }

  if (blocks.length === 0) return null;

  return (
    <div className="fv-msg-enter">
      <section className="ra-section">
        <div className="ra-section-head">
          <div>
            <p className="ra-kicker">Chapter 2 · Pressure test</p>
            <h3 className="ra-section-title">You answered the hard questions.</h3>
          </div>
          {editButton}
        </div>

        {editingMessageId ? (
          <>
            <textarea
              ref={textareaRef}
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              disabled={saving}
              rows={8}
              className="fv-input w-full resize-y px-3 py-2 font-mono text-[13px] leading-[1.55]"
            />
            <EditActions
              saving={saving}
              canSave={Boolean(draft.trim())}
              onSave={() => void handleSave()}
              onCancel={() => {
                setDraft(editingContent ?? "");
                setEditingMessageId(null);
              }}
            />
          </>
        ) : (
          <ClarityAnswerCarousel
            blocks={blocks}
            contentKey={contentKey}
            index={index}
            onIndexChange={setIndex}
          />
        )}
      </section>
    </div>
  );
}
