"use client";

import { AuthProvider, useAuth } from "@/lib/auth-context";
import { FivvleShell } from "@/components/layout/FivvleShell";
import { DashboardContent } from "@/components/dashboard/DashboardContent";
import { MarketingLandingPage } from "@/components/marketing/MarketingLandingPage";

function HomeAuthGate() {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen bg-canvas-bg">
        <div className="mx-auto max-w-6xl p-gutter">
          <div className="mb-6 h-8 w-48 animate-pulse bg-surface-elevated motion-reduce:animate-none" />
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {Array.from({ length: 6 }).map((_, i) => (
              <div
                key={i}
                className="h-40 animate-pulse bg-surface-elevated motion-reduce:animate-none"
              />
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (!user) {
    return <MarketingLandingPage />;
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
