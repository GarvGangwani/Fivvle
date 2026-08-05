"use client";

import { createPortal } from "react-dom";
import { getCanvasAccentPortalTarget } from "@/components/experiment/canvas-accent";
import { getThemePalette } from "@/lib/theme-palettes";

type Props = {
  projectName: string | null;
  paletteName: string;
  onAccept: () => void;
  onDecline: () => void;
  busy?: boolean;
};

/**
 * Consent step between idea capture and the refine handoff. The AI's palette is
 * a suggestion — nothing recolors until the founder says yes.
 */
export function ThemeConsentDialog({
  projectName,
  paletteName,
  onAccept,
  onDecline,
  busy = false,
}: Props) {
  if (typeof document === "undefined") return null;

  const palette = getThemePalette(paletteName);
  const subject = projectName?.trim() || "your idea";

  return createPortal(
    <div
      className="fixed inset-0 z-[90] flex items-center justify-center bg-ink-primary/50 p-8"
      role="dialog"
      aria-modal="true"
      aria-label="Suggested canvas theme"
    >
      <div className="w-full max-w-md rounded-md border-2 border-border-master bg-surface-card shadow-brutal-lg">
        <div className="p-6">
          <h3 className="mb-3 font-headline text-headline-md uppercase">
            Fivvle picked a theme for {subject}
          </h3>

          <div className="flex items-center gap-3 rounded-md border-2 border-border-master bg-surface-muted p-3">
            <span
              aria-hidden
              className="h-10 w-10 shrink-0 border-2 border-border-master"
              style={{ backgroundColor: palette.accent }}
            />
            <span className="min-w-0">
              <span className="block font-label-md text-label-md uppercase text-ink-primary">
                {palette.displayName}
              </span>
              <span className="block font-mono text-mono-sm uppercase text-ink-tertiary">
                {palette.accent} · {palette.domain}
              </span>
            </span>
          </div>

          <p className="mt-3 font-body text-body-md text-ink-secondary">
            It colors this experiment&apos;s canvas only. You can change or revert
            it anytime from the canvas.
          </p>
        </div>

        <div className="flex gap-3 border-t-2 border-border-master p-4">
          <button
            type="button"
            onClick={onDecline}
            disabled={busy}
            className="flex-1 rounded-sm border-2 border-border-master bg-surface-card px-6 py-3 font-label-md text-label-md uppercase shadow-brutal-sm transition-all hover:-translate-x-0.5 hover:-translate-y-0.5 hover:shadow-brutal-md disabled:opacity-50"
          >
            Keep purple
          </button>
          <button
            type="button"
            onClick={onAccept}
            disabled={busy}
            className="flex-1 rounded-sm border-2 border-border-master bg-accent px-6 py-3 font-label-md text-label-md uppercase text-accent-fg shadow-brutal-md transition-all hover:-translate-x-0.5 hover:-translate-y-0.5 hover:shadow-brutal-lg active:translate-x-0 active:translate-y-0 active:shadow-none disabled:opacity-50"
          >
            {busy ? "..." : "Use it"}
          </button>
        </div>
      </div>
    </div>,
    getCanvasAccentPortalTarget(),
  );
}
