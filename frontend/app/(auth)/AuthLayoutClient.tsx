"use client";

import { AuthProvider } from "@/lib/auth-context";

export function AuthLayoutClient({ children }: { children: React.ReactNode }) {
  return <AuthProvider>{children}</AuthProvider>;
}
