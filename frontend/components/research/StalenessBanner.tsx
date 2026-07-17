"use client";

import { AlertTriangle } from "lucide-react";

export function StalenessBanner() {
  return (
    <div
      role="status"
      className="flex items-center gap-2 border-2 border-border-master bg-brutalist-yellow p-3 font-mono text-mono-sm uppercase text-ink-primary shadow-brutal-sm"
    >
      <AlertTriangle className="h-4 w-4 shrink-0" aria-hidden="true" />
      <span>
        This report was regenerated after your last edit. Your edits may
        reference outdated content.
      </span>
    </div>
  );
}
