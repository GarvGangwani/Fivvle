"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Archive, Loader2, X } from "lucide-react";
import { archiveProject, ApiError } from "@/lib/api";
import { notifyExperimentsChanged } from "@/lib/experiment-events";
import { ErrorBanner } from "@/components/ui/ErrorBanner";

interface ArchiveProjectDialogProps {
  experimentId: string;
  projectName: string;
  open: boolean;
  onClose: () => void;
  onArchived?: () => void;
  redirectTo?: string;
}

export function ArchiveProjectDialog({
  experimentId,
  projectName,
  open,
  onClose,
  onArchived,
  redirectTo = "/",
}: ArchiveProjectDialogProps) {
  const router = useRouter();
  const [archiving, setArchiving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!open) return null;

  async function handleArchive() {
    setArchiving(true);
    setError(null);
    try {
      await archiveProject(experimentId);
      notifyExperimentsChanged();
      onArchived?.();
      onClose();
      router.push(redirectTo);
    } catch (err) {
      setError(
        err instanceof ApiError && err.status === 409
          ? "This project is already archived."
          : "Could not archive project. Please try again.",
      );
    } finally {
      setArchiving(false);
    }
  }

  return (
    <div
      className="fixed inset-0 z-[80] flex items-center justify-center bg-black/60 p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="archive-dialog-title"
    >
      <div className="w-full max-w-md rounded-2xl border border-[var(--fv-border)] bg-[var(--fv-surface)] p-6 shadow-xl">
        <div className="mb-4 flex items-start justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-[var(--fv-danger)]/10 text-[var(--fv-danger)]">
              <Archive className="h-5 w-5" />
            </div>
            <div>
              <h2
                id="archive-dialog-title"
                className="text-lg font-semibold text-[var(--fv-text)]"
              >
                Archive project?
              </h2>
              <p className="mt-0.5 text-sm text-[var(--fv-text-muted)]">
                {projectName}
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            disabled={archiving}
            className="fv-icon-btn shrink-0"
            aria-label="Close"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <p className="text-sm leading-relaxed text-[var(--fv-text-muted)]">
          Archived projects are hidden from your main list. You can restore them
          anytime from the Archived page. Public landing pages stop accepting
          new signups while archived.
        </p>

        {error && <ErrorBanner message={error} className="mt-4" />}

        <div className="mt-6 flex justify-end gap-3">
          <button
            type="button"
            onClick={onClose}
            disabled={archiving}
            className="fv-btn-ghost px-4 py-2 text-sm disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={() => void handleArchive()}
            disabled={archiving}
            className="fv-btn-primary bg-[var(--fv-danger)] px-4 py-2 text-sm hover:bg-red-500 disabled:opacity-50"
          >
            {archiving ? (
              <span className="inline-flex items-center gap-2">
                <Loader2 className="h-4 w-4 animate-spin" />
                Archiving…
              </span>
            ) : (
              "Archive project"
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
