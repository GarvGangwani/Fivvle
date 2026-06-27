"use client";

import { useState } from "react";
import { ArrowLeft, CheckCircle2, Loader2 } from "lucide-react";
import { ApiError, createWalletOrder, verifyWalletPayment, type CreditPack } from "@/lib/api";
import { PACK_UI_META } from "@/lib/pricing";
import { loadRazorpayCheckout } from "@/lib/razorpay-checkout";
import { useWallet } from "@/lib/wallet-context";
import { ErrorBanner } from "@/components/ui/ErrorBanner";
import { formatUsdFromCredits } from "@/lib/pricing";
import { RazorpayBrand } from "@/components/wallet/RazorpayBrand";

type FlowStep = "packs" | "checkout" | "success";

interface BuyCreditsFlowProps {
  onPurchaseComplete?: () => void;
}

function paymentErrorMessage(err: unknown): string {
  if (err instanceof ApiError) {
    const detail =
      typeof err.body === "object" &&
      err.body !== null &&
      "detail" in err.body &&
      typeof (err.body as { detail: unknown }).detail === "string"
        ? (err.body as { detail: string }).detail
        : null;
    if (err.status === 503) {
      return "Payments are not configured yet. Try again later.";
    }
    if (err.status === 502) {
      return "Could not start checkout. Please try again.";
    }
    if (err.status === 409) {
      return detail ?? "This payment was already processed.";
    }
    if (detail) {
      return detail;
    }
    return "Payment could not be completed. Please try again.";
  }
  if (err instanceof Error) {
    if (err.message === "Payment cancelled") {
      return "";
    }
    if (err.message === "Razorpay failed to load") {
      return "Could not load payment checkout. Refresh and try again.";
    }
    if (err.message) {
      return err.message;
    }
  }
  return "Payment could not be completed. Please try again.";
}

