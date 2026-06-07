"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { LogOut } from "lucide-react";
import { useAuth } from "@/lib/auth-context";
import { FivvleLogo } from "@/components/layout/FivvleLogo";

function DashboardAuthGuard({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !user) {
      router.replace("/login");
    }
  }, [user, loading, router]);

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[var(--fv-bg)]">
        <span className="text-sm text-[var(--fv-text-muted)]">Loading…</span>
      </div>
    );
  }

  if (!user) {
    return null;
  }

  return <>{children}</>;
}

function DashboardNav() {
  const { user, logOut } = useAuth();
  const [signingOut, setSigningOut] = useState(false);

  async function handleSignOut() {
    setSigningOut(true);
    try {
      await logOut();
    } finally {
      setSigningOut(false);
    }
  }

  return (
    <header className="border-b border-[var(--fv-border)] bg-[var(--fv-surface)]">
      <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-3 sm:px-6">
        <Link
          href="/dashboard"
          className="flex items-center gap-2.5 no-underline"
        >
          <FivvleLogo size={28} className="rounded-lg" />
          <span className="text-lg font-semibold text-[var(--fv-text)]">Fivvle</span>
        </Link>

        <div className="flex items-center gap-3 sm:gap-4">
          <span className="hidden max-w-[200px] truncate text-sm text-[var(--fv-text-muted)] sm:inline">
            {user?.email}
          </span>
          <button
            type="button"
            onClick={handleSignOut}
            disabled={signingOut}
            className="fv-btn-ghost inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium disabled:cursor-not-allowed disabled:opacity-50"
          >
            <LogOut className="h-4 w-4" />
            <span className="hidden sm:inline">
              {signingOut ? "Signing out…" : "Sign out"}
            </span>
          </button>
        </div>
      </div>
    </header>
  );
}

export default function DashboardShellLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <DashboardAuthGuard>
      <div className="min-h-screen bg-[var(--fv-bg)]">
        <DashboardNav />
        {children}
      </div>
    </DashboardAuthGuard>
  );
}
