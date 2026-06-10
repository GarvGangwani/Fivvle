"use client";

import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type KeyboardEvent,
} from "react";
import { Loader2, Paperclip, Send, Zap } from "lucide-react";

interface ChatInputProps {
  onSend: (text: string, deepResearch: boolean) => void;
  disabled: boolean;
  placeholder: string;
  deepResearchLocked?: boolean;
  prefillText?: string | null;
  prefillNonce?: number;
}

const MAX_HEIGHT_PX = 120;

function getMaxTextareaHeightPx(): number {
  if (typeof window === "undefined") return MAX_HEIGHT_PX;
  const mobileCap = Math.floor(window.innerHeight * 0.4);
  if (window.matchMedia("(max-width: 1023px)").matches) {
    return Math.min(MAX_HEIGHT_PX, mobileCap);
  }
  return MAX_HEIGHT_PX;
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
  const [deepResearch, setDeepResearch] = useState(true);

  const resizeTextarea = useCallback(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, getMaxTextareaHeightPx())}px`;
  }, []);

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

  function handleSend() {
    const el = textareaRef.current;
    if (!el) return;
    const text = el.value.trim();
    if (!text || disabled) return;
    onSend(text, deepResearchLocked ? false : deepResearch);
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
    <div className="sticky bottom-0 z-10 bg-gradient-to-t from-[var(--fv-bg)] via-[var(--fv-bg)]/95 to-transparent px-4 pb-4 pt-6 backdrop-blur-md lg:px-12">
      <div className="mx-auto flex max-w-3xl flex-col gap-2.5 rounded-2xl border border-[var(--fv-border)] bg-[var(--fv-surface)]/80 p-2 shadow-[0_-4px_24px_rgba(0,0,0,0.3)] backdrop-blur-xl">
        <textarea
          ref={textareaRef}
          rows={1}
          placeholder={placeholder}
          disabled={disabled}
          onChange={resizeTextarea}
          onKeyDown={handleKeyDown}
          className="min-h-[50px] max-h-[40vh] w-full resize-none border-none bg-transparent text-[14px] leading-normal text-[var(--fv-text)] outline-none placeholder:text-[var(--fv-text-muted)] disabled:cursor-not-allowed disabled:opacity-50 lg:max-h-[120px]"
          style={{ lineHeight: 1.5 }}
        />

        <div className="flex items-center gap-2">
          <button
            type="button"
            className="fv-icon-btn cursor-not-allowed opacity-40"
            title="Coming soon"
            aria-label="Attach file"
            disabled
          >
            <Paperclip className="h-4 w-4" />
          </button>

          {!deepResearchLocked && (
            <button
              type="button"
              onClick={() => setDeepResearch((v) => !v)}
              disabled={disabled}
              className={`fv-deep-toggle ${deepResearch ? "fv-deep-toggle-on" : ""}`}
            >
              <Zap className="h-[13px] w-[13px]" />
              Deep Research {deepResearch ? "ON" : "OFF"}
            </button>
          )}

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