export function BuyCreditsFlow({ onPurchaseComplete }: BuyCreditsFlowProps) {
  const { balance, refresh, applyWalletPatch } = useWallet();
  const packs = balance?.packs ?? [];

  const [step, setStep] = useState<FlowStep>("packs");
  const [selectedPack, setSelectedPack] = useState<CreditPack | null>(null);
  const [confirming, setConfirming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [purchasedCredits, setPurchasedCredits] = useState(0);

  function handleSelectPack(pack: CreditPack) {
    setSelectedPack(pack);
    setStep("checkout");
    setError(null);
  }

  function handleBack() {
    setStep("packs");
    setSelectedPack(null);
    setConfirming(false);
    setError(null);
  }

  async function handleConfirm() {
    if (!selectedPack) return;
    setConfirming(true);
    setError(null);

    try {
      const order = await createWalletOrder(selectedPack.id);
      const Razorpay = await loadRazorpayCheckout();

      await new Promise<void>((resolve, reject) => {
        let settled = false;
        let verificationInFlight = false;

        const checkout = new Razorpay({
          key: order.razorpay_key_id,
          amount: order.amount_inr_paise,
          currency: order.currency,
          name: "Fivvle",
          description: `${order.pack_name} credit pack`,
          order_id: order.razorpay_order_id,
          handler: (response) => {
            verificationInFlight = true;
            void (async () => {
              try {
                const verified = await verifyWalletPayment({
                  razorpayPaymentId: response.razorpay_payment_id,
                  razorpayOrderId: response.razorpay_order_id,
                  razorpaySignature: response.razorpay_signature,
                });
                applyWalletPatch({
                  credits_balance: verified.new_balance,
                  usd_equivalent: formatUsdFromCredits(verified.new_balance),
                });
                setPurchasedCredits(
                  verified.credits_added + verified.bonus_credits,
                );
                await refresh();
                onPurchaseComplete?.();
                settled = true;
                resolve();
              } catch (err) {
                settled = true;
                reject(err);
              }
            })();
          },
          modal: {
            ondismiss: () => {
              if (settled || verificationInFlight) {
                return;
              }
              reject(new Error("Payment cancelled"));
            },
          },
        });
        checkout.on("payment.failed", (payload) => {
          if (settled) {
            return;
          }
          settled = true;
          reject(new Error(payload.error.description || "Payment failed"));
        });
        checkout.open();
      });

      setStep("success");
    } catch (err) {
      const message = paymentErrorMessage(err);
      setError(message || null);
    } finally {
      setConfirming(false);
    }
  }

  if (step === "checkout" && selectedPack) {
    const meta = PACK_UI_META[selectedPack.id];
    const bonusLabel =
      selectedPack.bonus_credits > 0
        ? ` (+${selectedPack.bonus_credits} bonus)`
        : "";

    return (
      <section>
        <button
          type="button"
          onClick={handleBack}
          className="fv-wallet-back-btn mb-4"
          disabled={confirming}
        >
          <ArrowLeft className="h-3.5 w-3.5" aria-hidden />
          Back to packs
        </button>

        <h3 className="fv-panel-label mb-3">Confirm purchase</h3>

        {error ? (
          <ErrorBanner
            message={error}
            onDismiss={() => setError(null)}
            className="mb-4"
          />
        ) : null}

        <div className="fv-wallet-checkout-card mb-5">
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="text-sm font-semibold text-[var(--fv-text)]">
                {selectedPack.name} pack
              </p>
              {meta?.description ? (
                <p className="mt-1 text-xs text-[var(--fv-text-muted)]">
                  {meta.description}
                </p>
              ) : null}
            </div>
            {meta?.popular ? (
              <span className="fv-wallet-pack-badge shrink-0">Popular</span>
            ) : null}
          </div>

          <dl className="fv-wallet-checkout-summary mt-4">
            <div className="fv-wallet-checkout-row">
              <dt>Credits</dt>
              <dd>
                {selectedPack.total_credits.toLocaleString()}
                {bonusLabel}
              </dd>
            </div>
            <div className="fv-wallet-checkout-row">
              <dt>Price</dt>
              <dd>{selectedPack.usd_display}</dd>
            </div>
            <div className="fv-wallet-checkout-row fv-wallet-checkout-row-total">
              <dt>Checkout</dt>
              <dd className="inline-flex items-center gap-1.5">
                <span className="text-[var(--fv-text-muted)]">Secure payment via</span>
                <RazorpayBrand />
              </dd>
            </div>
          </dl>
        </div>

        <p className="mb-4 text-xs leading-relaxed text-[var(--fv-text-dim)]">
          Credits never expire. You will complete payment in{" "}
          <RazorpayBrand className="align-middle" /> checkout (test mode in
          development).
        </p>

        <button
          type="button"
          className="fv-btn-primary fv-wallet-buy-confirm w-full justify-center px-4 py-2.5 text-sm"
          onClick={() => void handleConfirm()}
          disabled={confirming}
        >
          {confirming ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
              Opening checkout…
            </>
          ) : (
            `Pay ${selectedPack.usd_display}`
          )}
        </button>
      </section>
    );
  }

  if (step === "success" && selectedPack) {
    return (
      <section className="fv-wallet-success text-center">
        <span className="fv-wallet-success-icon mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full">
          <CheckCircle2 className="h-6 w-6 text-[var(--fv-success)]" aria-hidden />
        </span>
        <h3 className="text-base font-semibold text-[var(--fv-text)]">
          Payment successful
        </h3>
        <p className="mx-auto mt-2 max-w-xs text-sm leading-relaxed text-[var(--fv-text-muted)]">
          {purchasedCredits.toLocaleString()} credits from the {selectedPack.name}{" "}
          pack were added to your wallet.
        </p>
        <button
          type="button"
          className="fv-btn-ghost fv-wallet-buy-confirm mt-6 px-4 py-2 text-sm"
          onClick={handleBack}
        >
          Back to wallet
        </button>
      </section>
    );
  }

  if (!packs.length) {
    return (
      <section>
        <h3 className="fv-panel-label mb-3">Credit packs</h3>
        <p className="text-sm text-[var(--fv-text-muted)]">
          Loading packs…
        </p>
      </section>
    );
  }

  return (
    <section>
      <h3 className="fv-panel-label mb-3">Credit packs</h3>
      <ul className="space-y-2">
        {packs.map((pack) => {
          const meta = PACK_UI_META[pack.id];
          return (
            <li
              key={pack.id}
              className={`fv-wallet-pack-row ${
                meta?.popular ? "fv-wallet-pack-row-popular" : ""
              }`}
            >
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-sm font-semibold text-[var(--fv-text)]">
                    {pack.name}
                  </span>
                  {meta?.popular ? (
                    <span className="fv-wallet-pack-badge">Popular</span>
                  ) : null}
                </div>
                {meta?.description ? (
                  <p className="mt-0.5 text-xs text-[var(--fv-text-muted)]">
                    {meta.description}
                  </p>
                ) : null}
                <p className="mt-1.5 text-xs font-medium tabular-nums text-[var(--fv-text-soft)]">
                  {pack.total_credits.toLocaleString()} credits · {pack.usd_display}
                </p>
              </div>
              <button
                type="button"
                className="fv-btn-primary fv-wallet-pack-buy shrink-0 px-3 py-1.5 text-xs"
                onClick={() => handleSelectPack(pack)}
              >
                Buy {pack.usd_display}
              </button>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
