"use client";

import { AuthProvider, useAuth } from "@/lib/auth-context";
import { FivvleShell } from "@/components/layout/FivvleShell";
import { DashboardContent } from "@/components/dashboard/DashboardContent";
import { MarketingHero } from "./MarketingHero";

function HomeAuthGate() {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen bg-[var(--fv-bg)]">
        <div className="mx-auto max-w-6xl p-6">
          <div className="fv-skeleton mb-6 h-8 w-48 rounded" />
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="fv-skeleton h-40 rounded-xl" />
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (!user) {
    return <MarketingHero />;
  }

  return (
    <FivvleShell>
      <DashboardContent />
    </FivvleShell>
  );
}

export function HomePageContent() {
  return (
    <AuthProvider>
      <HomeAuthGate />
    </AuthProvider>
  );
}
