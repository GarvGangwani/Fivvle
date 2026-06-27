"use client";

import type { ReactNode } from "react";
import { PreferencesProvider } from "@/lib/preferences-context";

export function AppProviders({ children }: { children: ReactNode }) {
  return <PreferencesProvider>{children}</PreferencesProvider>;
}
