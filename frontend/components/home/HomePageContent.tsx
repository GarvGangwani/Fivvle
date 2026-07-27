"use client";

import { useAuth } from "@/lib/auth-context";
import { DashboardShell } from "@/components/dashboard/DashboardShell";
import { HomeOverviewContent } from "@/components/dashboard/HomeOverviewContent";
import { DashboardHomeSkeleton } from "@/components/dashboard/skeletons/DashboardHomeSkeleton";
import { MarketingLandingPage } from "@/components/marketing/MarketingLandingPage";

function HomeAuthGate() {
  const { status } = useAuth();

  if (status === "initializing") {
    return (
      <div className="min-h-screen bg-canvas-bg">
        <div className="px-gutter pb-gutter pt-24">
          <DashboardHomeSkeleton />
        </div>
      </div>
    );
  }

  if (status === "unauthenticated") {
    return <MarketingLandingPage />;
  }

  return (
    <DashboardShell>
      <HomeOverviewContent />
    </DashboardShell>
  );
}

export function HomePageContent() {
  return <HomeAuthGate />;
}
