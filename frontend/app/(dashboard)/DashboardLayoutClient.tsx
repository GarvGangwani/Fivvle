"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { DashboardShell } from "@/components/layout/DashboardShell";
import { ToastProvider } from "@/components/ui/ToastProvider";

function DashboardGuard({ children }: { children: React.ReactNode }) {
  const { user, status } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (status === "unauthenticated") {
      router.replace("/login");
    }
  }, [status, router]);

  // Auth initializing is handled by root AuthInitializingGate.
  // Route transitions use sibling loading.tsx files (brutalist).
  if (status === "initializing") {
    return null;
  }

  if (status === "unauthenticated" || !user) {
    return null;
  }

  return <>{children}</>;
}

export function DashboardLayoutClient({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <DashboardGuard>
      <ToastProvider>
        <DashboardShell>{children}</DashboardShell>
      </ToastProvider>
    </DashboardGuard>
  );
}
