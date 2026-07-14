"use client";

import { usePathname } from "next/navigation";
import { FivvleShell } from "@/components/layout/FivvleShell";
import { DashboardShell as BrutalistDashboardShell } from "@/components/dashboard/DashboardShell";

const BRUTALIST_ROUTES = [
  "/archived",
  "/experiments",
  "/experiment",
  "/settings",
  "/new",
];

export function DashboardShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  if (
    BRUTALIST_ROUTES.some(
      (route) => pathname === route || pathname.startsWith(`${route}/`),
    )
  ) {
    return <BrutalistDashboardShell>{children}</BrutalistDashboardShell>;
  }

  const fullHeight = pathname.startsWith("/experiment/");

  return <FivvleShell fullHeight={fullHeight}>{children}</FivvleShell>;
}
