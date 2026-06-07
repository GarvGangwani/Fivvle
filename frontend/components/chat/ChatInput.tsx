"use client";

import { useCallback, useRef, type KeyboardEvent } from "react";
import { Loader2, Send } from "lucide-react";

interface ChatInputProps {
  onSend: (text: string) => void;
  disabled: boolean;
  placeholder: string;
}

const MAX_HEIGHT_PX = 160;

export function ChatInput({ onSend, disabled, placeholder }: ChatInputProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const resizeTextarea = useCallback(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, MAX_HEIGHT_PX)}px`;
  }, []);

  function handleSend() {
    const el = textareaRef.current;
    if (!el) return;
    const text = el.value.trim();
    if (!text || disabled) return;
    onSend(text);
    el.value = "";
    el.style.height = "auto";
  }

  function handleKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  return (
    <div className="flex items-end gap-2 border-t border-[var(--fv-border)] bg-[var(--fv-surface)] px-4 py-3 sm:px-6">
      <textarea
        ref={textareaRef}
        rows={1}
        placeholder={placeholder}
        disabled={disabled}
        onChange={resizeTextarea}
        onKeyDown={handleKeyDown}
        className="fv-input max-h-40 min-h-[44px] flex-1 resize-none px-4 py-2.5 text-sm leading-relaxed placeholder:text-[var(--fv-text-muted)] disabled:cursor-not-allowed disabled:opacity-50"
      />
      <button
        type="button"
        onClick={handleSend}
        disabled={disabled}
        aria-label="Send message"
        className="fv-send-btn shrink-0 disabled:cursor-not-allowed"
      >
        {disabled ? (
          <Loader2 className="h-4 w-4 animate-spin" />
        ) : (
          <Send className="h-4 w-4" />
        )}
      </button>
    </div>
  );
}
