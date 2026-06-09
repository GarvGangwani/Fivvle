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

  if (isUser) {
    return (
      <div className="flex justify-end">
        <div className="fv-msg-user whitespace-pre-wrap break-words">{content}</div>
      </div>
    );
  }

  return (
    <div className="flex justify-start">
      <div className="w-full max-w-[80%]">
        <div className="mb-1.5 flex items-center gap-2">
          <div
            className="fv-f-logo"
            style={{ width: 22, height: 22, fontSize: 11 }}
          >
            F
          </div>
          <span className="text-[12px] font-medium text-fv-text-dim">Fivvle</span>
          {showRefining && (
            <span className="fv-refining-badge">Refining</span>
          )}
        </div>
        <div className="fv-msg-ai max-w-full whitespace-pre-wrap break-words">
          {content}
        </div>
      </div>
    </div>
  );
}
