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
        className={`max-w-[85%] sm:max-w-[75%] ${
          isUser ? "items-end" : "items-start"
        } flex flex-col gap-1`}
      >
        <div
          className={`rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${
            isUser
              ? "rounded-br-md bg-gray-900 text-white"
              : "rounded-bl-md bg-white text-gray-900 shadow-sm ring-1 ring-gray-200"
          }`}
        >
          <p className="whitespace-pre-wrap break-words">{content}</p>
        </div>
        {timestamp && (
          <span
            className={`px-1 text-xs text-gray-400 ${isUser ? "text-right" : "text-left"}`}
          >
            {formatTime(timestamp)}
          </span>
        )}
      </div>
    </div>
  );
}
