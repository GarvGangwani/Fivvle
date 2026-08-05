"use client";

import Link from "next/link";
import { useWallet } from "@/lib/wallet-context";

// TODO: wire target to user's subscription tier once subscription monetization is real — tracked-work #3.
const MONTHLY_VALIDATION_TARGET = 20;

interface UsageSidebarCardProps {
  validationsThisMonth: number;
}

export function UsageSidebarCard({
  validationsThisMonth,
}: UsageSidebarCardProps) {
  const { balance, loading } = useWallet();

  // TODO: replace hardcoded fallback once wallet is always available — tracked-work.
  const creditsRemaining = balance?.credits_balance ?? 237;

  const overTarget = validationsThisMonth > MONTHLY_VALIDATION_TARGET;
  const progressPercent = Math.min(
    (validationsThisMonth / MONTHLY_VALIDATION_TARGET) * 100,
    100,
  );

  return (
    <div className="flex h-full min-h-[280px] flex-col rounded-md border-2 border-border-master bg-surface-elevated p-6 shadow-brutal-md lg:min-h-[320px]">
      <div className="text-center">
        <span
          className="material-symbols-outlined text-[36px] text-accent"
          aria-hidden
        >
          query_stats
        </span>
        <p className="mt-2 font-label-md text-label-md uppercase text-ink-primary">
          USAGE
        </p>
      </div>

      <div className="my-6 border-t-2 border-border-master" />

      <div className="space-y-8">
        <div>
          <p className="font-label-md text-label-md uppercase text-ink-tertiary">
            CREDITS REMAINING
          </p>
          <p className="mt-2 font-display text-display-lg font-black leading-none text-ink-primary">
            {loading ? "…" : creditsRemaining}
          </p>
        </div>
        <div>
          <div className="flex items-center gap-1">
            <p className="font-label-md text-label-md uppercase text-ink-tertiary">
              VALIDATIONS THIS MONTH
            </p>
            <span
              className="cursor-help font-label-md text-label-md text-ink-tertiary"
              title="Soft monthly target based on your plan. Nothing stops you from running more."
              aria-label="Soft monthly target based on your plan. Nothing stops you from running more."
            >
              ?
            </span>
          </div>
          <p className="mt-2 font-display text-display-lg font-black leading-none text-ink-primary">
            {validationsThisMonth}
            <span className="font-headline text-headline-md text-ink-tertiary">
              {" "}
              / {MONTHLY_VALIDATION_TARGET}
            </span>
          </p>
          <div className="mt-3 h-3 border-2 border-border-master bg-surface-card">
            <div
              className={`h-full transition-all ${
                overTarget ? "bg-status-success" : "bg-accent"
              }`}
              style={{ width: `${progressPercent}%` }}
              role="progressbar"
              aria-valuenow={validationsThisMonth}
              aria-valuemin={0}
              aria-valuemax={MONTHLY_VALIDATION_TARGET}
              aria-label="Validations this month toward soft monthly target"
            />
          </div>
        </div>
      </div>

      <Link
        href="/settings#billing"
        className="mt-auto pt-8 font-label-md text-label-md uppercase text-accent no-underline hover:underline"
      >
        Manage credits →
      </Link>
    </div>
  );
}
