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
      <div className="flex min-h-screen bg-[var(--fv-bg)]">
        <aside className="hidden h-screen w-[260px] shrink-0 border-r border-[var(--fv-border)] bg-[var(--fv-surface)] p-4 lg:flex">
          <div className="fv-skeleton h-8 w-full rounded-xl" />
          <div className="fv-skeleton mt-5 h-10 w-full rounded-xl" />
          <div className="mt-8 space-y-1">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="fv-skeleton h-14 rounded-lg" />
            ))}
          </div>
        </aside>
        <div className="flex min-w-0 flex-1 flex-col">
          <div
            className="flex h-16 shrink-0 items-center justify-between border-b px-4 sm:px-6"
            style={{ borderColor: "rgba(255,255,255,0.06)" }}
          >
            <div className="fv-skeleton h-8 w-24 rounded lg:hidden" />
            <div className="fv-skeleton h-8 w-8 rounded-full" />
          </div>
          <main className="flex-1 p-6">
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {Array.from({ length: 6 }).map((_, i) => (
                <div key={i} className="fv-skeleton h-40 rounded-xl" />
              ))}
            </div>
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
