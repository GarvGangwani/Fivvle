"use client";

import { useEffect, useMemo } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "@/lib/auth-context";

export function resolveAuthDestination(intent: string | null): string {
  if (intent === "start") return "/new";
  return "/dashboard";
}

/**
 * Send authenticated users away from login/signup (e.g. Google redirect return).
 * Does not wait on a status promise before navigation from the form — Option 2
 * pushes from the handler; destinations gate on status / loading.tsx.
 */
export function useAuthRedirect() {
  const { status } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const destination = useMemo(
    () => resolveAuthDestination(searchParams.get("intent")),
    [searchParams],
  );

  useEffect(() => {
    if (status === "authenticated") {
      router.replace(destination);
    }
  }, [status, router, destination]);
}

export function useAuthDestination(): string {
  const searchParams = useSearchParams();
  return useMemo(
    () => resolveAuthDestination(searchParams.get("intent")),
    [searchParams],
  );
}
