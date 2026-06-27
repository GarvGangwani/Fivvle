"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Trash2 } from "lucide-react";
import { deleteProject, ApiError } from "@/lib/api";
import { notifyExperimentsChanged } from "@/lib/experiment-events";
import { TypeConfirmDialog } from "@/components/ui/TypeConfirmDialog";

interface DeleteProjectDialogProps {
  experimentId: string;
  projectName: string;
  open: boolean;
  onClose: () => void;
  onDeleted?: () => void;
  redirectTo?: string;
}

export function DeleteProjectDialog({
  experimentId,
  projectName,
  open,
  onClose,
  onDeleted,
  redirectTo = "/",
}: DeleteProjectDialogProps) {
  const router = useRouter();
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleDelete() {
    setDeleting(true);
    setError(null);
    try {
      await deleteProject(experimentId);
      notifyExperimentsChanged();
      onDeleted?.();
      onClose();
      router.push(redirectTo);
    } catch (err) {
      setError(
        err instanceof ApiError && err.status === 404
          ? "This project no longer exists."
          : "Could not delete project. Please try again.",
      );
    } finally {
      setDeleting(false);
    }
  }

  return (
    <TypeConfirmDialog
      open={open}
      onClose={onClose}
      title="Delete project permanently?"
      icon={<Trash2 className="h-5 w-5" />}
      confirmWord="CONFIRM"
      confirmLabel="Delete project"
      loading={deleting}
      error={error}
      onConfirm={handleDelete}
      description={
        <>
          <p>
            You are about to delete <strong className="text-[var(--fv-text)]">{projectName}</strong>.
            This cannot be undone.
          </p>
          <p className="mt-2">
            All research, landing page content, waitlist signups, and analytics for
            this project will be removed permanently.
          </p>
        </>
      }
    />
  );
}
