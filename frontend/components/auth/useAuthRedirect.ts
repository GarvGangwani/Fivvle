"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";

/** Send authenticated users away from login/signup pages (e.g. after Google redirect). */
export function useAuthRedirect(destination = "/dashboard") {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && user) {
      router.replace(destination);
    }
  }, [user, loading, router, destination]);
}
