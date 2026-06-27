"use client";

import { ChatInterface } from "@/components/chat/ChatInterface";

/** Demo showcase — live chat refinement UI. */
export function QuestMapExperience() {
  return (
    <div className="flex h-[min(720px,80vh)] min-h-[480px] flex-col overflow-hidden rounded-xl border border-[var(--fv-border)] bg-[var(--fv-surface)]">
      <ChatInterface />
    </div>
  );
}
