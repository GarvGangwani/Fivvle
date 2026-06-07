"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";
import { useAuth } from "@/lib/auth-context";
import { FivvleLogo } from "./FivvleLogo";

function getGreeting(): string {
  const hour = new Date().getHours();
  if (hour < 12) return "Good morning,";
  if (hour < 17) return "Good afternoon,";
  return "Good evening,";
}

function getFirstName(
  displayName: string | null | undefined,
  email: string | null | undefined,
): string {
  if (displayName) {
    const first = displayName.trim().split(/\s+/)[0];
    if (first) return first;
  }
  if (email) {
    const local = email.split("@")[0];
    if (local) return local.charAt(0).toUpperCase() + local.slice(1);
  }
  return "Founder";
}

function getExperimentIdFromPath(pathname: string): string | null {
  const match = pathname.match(/^\/experiment\/([^/]+)/);
  return match ? match[1] : null;
}

function tabActive(pathname: string, tab: "validate" | "host" | "distribute"): boolean {
  if (tab === "validate") {
    return pathname === "/new" || pathname.startsWith("/new/");
  }
  if (tab === "host") {
    return pathname.includes("/landing-page");
  }
  if (tab === "distribute") {
    const expMatch = pathname.match(/^\/experiment\/([^/]+)$/);
    return expMatch !== null;
  }
  return false;
}

interface FivvleShellProps {
  children: ReactNode;
  fullHeight?: boolean;
}

export function FivvleShell({ children, fullHeight = false }: FivvleShellProps) {
  const pathname = usePathname();
  const { user } = useAuth();
  const experimentId = getExperimentIdFromPath(pathname);

  const validateHref = "/new";
  const hostHref = experimentId
    ? `/experiment/${experimentId}/landing-page`
    : "/dashboard";
  const distributeHref = experimentId
    ? `/experiment/${experimentId}`
    : "/dashboard";

  const firstName = getFirstName(user?.displayName, user?.email);

  return (
    <div className="min-h-screen bg-[var(--fv-bg)] text-[var(--fv-text)]">
      <header
        className="sticky top-0 z-50 flex h-[58px] items-center justify-between border-b px-4 sm:px-6"
        style={{
          borderColor: "rgba(255,255,255,0.06)",
          background: "rgba(8,12,20,0.9)",
          backdropFilter: "blur(12px)",
        }}
      >
        <Link href="/dashboard" className="flex items-center gap-2.5 no-underline">
          <FivvleLogo size={30} />
          <span className="text-[15px] font-semibold text-[var(--fv-text)]">
            Fivvle
          </span>
        </Link>

        <nav
          className="hidden rounded-xl border p-1 sm:flex"
          style={{
            background: "rgba(255,255,255,0.04)",
            borderColor: "rgba(255,255,255,0.08)",
          }}
        >
          <Link
            href={validateHref}
            className={`fv-tab-pill no-underline ${
              tabActive(pathname, "validate") ? "fv-tab-pill-active" : ""
            }`}
          >
            Validate
          </Link>
          <Link
            href={hostHref}
            className={`fv-tab-pill no-underline ${
              tabActive(pathname, "host") ? "fv-tab-pill-active" : ""
            }`}
          >
            Host
          </Link>
          <Link
            href={distributeHref}
            className={`fv-tab-pill no-underline ${
              tabActive(pathname, "distribute") ? "fv-tab-pill-active" : ""
            }`}
          >
            Distribute
          </Link>
        </nav>

        <p className="hidden text-[13px] sm:block">
          <span className="text-[var(--fv-text-soft)]">{getGreeting()}</span>{" "}
          <span className="font-medium text-[var(--fv-accent)]">{firstName}</span>
        </p>
      </header>

      <div className={fullHeight ? "h-[calc(100vh-58px)] overflow-hidden" : ""}>
        {children}
      </div>
    </div>
  );
}
