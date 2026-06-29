"use client";

import { useState } from "react";
import { Coins, Loader2 } from "lucide-react";
import { useWallet } from "@/lib/wallet-context";
import { WalletModal } from "./WalletModal";

export function WalletTrigger() {
  const [open, setOpen] = useState(false);
  const { credits, loading } = useWallet();

  return (
    <>
      <button
        type="button"
        className="fv-wallet-balance"
        onClick={() => setOpen(true)}
        aria-label={`${credits} credits. Open wallet`}
        aria-haspopup="dialog"
      >
        <Coins className="fv-wallet-balance-icon" aria-hidden />
        <span className="fv-wallet-balance-credits">
          {loading ? (
            <Loader2 className="inline h-3.5 w-3.5 animate-spin" aria-hidden />
          ) : (
            <>{credits.toLocaleString()} Credits</>
          )}
        </span>
      </button>
      <WalletModal open={open} onClose={() => setOpen(false)} />
    </>
  );
}
