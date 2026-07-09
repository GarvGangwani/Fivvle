"use client";

import { useEffect, useMemo } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "@/lib/auth-context";

export function resolveAuthDestination(intent: string | null): string {
  if (intent === "start") return "/new";
  return "/dashboard";
}

/** Send authenticated users away from login/signup pages (e.g. after Google redirect). */
export function useAuthRedirect() {
  const { user, loading } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const destination = useMemo(
    () => resolveAuthDestination(searchParams.get("intent")),
    [searchParams],
  );

  useEffect(() => {
    if (!loading && user) {
      router.replace(destination);
    }
  }, [user, loading, router, destination]);
}

export function useAuthDestination(): string {
  const searchParams = useSearchParams();
  return useMemo(
    () => resolveAuthDestination(searchParams.get("intent")),
    [searchParams],
  );
}
