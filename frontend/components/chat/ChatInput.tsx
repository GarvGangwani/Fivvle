"use client";

import { useCallback, useRef, useState, type KeyboardEvent } from "react";
import { Loader2, Paperclip, Send, Zap } from "lucide-react";

interface ChatInputProps {
  onSend: (text: string, deepResearch: boolean) => void;
  disabled: boolean;
  placeholder: string;
  deepResearchLocked?: boolean;
}

const MAX_HEIGHT_PX = 120;

export function ChatInput({
  onSend,
  disabled,
  placeholder,
  deepResearchLocked = false,
}: ChatInputProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const [deepResearch, setDeepResearch] = useState(true);

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
    onSend(text, deepResearch);
    el.value = "";
    el.style.height = "auto";
  }

  function handleKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  const effectiveDeepResearch = deepResearchLocked ? true : deepResearch;

  return (
    <div
      className="px-6 py-4 sm:px-12 sm:pb-6"
      style={{ borderTop: "1px solid rgba(255,255,255,0.05)" }}
    >
      <div
        className="mx-auto flex max-w-3xl flex-col gap-2.5 rounded-2xl p-3 sm:p-3.5"
        style={{
          background: "rgba(255,255,255,0.03)",
          border: "1px solid rgba(255,255,255,0.08)",
        }}
      >
        <textarea
          ref={textareaRef}
          rows={1}
          placeholder={placeholder}
          disabled={disabled}
          onChange={resizeTextarea}
          onKeyDown={handleKeyDown}
          className="min-h-[50px] max-h-[120px] w-full resize-none border-none bg-transparent text-[14px] leading-normal text-[var(--fv-text)] outline-none placeholder:text-[var(--fv-text-muted)] disabled:cursor-not-allowed disabled:opacity-50"
          style={{ lineHeight: 1.5 }}
        />

        <div className="flex items-center gap-2">
          <button
            type="button"
            className="fv-icon-btn"
            aria-label="Attach file"
            disabled={disabled}
          >
            <Paperclip className="h-4 w-4" />
          </button>

          <button
            type="button"
            onClick={() => !deepResearchLocked && setDeepResearch((v) => !v)}
            disabled={disabled || deepResearchLocked}
            className={`fv-deep-toggle ${
              effectiveDeepResearch ? "fv-deep-toggle-on" : ""
            }`}
          >
            <Zap className="h-[13px] w-[13px]" />
            Deep Research {effectiveDeepResearch ? "ON" : "OFF"}
          </button>

          <button
            type="button"
            onClick={handleSend}
            disabled={disabled}
            aria-label="Send message"
            className="fv-send-btn ml-auto shrink-0 disabled:cursor-not-allowed"
          >
            {disabled ? (
              <Loader2 className="h-[15px] w-[15px] animate-spin" />
            ) : (
              <Send className="h-[15px] w-[15px]" />
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
