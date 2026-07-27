"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { AdminCostDashboard } from "@/components/admin/AdminCostDashboard";
import { ErrorBanner } from "@/components/ui/ErrorBanner";
import { LoadingState } from "@/components/ui/LoadingState";
import { ApiError, syncUser } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";

type AccessState = "loading" | "granted" | "denied" | "error";

export default function AdminCostPageClient() {
  const { user, status, refreshProfile } = useAuth();
  const router = useRouter();
  const [accessState, setAccessState] = useState<AccessState>("loading");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    if (status === "initializing") return;

    if (status === "unauthenticated" || !user) {
      router.replace("/login");
      return;
    }

    const currentUser = user;

    let cancelled = false;

    async function verifyAdminAccess() {
      setAccessState("loading");
      setErrorMessage(null);
      try {
        const profile = await syncUser(currentUser);
        if (cancelled) return;
        if (profile.is_admin) {
          setAccessState("granted");
          await refreshProfile();
        } else {
          setAccessState("denied");
        }
      } catch (err) {
        if (cancelled) return;
        setAccessState("error");
        if (err instanceof ApiError && err.status === 0) {
          setErrorMessage(
            "Could not reach the API. Start the backend (uvicorn on port 8000) and try again.",
          );
        } else {
          setErrorMessage("Could not verify admin access. Try signing out and back in.");
        }
      }
    }

    void verifyAdminAccess();

    return () => {
      cancelled = true;
    };
  }, [status, user, router, refreshProfile]);

  useEffect(() => {
    if (accessState === "denied") {
      router.replace("/");
    }
  }, [accessState, router]);

  if (status === "initializing" || accessState === "loading") {
    return (
      <div className="p-6">
        <LoadingState label="Checking admin access…" />
      </div>
    );
  }

  if (accessState === "error") {
    return (
      <div className="mx-auto max-w-lg p-6">
        <ErrorBanner message={errorMessage ?? "Something went wrong."} />
      </div>
    );
  }

  if (accessState === "denied") {
    return null;
  }

  return <AdminCostDashboard />;
}
