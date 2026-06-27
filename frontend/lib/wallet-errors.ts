import { ApiError } from "@/lib/api";

type InsufficientCreditsDetail = {
  error?: string;
  available?: number;
  required?: number;
};

function readInsufficientCreditsDetail(
  err: ApiError,
): InsufficientCreditsDetail | null {
  if (err.status !== 402) return null;
  const body = err.body;
  if (
    !body ||
    typeof body !== "object" ||
    !("detail" in body) ||
    !body.detail ||
    typeof body.detail !== "object"
  ) {
    return null;
  }
  const detail = body.detail as InsufficientCreditsDetail;
  if (detail.error !== "insufficient_credits") return null;
  return detail;
}

export function isInsufficientCreditsError(err: unknown): boolean {
  return err instanceof ApiError && readInsufficientCreditsDetail(err) !== null;
}

export function readInsufficientCreditsMessage(
  err: unknown,
  fallbackRequired: number,
): string | null {
  if (!(err instanceof ApiError)) return null;
  const detail = readInsufficientCreditsDetail(err);
  if (!detail) return null;
  const required = detail.required ?? fallbackRequired;
  const available = detail.available ?? 0;
  return `You need ${required.toLocaleString()} credits but only have ${available.toLocaleString()}. Open your wallet to buy more.`;
}

export function readPaidActionError(
  err: unknown,
  options: {
    fallbackRequired?: number;
    fallback?: string;
  } = {},
): string {
  const fallback = options.fallback ?? "Something went wrong. Please try again.";
  if (options.fallbackRequired !== undefined) {
    const insufficient = readInsufficientCreditsMessage(
      err,
      options.fallbackRequired,
    );
    if (insufficient) return insufficient;
  }
  if (err instanceof ApiError && err.status === 502) {
    return "The server could not start this action. Your credits have been refunded — please try again.";
  }
  return fallback;
}
