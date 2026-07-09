"use client";

import { AuthProvider, useAuth } from "@/lib/auth-context";
import { DashboardShell } from "@/components/dashboard/DashboardShell";
import { HomeOverviewContent } from "@/components/dashboard/HomeOverviewContent";
import { MarketingLandingPage } from "@/components/marketing/MarketingLandingPage";

function HomeAuthGate() {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen bg-canvas-bg md:ml-28">
        <div className="p-gutter">
          <div className="mb-6 h-12 w-72 animate-pulse bg-surface-elevated motion-reduce:animate-none" />
        </div>
      </div>
    );
  }

  if (!user) {
    return <MarketingLandingPage />;
  }

  return (
    <DashboardShell>
      <HomeOverviewContent />
    </DashboardShell>
  );
}

export function HomePageContent() {
  return (
    <AuthProvider>
      <HomeAuthGate />
    </AuthProvider>
  );
}
