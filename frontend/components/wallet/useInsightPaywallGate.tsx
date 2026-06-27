"use client";

import { useCallback, useRef, useState } from "react";
import { InsightPaywallModal } from "./InsightPaywallModal";

/**
 * Gate insight unlock behind the paywall modal; billing runs on generate-insight.
 */
export function useInsightPaywallGate() {
  const [open, setOpen] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const pendingActionRef = useRef<(() => void | Promise<void>) | null>(null);

  const requestInsightUnlock = useCallback(
    (action: () => void | Promise<void>) => {
      pendingActionRef.current = action;
      setOpen(true);
    },
    [],
  );

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
    <InsightPaywallModal
      open={open}
      onClose={handleClose}
      onConfirm={() => void handleConfirm()}
      confirming={confirming}
    />
  );

  return { requestInsightUnlock, paywallModal };
}
