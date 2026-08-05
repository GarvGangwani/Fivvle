"use client";

import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { Coins, X } from "lucide-react";
import { useWallet } from "@/lib/wallet-context";
import { BuyCreditsFlow } from "./BuyCreditsFlow";
import { CouponRedemption } from "./CouponRedemption";

interface WalletModalProps {
  open: boolean;
  onClose: () => void;
}

export function WalletModal({ open, onClose }: WalletModalProps) {
  const [mounted, setMounted] = useState(false);
  const { balance, credits, usdLabel, loading, error, refresh } = useWallet();

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    if (!open) return;
    void refresh();
  }, [open, refresh]);

  useEffect(() => {
    if (!open) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  useEffect(() => {
    if (!open) return;
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = previous;
    };
  }, [open]);

  if (!open || !mounted) return null;

  return createPortal(
    <div className="fixed inset-0 z-[300] flex items-center justify-center p-4">
      <button
        type="button"
        className="absolute inset-0 z-0 bg-black/60 backdrop-blur-sm"
        aria-label="Close wallet"
        onClick={onClose}
      />

      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="wallet-modal-title"
        className="fv-wallet-modal relative z-10 flex max-h-[min(90vh,720px)] w-full max-w-lg flex-col overflow-hidden"
      >
        <header className="flex shrink-0 items-center justify-between gap-3 border-b border-[var(--fv-border)] px-5 py-4">
          <div className="flex items-center gap-3">
            <span className="flex h-9 w-9 items-center justify-center rounded-lg border border-[var(--fv-border)] bg-[var(--fv-surface-2)]">
              <Coins className="h-4 w-4 text-accent" aria-hidden />
            </span>
            <div>
              <h2
                id="wallet-modal-title"
                className="text-base font-semibold text-[var(--fv-text)]"
              >
                Wallet
              </h2>
              <p className="mt-0.5 text-xs text-[var(--fv-text-muted)]">
                Credits power validation and insights
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="fv-icon-btn"
            aria-label="Close wallet"
          >
            <X className="h-4 w-4" />
          </button>
        </header>

        <div className="min-h-0 flex-1 overflow-y-auto px-5 py-5">
          <section className="fv-wallet-balance-card mb-6" aria-live="polite">
            <p className="fv-wallet-balance-card-label">Current balance</p>
            <p className="fv-wallet-balance-card-credits">
              {loading && balance === null
                ? "…"
                : `${credits.toLocaleString()} Credits`}
            </p>
            <p className="fv-wallet-balance-card-usd">
              ≈ {loading && balance === null ? "…" : usdLabel}
            </p>
            {error ? (
              <p className="mt-2 text-xs text-[var(--fv-danger)]">{error}</p>
            ) : null}
          </section>

          <div className="mb-6">
            <CouponRedemption />
          </div>

          <BuyCreditsFlow />
        </div>
      </div>
    </div>,
    document.body,
  );
}
