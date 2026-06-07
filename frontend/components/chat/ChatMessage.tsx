import type { ChatRole } from "@/lib/types";

interface ChatMessageProps {
  role: ChatRole;
  content: string;
  timestamp?: string;
}

function formatTime(timestamp: string): string {
  return new Date(timestamp).toLocaleTimeString(undefined, {
    hour: "numeric",
    minute: "2-digit",
  });
}

export function ChatMessage({ role, content, timestamp }: ChatMessageProps) {
  const isUser = role === "user";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`flex flex-col gap-1 ${
          isUser ? "items-end" : "items-start"
        }`}
      >
        <div
          className={`whitespace-pre-wrap break-words ${
            isUser ? "fv-msg-user" : "fv-msg-ai"
          }`}
        >
          {content}
        </div>
        {timestamp && (
          <span
            className={`px-1 text-xs text-[var(--fv-text-muted)] ${isUser ? "text-right" : "text-left"}`}
          >
            {formatTime(timestamp)}
          </span>
        )}
      </div>
    </div>
  );
}
