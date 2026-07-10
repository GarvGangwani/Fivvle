"use client";

import { ChatInterface } from "@/components/chat/ChatInterface";

type Props = {
  experimentId: string;
};

export function RefineDeepDive({ experimentId }: Props) {
  return (
    <div className="h-[calc(100vh-64px)] border-t-2 border-border-master bg-canvas-bg">
      <ChatInterface experimentId={experimentId} />
    </div>
  );
}
