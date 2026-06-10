"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";
import { Home, MessageSquare, Plus } from "lucide-react";
import { useAuth } from "@/lib/auth-context";
import {
  getExperimentIdFromPath,
  ShellSidebar,
} from "@/components/layout/ShellSidebar";

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

function mobileTabActive(
  pathname: string,
  tab: "projects" | "new" | "experiment",
  experimentId: string | null,
): boolean {
  if (tab === "projects") {
    return pathname === "/" || pathname === "/dashboard";
  }
  if (tab === "new") {
    return pathname === "/new" || pathname.startsWith("/new/");
  }
  if (tab === "experiment") {
    return experimentId !== null && pathname.startsWith(`/experiment/${experimentId}`);
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

  const firstName = getFirstName(user?.displayName, user?.email);
  const userInitial = getUserInitial(user?.displayName, user?.email);

  const experimentHref = experimentId
    ? `/experiment/${experimentId}`
    : "/";

  const contentClass = fullHeight
    ? "flex min-h-0 flex-1 flex-col overflow-hidden"
    : "flex-1 overflow-y-auto";

  return (
    <div className="flex min-h-screen bg-[var(--fv-bg)] text-[var(--fv-text)]">
      <ShellSidebar />

      <div className="flex min-h-0 min-w-0 flex-1 flex-col">
        <header
          className="sticky top-0 z-50 flex h-16 min-w-0 shrink-0 items-center justify-between gap-2 border-b border-[var(--fv-border)] px-4 sm:px-6 lg:pl-6"
          style={{
            background: "rgba(8,12,20,0.9)",
            backdropFilter: "blur(12px)",
          }}
        >
          <Link
            href="/"
            className="flex min-w-0 shrink items-center gap-2 no-underline lg:hidden"
          >
            <div
              className="fv-f-logo shrink-0"
              style={{ width: 30, height: 30, fontSize: 15 }}
              aria-hidden
            >
              F
            </div>
            <span className="truncate text-base font-semibold tracking-[-0.02em] text-[var(--fv-text)]">
              Fivvle
            </span>
          </Link>

          <div className="hidden min-w-0 flex-1 lg:block" aria-hidden />

          <div className="flex shrink-0 items-center gap-2 sm:gap-3">
            <p className="hidden max-w-[140px] truncate text-[13px] sm:block md:max-w-none">
              <span className="text-[var(--fv-text-soft)]">{getGreeting()}</span>{" "}
              <span className="font-medium text-[var(--fv-accent)]">
                {firstName}
              </span>
            </p>
            <div
              className="flex h-8 w-8 items-center justify-center rounded-full bg-[var(--fv-accent-muted)] text-xs font-semibold text-[var(--fv-accent)]"
              aria-hidden
            >
              {userInitial}
            </div>
          </div>
        </header>

        <div className={`${contentClass} pb-16 lg:pb-0`}>{children}</div>

        <nav
          className="fixed bottom-0 left-0 right-0 z-50 flex border-t border-[var(--fv-border)] bg-[var(--fv-bg)]/95 pb-[env(safe-area-inset-bottom,0px)] backdrop-blur-md lg:hidden"
          aria-label="Mobile navigation"
        >
          <Link
            href="/"
            className={`flex min-h-[48px] flex-1 flex-col items-center justify-center gap-1 py-2 text-[11px] no-underline ${
              mobileTabActive(pathname, "projects", experimentId)
                ? "text-[var(--fv-accent)]"
                : "text-[var(--fv-text-muted)]"
            }`}
          >
            <Home className="h-5 w-5" />
            Projects
          </Link>
          <Link
            href="/new"
            className={`flex min-h-[48px] flex-1 flex-col items-center justify-center gap-1 py-2 text-[11px] no-underline ${
              mobileTabActive(pathname, "new", experimentId)
                ? "text-[var(--fv-accent)]"
                : "text-[var(--fv-text-muted)]"
            }`}
          >
            <Plus className="h-5 w-5" />
            New
          </Link>
          <Link
            href={experimentHref}
            className={`flex min-h-[48px] flex-1 flex-col items-center justify-center gap-1 py-2 text-[11px] no-underline ${
              mobileTabActive(pathname, "experiment", experimentId)
                ? "text-[var(--fv-accent)]"
                : "text-[var(--fv-text-muted)]"
            }`}
          >
            <MessageSquare className="h-5 w-5" />
            {experimentId ? "Project" : "Open"}
          </Link>
        </nav>
      </div>
    </div>
  );
}
