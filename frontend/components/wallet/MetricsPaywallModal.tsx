"use client";

import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import {
  BarChart3,
  Coins,
  Globe,
  MousePointerClick,
  X,
} from "lucide-react";
import {
  METRICS_PAYWALL_CREDITS,
  METRICS_PAYWALL_INCLUDES,
} from "@/lib/wallet-paywall";
import { useWallet } from "@/lib/wallet-context";

const INCLUDE_ICONS = {
  traffic: MousePointerClick,
  sources: BarChart3,
  locations: Globe,
} as const;

interface MetricsPaywallModalProps {
  open: boolean;
  onClose: () => void;
  onConfirm: () => void;
  confirming?: boolean;
}

/**
 * Phase 6 — metrics analysis paywall UI only (no billing).
 */
export function MetricsPaywallModal({
  open,
  onClose,
  onConfirm,
  confirming = false,
}: MetricsPaywallModalProps) {
  const [mounted, setMounted] = useState(false);
  const { credits } = useWallet();
  const hasEnoughCredits = credits >= METRICS_PAYWALL_CREDITS;

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    if (!open) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape" && !confirming) onClose();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose, confirming]);

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
    <div className="fixed inset-0 z-[310] flex items-center justify-center p-4">
      <button
        type="button"
        className="absolute inset-0 z-0 bg-black/60 backdrop-blur-sm"
        aria-label="Close metrics paywall"
        onClick={() => {
          if (!confirming) onClose();
        }}
      />

      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="metrics-paywall-title"
        className="fv-wallet-modal fv-validation-paywall relative z-10 w-full max-w-md overflow-hidden"
      >
        <header className="flex items-center justify-between gap-3 border-b border-[var(--fv-border)] px-5 py-4">
          <div>
            <h2
              id="metrics-paywall-title"
              className="text-base font-semibold text-[var(--fv-text)]"
            >
              Analyze metrics
            </h2>
            <p className="mt-0.5 text-xs text-[var(--fv-text-muted)]">
              Unlock behavioral signal from your live landing page
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="fv-icon-btn"
            aria-label="Close"
            disabled={confirming}
          >
            <X className="h-4 w-4" />
          </button>
        </header>

        <div className="px-5 py-5">
          <p className="mb-3 text-xs font-semibold uppercase tracking-wide text-[var(--fv-text-muted)]">
            Includes
          </p>
          <ul className="mb-5 space-y-2">
            {METRICS_PAYWALL_INCLUDES.map((item) => {
              const Icon = INCLUDE_ICONS[item.id];
              return (
                <li key={item.id} className="fv-validation-paywall-include">
                  <span className="fv-validation-paywall-include-icon">
                    <Icon className="h-4 w-4" aria-hidden />
                  </span>
                  <div className="min-w-0">
                    <p className="text-sm font-semibold text-[var(--fv-text)]">
                      {item.label}
                    </p>
                    <p className="mt-0.5 text-xs text-[var(--fv-text-muted)]">
                      {item.description}
                    </p>
                  </div>
                </li>
              );
            })}
          </ul>

          <div className="fv-validation-paywall-cost mb-4">
            <div className="flex items-center justify-between gap-3">
              <span className="text-sm font-medium text-[var(--fv-text-muted)]">
                Cost
              </span>
              <span className="flex items-center gap-1.5 text-lg font-bold tabular-nums text-[var(--fv-text)]">
                <Coins className="h-4 w-4 text-accent" aria-hidden />
                {METRICS_PAYWALL_CREDITS} Credits
              </span>
            </div>
            <div className="mt-3 flex items-center justify-between gap-3 border-t border-[var(--fv-border)] pt-3 text-xs">
              <span className="text-[var(--fv-text-muted)]">Your balance</span>
              <span
                className={`font-semibold tabular-nums ${
                  hasEnoughCredits
                    ? "text-[var(--fv-text)]"
                    : "text-[var(--fv-danger)]"
                }`}
              >
                {credits.toLocaleString()} Credits
              </span>
            </div>
          </div>

          {!hasEnoughCredits ? (
            <p className="mb-4 text-xs leading-relaxed text-[var(--fv-danger-light)]">
              You need {(METRICS_PAYWALL_CREDITS - credits).toLocaleString()} more
              credits. Open your wallet from the header to buy more.
            </p>
          ) : null}

          <p className="mb-4 text-xs leading-relaxed text-[var(--fv-text-dim)]">
            Credits are deducted from your wallet when you confirm.
          </p>

          <div className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
            <button
              type="button"
              className="fv-btn-ghost px-4 py-2.5 text-sm"
              onClick={onClose}
              disabled={confirming}
            >
              Not now
            </button>
            <button
              type="button"
              className="fv-btn-primary px-4 py-2.5 text-sm disabled:cursor-not-allowed"
              onClick={onConfirm}
              disabled={confirming || !hasEnoughCredits}
            >
              {confirming
                ? "Unlocking…"
                : `Analyze — ${METRICS_PAYWALL_CREDITS} Credits`}
            </button>
          </div>
        </div>
      </div>
    </div>,
    document.body,
  );
}
