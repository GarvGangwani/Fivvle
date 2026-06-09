"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { CSSProperties, ReactNode } from "react";
import { Globe, Share2, Sparkles } from "lucide-react";
import { useAuth } from "@/lib/auth-context";
import { FivvleLogo } from "./FivvleLogo";

const SHELL_HEADER_HEIGHT = "4rem";
const SHELL_MOBILE_NAV_HEIGHT = "4rem";

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

function getUserInitial(
  displayName: string | null | undefined,
  email: string | null | undefined,
): string {
  if (displayName) {
    const initial = displayName.trim().charAt(0);
    if (initial) return initial.toUpperCase();
  }
  if (email) {
    return email.charAt(0).toUpperCase();
  }
  return "U";
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
  const userInitial = getUserInitial(user?.displayName, user?.email);

  const contentHeightClass = fullHeight
    ? "h-[calc(100vh-var(--fv-shell-header))] max-sm:h-[calc(100vh-var(--fv-shell-header)-var(--fv-shell-mobile-nav))] overflow-hidden"
    : "pb-16 sm:pb-0";

  return (
    <div
      className="min-h-screen bg-[var(--fv-bg)] text-[var(--fv-text)]"
      style={
        {
          "--fv-shell-header": SHELL_HEADER_HEIGHT,
          "--fv-shell-mobile-nav": SHELL_MOBILE_NAV_HEIGHT,
        } as CSSProperties
      }
    >
      <header
        className="sticky top-0 z-50 flex h-16 items-center justify-between border-b px-4 sm:px-6"
        style={{
          borderColor: "rgba(255,255,255,0.06)",
          background: "rgba(8,12,20,0.9)",
          backdropFilter: "blur(12px)",
        }}
      >
        <Link href="/dashboard" className="flex items-center gap-2.5 no-underline">
          <FivvleLogo size={30} />
          <span className="text-base font-semibold tracking-[-0.02em] text-[var(--fv-text)]">
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

        <div className="flex items-center gap-3">
          <p className="hidden text-[13px] sm:block">
            <span className="text-[var(--fv-text-soft)]">{getGreeting()}</span>{" "}
            <span className="font-medium text-[var(--fv-accent)]">{firstName}</span>
          </p>
          <div
            className="flex h-8 w-8 items-center justify-center rounded-full bg-[var(--fv-accent-muted)] text-xs font-semibold text-[var(--fv-accent)]"
            aria-hidden
          >
            {userInitial}
          </div>
        </div>
      </header>

      <div className={contentHeightClass}>{children}</div>

      <nav className="fixed bottom-0 left-0 right-0 z-50 flex border-t border-[var(--fv-border)] bg-[var(--fv-bg)]/95 backdrop-blur-md sm:hidden">
        <Link
          href={validateHref}
          className={`flex flex-1 flex-col items-center justify-center gap-1 py-2 text-[11px] no-underline ${
            tabActive(pathname, "validate")
              ? "text-[var(--fv-accent)]"
              : "text-[var(--fv-text-muted)]"
          }`}
        >
          <Sparkles className="h-5 w-5" />
          Validate
        </Link>
        <Link
          href={hostHref}
          className={`flex flex-1 flex-col items-center justify-center gap-1 py-2 text-[11px] no-underline ${
            tabActive(pathname, "host")
              ? "text-[var(--fv-accent)]"
              : "text-[var(--fv-text-muted)]"
          }`}
        >
          <Globe className="h-5 w-5" />
          Host
        </Link>
        <Link
          href={distributeHref}
          className={`flex flex-1 flex-col items-center justify-center gap-1 py-2 text-[11px] no-underline ${
            tabActive(pathname, "distribute")
              ? "text-[var(--fv-accent)]"
              : "text-[var(--fv-text-muted)]"
          }`}
        >
          <Share2 className="h-5 w-5" />
          Distribute
        </Link>
      </nav>
    </div>
  );
}
