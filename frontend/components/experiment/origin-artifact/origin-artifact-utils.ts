/**
 * Helpers for the Origin Artifact provenance card (frozen original idea).
 */

export function formatCaptureDateTime(
  createdAt?: string | null,
  fallback?: string | null,
): string {
  const raw = createdAt ?? fallback;
  if (!raw) return "DATE UNKNOWN";
  const d = new Date(raw);
  if (Number.isNaN(d.getTime())) return "DATE UNKNOWN";
  const date = d
    .toLocaleDateString(undefined, {
      month: "short",
      day: "numeric",
      year: "numeric",
    })
    .toUpperCase();
  const time = d
    .toLocaleTimeString(undefined, {
      hour: "numeric",
      minute: "2-digit",
    })
    .toUpperCase();
  return `${date} · ${time}`;
}

/** Original idea is write-once — always V1. */
export function originVersionLabel(): string {
  return "V1";
}
