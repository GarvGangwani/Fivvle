"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { ApiError, getWallet, type WalletBalance } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";

type WalletSnapshotPatch = Partial<
  Pick<
    WalletBalance,
    | "credits_balance"
    | "usd_equivalent"
    | "has_redeemed_welcome_coupon"
    | "total_credits_purchased"
  >
>;

type WalletContextValue = {
  balance: WalletBalance | null;
  credits: number;
  usdLabel: string;
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
  applyWalletPatch: (patch: WalletSnapshotPatch) => void;
};

const WalletContext = createContext<WalletContextValue | null>(null);

export function WalletProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  const [balance, setBalance] = useState<WalletBalance | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const refreshGeneration = useRef(0);

  const refresh = useCallback(async () => {
    if (!user) {
      setBalance(null);
      setError(null);
      return;
    }
    const generation = ++refreshGeneration.current;
    setLoading(true);
    setError(null);
    try {
      const snapshot = await getWallet();
      if (generation !== refreshGeneration.current) {
        return;
      }
      setBalance(snapshot);
    } catch (err) {
      if (generation !== refreshGeneration.current) {
        return;
      }
      setBalance(null);
      if (err instanceof ApiError && err.status === 401) {
        setError(null);
        return;
      }
      setError("Could not load wallet balance.");
    } finally {
      if (generation === refreshGeneration.current) {
        setLoading(false);
      }
    }
  }, [user]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const applyWalletPatch = useCallback((patch: WalletSnapshotPatch) => {
    setBalance((prev) => {
      if (!prev) {
        return {
          credits_balance: patch.credits_balance ?? 0,
          usd_equivalent: patch.usd_equivalent ?? "—",
          total_credits_purchased: patch.total_credits_purchased ?? 0,
          total_credits_consumed: 0,
          credit_conversion_rate: 5,
          has_redeemed_welcome_coupon: patch.has_redeemed_welcome_coupon ?? false,
          packs: [],
        };
      }
      return { ...prev, ...patch };
    });
  }, []);

  const value = useMemo<WalletContextValue>(
    () => ({
      balance,
      credits: balance?.credits_balance ?? 0,
      usdLabel: balance?.usd_equivalent ?? "—",
      loading,
      error,
      refresh,
      applyWalletPatch,
    }),
    [balance, loading, error, refresh, applyWalletPatch],
  );

  return (
    <WalletContext.Provider value={value}>{children}</WalletContext.Provider>
  );
}

export function useWallet(): WalletContextValue {
  const ctx = useContext(WalletContext);
  if (!ctx) {
    throw new Error("useWallet must be used within WalletProvider");
  }
  return ctx;
}
