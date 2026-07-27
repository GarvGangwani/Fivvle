"use client";

import type { ReactNode } from "react";
import { useAuth } from "@/lib/auth-context";
import { BrutalistSkeleton } from "@/components/ui/BrutalistSkeleton";

/**
 * Whole-app gate while Firebase resolves. Intentionally not dashboard-shaped —
 * reads as "app is loading," not "dashboard is loading."
 */
export function AuthInitializingGate({ children }: { children: ReactNode }) {
  const { status } = useAuth();

  if (status === "initializing") {
    return (
      <div
        className="flex min-h-screen flex-col items-center justify-center gap-6 bg-canvas-bg px-6"
        aria-busy="true"
        aria-label="Loading Fivvle"
      >
        <p className="font-mono text-mono-sm uppercase tracking-wider text-ink-tertiary">
          Fivvle
        </p>
        <div className="flex w-full max-w-xs flex-col gap-3">
          <BrutalistSkeleton variant="block" height="h-10" />
          <BrutalistSkeleton variant="line" width="w-3/4" />
          <BrutalistSkeleton variant="line" width="w-1/2" />
        </div>
      </div>
    );
  }

  return <>{children}</>;
}
