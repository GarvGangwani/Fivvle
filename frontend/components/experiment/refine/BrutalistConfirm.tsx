"use client";

import { createPortal } from "react-dom";
import { getCanvasAccentPortalTarget } from "@/components/experiment/canvas-accent";

type Props = {
  title: string;
  body: string;
  confirmLabel: string;
  cancelLabel: string;
  onConfirm: () => void | Promise<void>;
  onCancel: () => void;
  loading?: boolean;
  variant?: "default" | "critical";
};

export function BrutalistConfirm({
  title,
  body,
  confirmLabel,
  cancelLabel,
  onConfirm,
  onCancel,
  loading = false,
  variant = "default",
}: Props) {
  if (typeof document === "undefined") return null;

  return createPortal(
    <div className="fixed inset-0 z-[60] bg-ink-primary/50 flex items-center justify-center p-8">
      <div className="max-w-md w-full rounded-md bg-surface-card border-2 border-border-master shadow-brutal-lg">
        <div className="p-6">
          <h3 className="font-headline text-headline-md uppercase mb-3">
            {title}
          </h3>
          <p className="font-body text-body-md text-ink-secondary">{body}</p>
        </div>
        <div className="border-t-2 border-border-master p-4 flex gap-3">
          <button
            type="button"
            onClick={onCancel}
            disabled={loading}
            className="flex-1 rounded-sm border-2 border-border-master bg-surface-card px-6 py-3 font-label-md text-label-md uppercase shadow-brutal-sm hover:shadow-brutal-md hover:-translate-x-0.5 hover:-translate-y-0.5 transition-all disabled:opacity-50"
          >
            {cancelLabel}
          </button>
          <button
            type="button"
            onClick={() => void onConfirm()}
            disabled={loading}
            className={`flex-1 rounded-sm px-6 py-3 border-2 border-border-master font-label-md text-label-md uppercase text-ink-inverse shadow-brutal-md hover:shadow-brutal-lg hover:-translate-x-0.5 hover:-translate-y-0.5 active:translate-x-0 active:translate-y-0 active:shadow-none transition-all disabled:opacity-50 ${
              variant === "critical" ? "bg-status-critical" : "bg-accent"
            }`}
          >
            {loading ? "..." : confirmLabel}
          </button>
        </div>
      </div>
    </div>,
    getCanvasAccentPortalTarget(),
  );
}
