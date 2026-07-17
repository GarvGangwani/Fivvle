"use client";

import { useEffect, useId, useState, type ReactNode } from "react";
import { Loader2, X } from "lucide-react";
import { ErrorBanner } from "@/components/ui/ErrorBanner";

export interface TypeConfirmDialogProps {
  open: boolean;
  onClose: () => void;
  title: string;
  description: ReactNode;
  /** Word the user must type exactly (default: CONFIRM). */
  confirmWord?: string;
  /** Primary action label when ready. */
  confirmLabel?: string;
  /** Icon shown in the dialog header. */
  icon?: ReactNode;
  loading?: boolean;
  error?: string | null;
  onConfirm: () => void | Promise<void>;
}

export function TypeConfirmDialog({
  open,
  onClose,
  title,
  description,
  confirmWord = "CONFIRM",
  confirmLabel = "Confirm",
  icon,
  loading = false,
  error = null,
  onConfirm,
}: TypeConfirmDialogProps) {
  const inputId = useId();
  const [typed, setTyped] = useState("");

  useEffect(() => {
    if (!open) {
      setTyped("");
    }
  }, [open]);

  if (!open) return null;

  const canConfirm = typed === confirmWord && !loading;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby={`${inputId}-title`}
    >
      <div className="w-full max-w-md rounded-2xl border border-[var(--fv-border)] bg-[var(--fv-surface)] p-6 shadow-xl">
        <div className="mb-4 flex items-start justify-between gap-3">
          <div className="flex items-center gap-3">
            {icon ? (
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-[var(--fv-danger)]/10 text-[var(--fv-danger)]">
                {icon}
              </div>
            ) : null}
            <div>
              <h2
                id={`${inputId}-title`}
                className="text-lg font-semibold text-[var(--fv-text)]"
              >
                {title}
              </h2>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            disabled={loading}
            className="fv-icon-btn shrink-0"
            aria-label="Close"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="text-sm leading-relaxed text-[var(--fv-text-muted)]">
          {description}
        </div>

        <div className="mt-4">
          <label
            htmlFor={inputId}
            className="mb-1.5 block text-[12px] font-medium text-[var(--fv-text-soft)]"
          >
            Type <span className="font-mono text-[var(--fv-text)]">{confirmWord}</span>{" "}
            to continue
          </label>
          <input
            id={inputId}
            type="text"
            value={typed}
            disabled={loading}
            onChange={(e) => setTyped(e.target.value)}
            autoComplete="off"
            spellCheck={false}
            className="fv-input w-full rounded-lg border border-[var(--fv-border)] bg-[var(--fv-surface-2)] px-3 py-2.5 font-mono text-[13px]"
            placeholder={confirmWord}
          />
        </div>

        {error && <ErrorBanner message={error} className="mt-4" />}

        <div className="mt-6 flex justify-end gap-3">
          <button
            type="button"
            onClick={onClose}
            disabled={loading}
            className="fv-btn-ghost px-4 py-2 text-sm disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={() => void onConfirm()}
            disabled={!canConfirm}
            className="fv-btn-primary bg-[var(--fv-danger)] px-4 py-2 text-sm hover:bg-red-500 disabled:opacity-50"
          >
            {loading ? (
              <span className="inline-flex items-center gap-2">
                <Loader2 className="h-4 w-4 animate-spin" />
                Working…
              </span>
            ) : (
              confirmLabel
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
