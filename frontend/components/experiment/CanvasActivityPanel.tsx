"use client";

import { useEffect, useState } from "react";
import { useActivityStream } from "./hooks/useActivityStream";

type Props = {
  experimentId: string;
};

const EVENT_BAR_CLASS: Record<string, string> = {
  pipeline: "bg-brand-primary",
  chat_message: "bg-ink-primary",
  resource_added: "bg-brand-primary-soft",
  resource_deleted: "bg-ink-tertiary",
  phase_completed: "bg-brand-primary",
  verdict_rendered: "bg-brand-primary",
};

function timeAgo(value: string): string {
  const d = new Date(value).getTime();
  const diff = Math.max(0, Date.now() - d);
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

export function CanvasActivityPanel({ experimentId }: Props) {
  const { items } = useActivityStream(experimentId, 30);
  const key = `canvas-activity-collapsed:${experimentId}`;
  const [collapsed, setCollapsed] = useState(false);

  useEffect(() => {
    const raw = localStorage.getItem(key);
    setCollapsed(raw === "1");
  }, [key]);

  const toggle = () => {
    setCollapsed((prev) => {
      const next = !prev;
      localStorage.setItem(key, next ? "1" : "0");
      return next;
    });
  };

  return (
    <aside
      className={`fixed right-6 top-20 z-20 rounded-md border-2 border-border-master bg-surface-card shadow-brutal-md transition-all ${
        collapsed ? "w-10" : "w-80"
      }`}
    >
      {collapsed ? (
        <button
          type="button"
          onClick={toggle}
          className="h-full min-h-[120px] w-full font-label-md text-label-sm uppercase tracking-widest text-ink-primary [writing-mode:vertical-rl]"
        >
          ACTIVITY
        </button>
      ) : (
        <>
          <button
            type="button"
            onClick={toggle}
            className="flex w-full items-center justify-between border-b-2 border-border-master px-4 py-3 text-left"
          >
            <span className="font-label-md text-label-md uppercase text-ink-primary">
              RECENT ACTIVITY
            </span>
            <span className="font-mono text-mono-sm text-brand-primary">LIVE_LOG</span>
          </button>
          <div className="max-h-72 space-y-2 overflow-y-auto p-3">
            {items.length === 0 ? (
              <div className="p-4 text-center">
                <p className="font-mono text-mono-sm text-ink-tertiary uppercase">
                  No activity yet.
                </p>
                <p className="font-body text-body-sm text-ink-tertiary mt-1">
                  Events from research, chat, and phase progression will appear here.
                </p>
              </div>
            ) : (
              items.map((item) => (
                <div
                  key={`${item.event_type}-${item.id}`}
                  className="flex items-stretch gap-2 rounded-sm border-2 border-border-master bg-surface-elevated p-2"
                >
                  <div
                    className={`w-1 shrink-0 ${
                      EVENT_BAR_CLASS[item.event_type] ?? "bg-ink-tertiary"
                    }`}
                  />
                  <div className="min-w-0">
                    <p className="font-body-sm text-body-sm text-ink-primary">{item.summary}</p>
                    <p className="font-mono text-mono-sm text-ink-tertiary">
                      {timeAgo(item.occurred_at)}
                    </p>
                  </div>
                </div>
              ))
            )}
          </div>
        </>
      )}
    </aside>
  );
}
