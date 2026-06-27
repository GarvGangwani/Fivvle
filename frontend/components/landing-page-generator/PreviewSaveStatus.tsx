"use client";

import { AlertCircle, Check, Loader2 } from "lucide-react";
import styles from "./device-preview.module.css";

export type PreviewSaveStatus = "idle" | "pending" | "saving" | "saved" | "error";

const STATUS_COPY: Record<
  Exclude<PreviewSaveStatus, "idle">,
  { label: string; className: string }
> = {
  pending: {
    label: "Unsaved changes",
    className: styles.saveStatusPending,
  },
  saving: {
    label: "Saving…",
    className: styles.saveStatusSaving,
  },
  saved: {
    label: "All changes saved",
    className: styles.saveStatusSaved,
  },
  error: {
    label: "Could not save",
    className: styles.saveStatusError,
  },
};

export function PreviewSaveStatusBadge({
  status,
  errorDetail,
}: {
  status: PreviewSaveStatus;
  errorDetail?: string | null;
}) {
  if (status === "idle") return null;

  const meta = STATUS_COPY[status];
  const label =
    status === "error" && errorDetail?.trim()
      ? errorDetail.trim()
      : meta.label;

  return (
    <div
      className={`${styles.saveStatus} ${meta.className}`}
      role="status"
      aria-live="polite"
      aria-atomic="true"
      title={status === "error" && errorDetail ? errorDetail : undefined}
    >
      {status === "saving" ? (
        <Loader2 className={styles.saveStatusIcon} aria-hidden />
      ) : status === "saved" ? (
        <Check className={styles.saveStatusIcon} aria-hidden />
      ) : status === "error" ? (
        <AlertCircle className={styles.saveStatusIcon} aria-hidden />
      ) : (
        <span className={styles.saveStatusDot} aria-hidden />
      )}
      <span>{label}</span>
    </div>
  );
}
