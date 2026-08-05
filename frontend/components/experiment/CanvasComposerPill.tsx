"use client";

import { useState } from "react";
import { useToast } from "@/components/ui/ToastProvider";

type Props = {
  experimentId: string;
  focusedAct: string | null;
};

export function CanvasComposerPill({ experimentId, focusedAct }: Props) {
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const { toast } = useToast();

  async function handleSubmit() {
    const trimmed = message.trim();
    if (!trimmed) return;
    setLoading(true);
    try {
      const res = await fetch("/api/composer/stub", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: trimmed,
          experiment_id: experimentId,
          act: focusedAct ?? null,
        }),
      });
      const data = (await res.json()) as { output?: string };
      toast(data.output ?? "Composer received your request.", "info");
      setMessage("");
    } catch {
      toast("Composer request failed. Try again.", "error");
    } finally {
      setLoading(false);
    }
  }

  function handleKeyDown(event: React.KeyboardEvent<HTMLInputElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      void handleSubmit();
    }
  }

  return (
    <div className="fixed bottom-8 left-1/2 -translate-x-1/2 z-30 w-full max-w-2xl px-4">
      <div className="flex items-center gap-3 rounded-md bg-surface-card border-2 border-border-master shadow-brutal-md px-4 py-3">
        <span className="material-symbols-outlined text-accent" aria-hidden="true">
          auto_awesome
        </span>
        <input
          type="text"
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={`Ask Fivvle about ${focusedAct ?? "this project"}...`}
          className="flex-1 bg-transparent border-none outline-none font-body text-body-md placeholder:text-ink-tertiary"
          aria-label="Ask Fivvle"
        />
        <button
          type="button"
          onClick={() => void handleSubmit()}
          disabled={loading}
          className="rounded-sm bg-ink-primary text-ink-inverse px-6 py-2 border-2 border-border-master font-label-md text-label-md uppercase tracking-wider shadow-brutal-sm hover:shadow-brutal-md hover:-translate-x-0.5 hover:-translate-y-0.5 active:translate-x-0 active:translate-y-0 active:shadow-none transition-all disabled:opacity-60"
        >
          {loading ? "..." : "SEND"}
        </button>
      </div>
    </div>
  );
}
