"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { AuthProvider, useAuth } from "@/lib/auth-context";
import { DashboardShell } from "@/components/layout/DashboardShell";
import { ToastProvider } from "@/components/ui/ToastProvider";

function DashboardGuard({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !user) {
      router.replace("/login");
    }
  }, [user, loading, router]);

  if (loading) {
    return (
      <div className="min-h-screen bg-[var(--fv-bg)]">
        <div
          className="flex h-16 items-center justify-between border-b px-4 sm:px-6"
          style={{
            borderColor: "rgba(255,255,255,0.06)",
            background: "rgba(8,12,20,0.9)",
          }}
        >
          <div className="flex items-center gap-2.5">
            <div className="fv-skeleton h-8 w-8 rounded-lg" />
            <div className="fv-skeleton h-4 w-16 rounded" />
          </div>
          <div className="fv-skeleton hidden h-9 w-64 rounded-xl sm:block" />
          <div className="fv-skeleton h-8 w-8 rounded-full" />
        </div>

        <div className="flex">
          <aside
            className="hidden w-[260px] shrink-0 border-r p-4 md:block"
            style={{ borderColor: "rgba(255,255,255,0.06)" }}
          >
            <div className="space-y-1">
              {Array.from({ length: 4 }).map((_, i) => (
                <div key={i} className="fv-skeleton h-14 rounded-lg" />
              ))}
            </div>
          </aside>

          <main className="flex-1 p-4 sm:p-6 md:p-8">
            <div className="fv-skeleton mb-4 h-8 w-48 rounded" />
            <div className="fv-skeleton h-64 rounded-xl" />
          </main>
        </div>
      </div>
    );
  }

  if (!user) {
    return null;
  }

  return <>{children}</>;
}

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <AuthProvider>
      <DashboardGuard>
        <ToastProvider>
          <DashboardShell>{children}</DashboardShell>
        </ToastProvider>
      </DashboardGuard>
    </AuthProvider>
  );
}
