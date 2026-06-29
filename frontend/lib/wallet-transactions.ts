import type { WalletTransaction, WalletTransactionType } from "@/lib/api";

export function formatTransactionCredits(credits: number): string {
  const prefix = credits > 0 ? "+" : "";
  return `${prefix}${credits.toLocaleString()}`;
}

export function isCreditTransaction(credits: number): boolean {
  return credits > 0;
}

export function formatTransactionDate(iso: string): string {
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(new Date(iso));
}

export function transactionTypeLabel(type: WalletTransactionType): string {
  switch (type) {
    case "TOPUP":
      return "Purchase";
    case "BONUS":
      return "Bonus";
    case "COUPON":
      return "Coupon";
    case "SERVICE_USAGE":
      return "Usage";
    case "REFUND":
      return "Refund";
    case "ADMIN_ADJUSTMENT":
      return "Adjustment";
    default:
      return type;
  }
}

export function summarizeTransaction(tx: WalletTransaction): string {
  const parts = [tx.title];
  if (tx.detail) parts.push(tx.detail);
  if (tx.reference) parts.push(tx.reference);
  return parts.join(" · ");
}
