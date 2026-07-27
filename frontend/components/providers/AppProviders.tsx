"use client";

import type { ReactNode } from "react";
import { AuthProvider } from "@/lib/auth-context";
import { PreferencesProvider } from "@/lib/preferences-context";
import { AuthInitializingGate } from "@/components/auth/AuthInitializingGate";

/**
 * Root client providers. AuthProvider is singular here so session persists
 * across `/`, `/(auth)`, and `/(dashboard)` without remounting Firebase.
 */
export function AppProviders({ children }: { children: ReactNode }) {
  return (
    <AuthProvider>
      <PreferencesProvider>
        <AuthInitializingGate>{children}</AuthInitializingGate>
      </PreferencesProvider>
    </AuthProvider>
  );
}
