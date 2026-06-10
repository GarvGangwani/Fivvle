import type { ChatRole } from "@/lib/types";

interface ChatMessageProps {
  role: ChatRole;
  content: string;
  timestamp?: string;
  showRefining?: boolean;
}

export function ChatMessage({
  role,
  content,
  showRefining = false,
}: ChatMessageProps) {
  const isUser = role === "user";

  return (
    <div className="fv-msg-enter border-b border-[var(--fv-border)] py-6">
      <div className="mx-auto max-w-[680px]">
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
            <div
              className={`whitespace-pre-wrap break-words ${isUser ? "fv-msg-user" : "fv-msg-ai"}`}
            >
              {content}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
