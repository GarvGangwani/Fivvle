"use client";

import { useState } from "react";
import { CheckCircle2, Loader2, Ticket, X } from "lucide-react";
import { redeemWalletCoupon } from "@/lib/api";
import { readCouponRedeemError } from "@/lib/coupon-errors";
import { WELCOME_COUPON_CODE } from "@/lib/pricing";
import { useWallet } from "@/lib/wallet-context";
import { ErrorBanner } from "@/components/ui/ErrorBanner";
import { formatUsdFromCredits } from "@/lib/pricing";

interface CouponRedemptionProps {
  onRedeemed?: () => void;
}

export function CouponRedemption({ onRedeemed }: CouponRedemptionProps) {
  const { balance, applyWalletPatch } = useWallet();
  const [code, setCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<{
    code: string;
    credits: number;
  } | null>(null);
  const [redeeming, setRedeeming] = useState(false);

  const welcomeAlreadyRedeemed = balance?.has_redeemed_welcome_coupon ?? false;

  async function handleRedeem(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSuccess(null);

    const trimmed = code.trim();
    if (!trimmed) {
      setError("Enter a coupon code.");
      return;
    }

    setRedeeming(true);
    try {
      const result = await redeemWalletCoupon(trimmed);
      const isWelcomeCoupon =
        trimmed.toUpperCase() === WELCOME_COUPON_CODE.toUpperCase();
      applyWalletPatch({
        credits_balance: result.new_balance,
        usd_equivalent: formatUsdFromCredits(result.new_balance),
        has_redeemed_welcome_coupon: isWelcomeCoupon
          ? true
          : balance?.has_redeemed_welcome_coupon,
      });
      setCode("");
      setSuccess({ code: result.code, credits: result.credits_added });
      onRedeemed?.();
    } catch (err) {
      setError(readCouponRedeemError(err));
    } finally {
      setRedeeming(false);
    }
  }

  return (
    <section aria-live="polite">
      <h3 className="fv-panel-label mb-3">Redeem coupon</h3>

      {welcomeAlreadyRedeemed ? (
        <p className="mb-3 text-xs text-[var(--fv-text-dim)]">
          Welcome coupon already used on this account. You can still redeem other
          codes below.
        </p>
      ) : null}

      {success ? (
        <div className="fv-wallet-coupon-success mb-3">
          <CheckCircle2
            className="mt-0.5 h-4 w-4 shrink-0 text-[var(--fv-success)]"
            aria-hidden
          />
          <div className="min-w-0 flex-1">
            <p className="text-sm font-semibold text-[var(--fv-text)]">
              Coupon redeemed
            </p>
            <p className="mt-1 text-sm leading-relaxed text-[var(--fv-text-muted)]">
              <span className="font-mono text-[var(--fv-text-soft)]">
                {success.code}
              </span>{" "}
              added {success.credits.toLocaleString()} credits to your wallet.
            </p>
          </div>
          <button
            type="button"
            onClick={() => setSuccess(null)}
            className="fv-icon-btn shrink-0 self-start"
            aria-label="Dismiss success message"
          >
            <X className="h-3.5 w-3.5" />
          </button>
        </div>
      ) : null}

      {error ? (
        <ErrorBanner
          message={error}
          onDismiss={() => setError(null)}
          className="mb-3"
        />
      ) : null}

      <form onSubmit={(e) => void handleRedeem(e)} className="fv-wallet-coupon-form">
        <div className="fv-wallet-coupon-input-wrap">
          <Ticket className="fv-wallet-coupon-input-icon" aria-hidden />
          <input
            type="text"
            value={code}
            onChange={(e) => {
              setCode(e.target.value);
              if (error) setError(null);
            }}
            placeholder={`e.g. ${WELCOME_COUPON_CODE}`}
            className="fv-input fv-wallet-coupon-input w-full"
            autoComplete="off"
            spellCheck={false}
            disabled={redeeming}
            aria-label="Coupon code"
            aria-invalid={error ? true : undefined}
          />
        </div>
        <button
          type="submit"
          className="fv-btn-primary fv-wallet-coupon-redeem shrink-0 px-4 py-2 text-sm"
          disabled={redeeming}
        >
          {redeeming ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
              Redeeming…
            </>
          ) : (
            "Redeem"
          )}
        </button>
      </form>
    </section>
  );
}
