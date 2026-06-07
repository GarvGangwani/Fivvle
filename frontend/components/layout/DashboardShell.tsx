"use client";

import { usePathname } from "next/navigation";
import { FivvleShell } from "@/components/layout/FivvleShell";

export function DashboardShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const fullHeight =
    pathname === "/new" || pathname.startsWith("/new/");

  return <FivvleShell fullHeight={fullHeight}>{children}</FivvleShell>;
}
