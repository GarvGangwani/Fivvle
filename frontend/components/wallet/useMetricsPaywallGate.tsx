"use client";

import { useCallback, useRef, useState } from "react";
import { MetricsPaywallModal } from "./MetricsPaywallModal";

/**
 * Gate metrics analysis behind the paywall modal and server-side unlock.
 */
export function useMetricsPaywallGate() {
  const [open, setOpen] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const pendingActionRef = useRef<(() => void | Promise<void>) | null>(null);

  const requestMetricsAnalysis = useCallback((action: () => void | Promise<void>) => {
    pendingActionRef.current = action;
    setOpen(true);
  }, []);

  const handleClose = useCallback(() => {
    if (confirming) return;
    setOpen(false);
    pendingActionRef.current = null;
  }, [confirming]);

  const handleConfirm = useCallback(async () => {
    const action = pendingActionRef.current;
    if (!action) return;
    setConfirming(true);
    try {
      await action();
      setOpen(false);
      pendingActionRef.current = null;
    } finally {
      setConfirming(false);
    }
  }, []);

  const paywallModal = (
    <MetricsPaywallModal
      open={open}
      onClose={handleClose}
      onConfirm={() => void handleConfirm()}
      confirming={confirming}
    />
  );

  return { requestMetricsAnalysis, paywallModal };
}
